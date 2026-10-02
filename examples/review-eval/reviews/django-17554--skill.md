# django-17554: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

## Review of PR #17554: "Fixed #28586 -- Added model field fetching modes"

Reviewed head `f52490c7` against base `bee64561`, which is also the merge-base. I read the full `django/` diff and the new `tests/defer` tests. No comments were on the PR. I did not run anything.

### [High] `FETCH_PEERS` stores a 1-tuple in the deferred field instead of the value
`django/db/models/query_utils.py`, `DeferredAttribute.fetch_many` (introduced in this PR)

Trigger: `Primary.objects.fetch_mode(FETCH_PEERS).defer("value")` with at least two rows, then read `p1.value`.

Impact:
- `fetch_many` builds its mapping with `.values_list(attname).in_bulk(pks)`.
- On `in_bulk` at this head, a `ValuesListIterable` queryset that doesn't include `pk` goes through `get_obj = itemgetter(slice(1, None))`. So each mapped value is `("xx",)`, not `"xx"`.
- `setattr(instance, attname, value_by_pk[instance.pk])` then caches `("xx",)` on every peer, including the one being read.
- The field silently holds the wrong type, and a later `save()` would write it.

The new tests (`test_only_fetch_mode_fetch_peers`, `test_defer_fetch_mode_fetch_peers`) only assert query counts, so they can't catch this.

Fix direction: use `values_list(attname, flat=True)`. Alternatively use `.values_list("pk", attname)` and build a dict. Add a test that asserts the fetched value.

### [Medium] `DeferredAttribute.fetch_many` overwrites peers' state and crashes on deleted peers
`django/db/models/query_utils.py`, `DeferredAttribute.fetch_many`

Trigger, overwrite:
- The peers are every live instance from the same queryset, and none of them is filtered by whether the field is already loaded.
- If a peer already had the field assigned, or its deferred value was already loaded, the loop overwrites it.
- Example: set `p2.value = "new"` without saving, then read `p1.value`. `p2.value` is reset to the DB value and the pending edit is lost.
- The relational `fetch_many` methods (`ForwardManyToOneDescriptor`, `ReverseOneToOneDescriptor`, GFK) filter with `is_cached`. This one doesn't, so it is inconsistent with them.

Trigger, crash:
- If a peer's row was deleted since the queryset was evaluated, `value_by_pk[instance.pk]` raises `KeyError`. This also breaks the read for the instance the caller actually asked about.
- `refresh_from_db` would raise `DoesNotExist` for the same row. The peer path now behaves differently and fails on an unrelated peer.

Fix direction: only fetch and set for peers where `attname not in instance.__dict__`. Use `.get()` and skip missing rows.

### [Low] A dangling FK on a non-null relation returns `None` under `FETCH_PEERS`
`django/db/models/fields/related_descriptors.py`, `ForwardManyToOneDescriptor.__get__`

Trigger:
- The FK value has no matching row (no DB constraint, or a deleted row), and there are at least two peers.
- `fetch_many` goes through `prefetch_related_objects`, which caches `None`.
- `__get__` now does `return self.field.get_cached_value(instance)` right after fetching, which skips the later `rel_obj is None and not self.field.null` check.
- Result: a non-null FK returns `None` instead of raising `RelatedObjectDoesNotExist`.
- With a single peer or `FETCH_ONE`, `get_object` still raises, so behaviour depends on the mode.

### [Low] The GFK prefetch overrides a custom queryset's fetch mode
`django/contrib/contenttypes/fields.py`, `GenericForeignKeyDescriptor.get_prefetch_querysets`

`queryset.fetch_mode(instances[0]._state.fetch_mode)` is applied to the user-supplied per-content-type querysets too. This silently replaces any `fetch_mode()` the caller set on the custom queryset. Other descriptors leave a user-supplied `Prefetch(queryset=...)` alone.

### Scope and limits
- All 29 changed files were inventoried. I traced the `django/` changes (fetch modes, descriptors, `QuerySet` and `RawQuerySet`, `from_db`, pickling, GFK and related managers). I did not read the docs or the non-defer tests in depth.
- The first finding comes from reading `in_bulk` at the PR head. I have not run it, and no CI results were available. I'd confirm it with a one-line test before relying on it.
- I didn't check the `peers` handling on composite-PK models or in async paths.
