# django-17554: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

### [High] `FETCH_PEERS` sets deferred fields to a 1-tuple instead of the value
`django/db/models/query_utils.py:288-297` (introduced in this PR)

Trigger: `Primary.objects.fetch_mode(FETCH_PEERS).defer("value")`, then read `p1.value` with 2 or more peers alive.

Impact: `fetch_many` calls `.values_list(attname).in_bulk(pks)`. In `in_bulk`, `pk` is not in `values_select`. It re-queries with `values_list("pk", attname)` and sets `get_obj = itemgetter(slice(1, None))` (`query.py:1228-1237`). Each dict value is therefore `("yy",)`, and `setattr(instance, attname, value_by_pk[instance.pk])` stores that tuple on every peer. The first access and all peers get a tuple, not the value, and a later `save()` would write it back.

The new tests only assert query counts (`tests/defer/tests.py`, `test_*_fetch_mode_fetch_peers`), never the value, so they miss this. I could not run it: the sandbox Python lacks `datetime.UTC`. This comes from reading the code.

Fix direction: use `values_list(attname, flat=True)` (flat mode maps back to itself), and assert the value in the test.

### [Medium] `fetch_many` overwrites peers that already have the field loaded, and raises `KeyError` for deleted rows
`django/db/models/query_utils.py:288-297` (introduced in this PR)

Trigger:
- A peer already has the field loaded and modified in memory, for example after an earlier `refresh_from_db` or an assignment. Another peer's deferred access then triggers `fetch_many`.
- A peer's row has been deleted since the queryset ran.

Impact:
- `fetch_many` passes every live peer, with no filter on `attname in instance.__dict__`. It overwrites loaded or unsaved values with DB values. The sibling descriptors filter with `is_cached`.
- `value_by_pk[instance.pk]` raises `KeyError` for a deleted row, so one peer's access fails on another peer's missing row. `FETCH_ONE` would only fail for the instance being accessed.

Fix direction: select only instances where `attname not in i.__dict__`, and use `.get`/skip for missing pks.

### [Medium] Forward and reverse one-to-one prefetch drops the `instance` router hint for custom querysets
`django/db/models/fields/related_descriptors.py:180-182` and `:474-476` (introduced in this PR)

Trigger: `Prefetch("fk", queryset=Qs.objects.all())` on a forward FK or one-to-one, or on a reverse one-to-one, with a database router that reads `hints["instance"]`.

Impact: the old code called `queryset._add_hints(instance=instances[0])` on every queryset, including user-supplied ones. Now the hint is only added through `get_queryset(instance=...)` when no queryset is supplied. A custom queryset no longer carries the hint, so `router.db_for_read` may pick a different database. The sibling reverse-FK, M2M and generic managers still call `_add_hints` on supplied querysets (`related_descriptors.py:806`, `:1183`; `contenttypes/fields.py:669`), so this looks unintended.

Fix direction: keep `queryset._add_hints(instance=instances[0])` for the supplied-queryset branch.

### [Medium] `get_queryset(**hints)` became keyword-only `get_queryset(*, instance)` on the one-to-one descriptors
`related_descriptors.py:169` and `:463` (introduced in this PR)

Trigger: third-party or user code that calls `descriptor.get_queryset()` with no arguments or with other hints, or that overrides it with the old signature. The old code accepted any hints and had a no-argument form.

Impact: `TypeError` for external callers. In-repo callers are updated, and `get_prefetch_querysets` and `get_object` are fine. The release notes don't mention the signature change.

Fix direction: keep `**hints` compatibility, or document the change.

### [Low] `RAISE` blocks generic foreign key access even when no query is needed
`django/contrib/contenttypes/fields.py:259-260` (introduced in this PR)

Trigger: a GFK instance with `content_type_id=None` or `object_id=None`, loaded under `RAISE`, then reading `obj.content_object`.

Impact: the old code returned `None` without a query. Now `fetch_mode.fetch` runs unconditionally, so `Raise` throws `FieldFetchBlocked`. The forward FK path guards with `has_value`, and the GFK path doesn't.

Fix direction: short-circuit when `ct_id is None` or the pk is `None`, before calling `fetch`.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `DeferredAttribute` now routes through `fetch_mode.fetch` and adds `fetch_many` | changes meaning; iterates inputs; library call | `in_bulk` source, `query_utils` callers (`FileDescriptor`, `SpatialProxy`, `ForeignKeyDeferredAttribute`) | findings 1 and 2 |
| `get_queryset(instance=)` and hint handling in forward and reverse one-to-one | signature; removes or moves code; sibling branch | siblings (reverse FK, M2M, generic managers), in-repo callers, `_add_hints` | findings 3 and 4 |
| GFK `__get__` split into `fetch_one` and `fetch_many` | removes or moves code; sibling branch | old `ct_id is None` path vs. `Raise.fetch` | finding 5 |
| `ModelState.fetch_mode`, `peers`, `__getstate__` | adds a field; state across calls | `from_db`, `QuerySet.create`, pickle via `__reduce__`, `RawQuerySet`, `RelatedPopulator`, `OneToOne.get_object` (parent link) | carried through everywhere; `peers` is dropped on copy or pickle, which is acceptable |
| Reverse-FK and M2M managers set `_fetch_mode` | adds a field; sibling branch | `_apply_rel_filters`, generic manager | consistent |
| `QuerySet._fetch_mode` | adds a field | `_clone`, `RawQuerySet.using`, `raw()` | carried |

Reviewed head `f52490c` against merge base `bee6456`. I did not run tests, CI or the Django code, because the sandbox Python is too old to import it. I read the head from a `git archive` export under `$TMPDIR`. Findings 1 and 2 are traced statically. There were no PR comments to triage.
