# django-17554: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

## Review of PR #17554: "Fixed #28586 -- Added model field fetching modes"

I read the diff statically. I did not run any tests.

### [High] `DeferredAttribute.fetch_many` stores a 1-tuple instead of the field value
`django/db/models/query_utils.py:288-297` (introduced in this PR)

Trigger: `Model.objects.fetch_mode(FETCH_PEERS).defer("value")` returns two or more rows, and you then read `p1.value`.

Why it breaks:
- `fetch_many` calls `.values_list(attname).in_bulk({pks})`.
- In `in_bulk`, `pk` is not in `values_select`, so the `ValuesListIterable` branch builds `values_list("pk", "value")`. It then uses `get_obj = itemgetter(slice(1, None))` (`query.py` ~1233-1243).
- So `value_by_pk[pk]` is `("xx",)`, not `"xx"`.
- `setattr(instance, attname, ...)` therefore puts a tuple on every peer, including the instance being read.

Impact: the first access returns `("xx",)` instead of `"xx"`. The wrong value then sits in `__dict__` and gets saved by `save()`. The new tests (`test_only_fetch_mode_fetch_peers`, `test_defer_fetch_mode_fetch_peers`) only count queries and never assert the value, so they pass anyway.

Fix direction: use `values_list(attname, flat=True)`, or `.in_bulk(...)` on `values_list("pk", attname)` and unpack the row. Assert the fetched value in the tests.

### [Medium] A custom `Prefetch` queryset no longer gets the `instance` router hint
`django/db/models/fields/related_descriptors.py:179-181` and `:473-475` (introduced in this PR)

Trigger: `prefetch_related(Prefetch("fk_or_o2o", queryset=qs))` on a multi-database setup, where a router's `db_for_read` uses `hints["instance"]`.

Why it breaks:
- The base code called `queryset._add_hints(instance=instances[0])` on whichever queryset was used.
- The head only adds the hint inside `get_queryset(instance=...)`, and that is only called when no custom queryset is given.
- The sibling paths still add the hint for custom querysets: `contenttypes/fields.py:669`, `related_descriptors.py:806` and `:1183`.

Impact: routing for custom-queryset prefetches on forward FK and reverse and forward one-to-one silently stops seeing the instance hint, so reads can go to the wrong database.

Fix direction: restore `queryset._add_hints(instance=instances[0])` after the selection, or only for the custom-queryset branch.

### [Medium] `FETCH_PEERS` on a dangling non-null FK returns `None` instead of raising
`django/db/models/fields/related_descriptors.py:259-261` (introduced in this PR)

Trigger: the FK value points at a row that doesn't exist (no DB constraint or a deleted row), on a non-null FK in `FETCH_PEERS` mode with two or more peers.

Why it breaks:
- The base code ran `get_object`, which raised `DoesNotExist`.
- The head now does `return self.field.get_cached_value(instance)` straight after `fetch`, which skips the `if rel_obj is None and not self.field.null: raise RelatedObjectDoesNotExist` check below.
- `fetch_many` goes through prefetch, which caches `None` for missing rows.

Impact: a non-null FK silently returns `None`, and the result differs from the `FETCH_ONE` path. The same early return exists for the generic foreign key, but there `None` is a legal value.

Fix direction: fall through to the existing null check instead of returning early.

### [Low] `DeferredAttribute.fetch_many` raises `KeyError` if a peer row was deleted
`query_utils.py:297` (introduced in this PR)

Trigger: a peer's row is deleted after the queryset was evaluated, then a deferred field is read in `FETCH_PEERS` mode.

Why it breaks: `value_by_pk[instance.pk]` raises `KeyError`. `FETCH_ONE` would raise `DoesNotExist` from `refresh_from_db`. The instance being read is covered by the same lookup, so reading a field of a peer that still exists can fail because of a different peer's deletion.

Fix direction: skip missing pks, or fall back to `fetch_one` for the requested instance.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| Deferred field load goes through `fetch_mode.fetch` | changes meaning; adds a branch; iterates input | `DeferredAttribute` subclasses (`FileDescriptor`, `SpatialProxy`, `ForeignKeyDeferredAttribute`), `in_bulk` source | tuple finding, `KeyError` finding |
| Forward FK `__get__` delegates to `fetch` | removes/moves code; adds a branch | base vs head side effects (reverse-cache set for one-to-one is kept in `fetch_one`; the null check is skipped in the early return) | dangling FK finding |
| `get_queryset(**hints)` becomes `get_queryset(*, instance)` | changes a signature; removes code | in-repo callers all updated; `_add_hints` for custom querysets compared with siblings | hint finding. The signature change breaks any external `get_queryset()` call and is undocumented, but it is a semi-internal descriptor API, so I didn't report it. |
| Reverse one-to-one `__get__` → `fetch_one` | removes code | `get_forward_related_filter` still used; reverse cache is set | OK |
| `peers` weakrefs on `ModelState` | adds a field; state across calls | pickle (`__getstate__` drops `peers`, so unpickled instances fall back to `fetch_one`), `copy` | OK |
| `fetch_mode` carried to the manager, generic FK, `create`, `RawQuerySet`, `_clone` | adds a field | reverse FK and M2M managers, GFK manager and prefetch, `from_db` and `RelatedPopulator`, `get_or_create`/`update_or_create` go through `create` | carried everywhere. I did not check `bulk_create`, `refresh_from_db`, or `Prefetch` querysets inheriting the mode. |
| New exception `FieldFetchBlocked(FieldError)` | changes meaning | `RAISE` message, `__cause__` suppressed | OK |

**Reviewed:** head `f52490c7f1dadde5a8186734ac3a16274f291a5c`, base `bee64561a6e8cd22995c2b1254bab66dae892a6d` (merge base is the base tip).

**Not checked:** I did not run the tests or see CI. I did not read the docs or release-note text, or the non-defer test files in detail. The tuple finding comes from reading `in_bulk`, not from running it, so run `Primary.objects.fetch_mode(FETCH_PEERS).defer("value")` and print `p1.value` to confirm it.
