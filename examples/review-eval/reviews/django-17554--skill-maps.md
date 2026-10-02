# django-17554: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

### [High] `FETCH_PEERS` deferred-field batch fetch assigns 1-tuples instead of the field value
`django/db/models/query_utils.py:292-297` (`DeferredAttribute.fetch_many`, introduced in this PR)

Trigger: `objs = list(Model.objects.fetch_mode(FETCH_PEERS).defer("value"))`, then `objs[0].value` with at least two peers.

- `fetch_many` calls `.values_list(attname).in_bulk(pks)`. The field name defaults to `pk`, which is not in `values_select`.
- So `in_bulk` (`query.py:1229-1240`) takes the `ValuesListIterable` branch. It rewrites the query to `values_list("pk", "value")` and strips the key with `itemgetter(slice(1, None))`.
- Each dict value is therefore `("x",)`, not `"x"`, and `setattr(instance, attname, value_by_pk[instance.pk])` stores the tuple.

Impact:
- `p1.value` and every peer's `.value` return `("x",)` instead of `"x"`. This is wrong data on the main path of the new feature.
- The new tests only check query counts (`tests/defer/tests.py:189-211`), so they don't catch it.

Fix direction: use `.in_bulk(pks)` on a plain `.only(attname)` queryset and read `getattr(obj, attname)`. Or use `values_list("pk", attname)` with an explicit mapping. Add a value assertion to the tests.

### [Medium] Same `fetch_many` overwrites loaded values and can raise `KeyError`
`django/db/models/query_utils.py:297` (introduced in this PR)

Trigger:
- Peer B already has the field loaded or deferred-then-fetched, with an unsaved local change. Peer A then triggers a fetch.
- Or a peer row was deleted after the load.

Impact:
- `fetch_many` doesn't filter to instances where `attname not in instance.__dict__`. The FK, one-to-one and GFK `fetch_many` methods do skip cached instances.
- The unconditional `setattr` clobbers B's in-memory edit with the DB value.
- A missing row raises `KeyError` from `value_by_pk[instance.pk]`.

Fix direction: skip instances that already have the attname in `__dict__`, and skip pks absent from the result.

### Scope and checks
- Reviewed `bee6456...f52490c` (PR head, base `main` at `bee6456`). I read the full diff of `django/`. I read only the `tests/defer` tests, and the docs and other test files were not traced.
- I traced `in_bulk` at the PR head by reading the source. I did not run any tests or code, so the tuple behavior is established by source reading only. Running `p1.value` in a quick test on the PR head would confirm it.
- I did not look at CI or existing PR comments (the offline mirror has none).
- Not covered: the GFK and related-manager `fetch_mode` propagation, and the pickling of `ModelState`/`fetch_mode`. I saw nothing wrong in them, but I did not trace them in depth.
- One thing I did not report: `GenericForeignKey.get_prefetch_querysets` now calls `.fetch_mode(...)` on a user-supplied custom queryset, which replaces any fetch mode that queryset already had. This looks like a design choice, so check whether it's intended.
