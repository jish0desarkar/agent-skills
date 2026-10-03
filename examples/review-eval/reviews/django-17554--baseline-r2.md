# django-17554: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

I read the PR #17554 diff but couldn't run it, so these findings come from reading the code only. The sandbox has no `asgiref`, and Python 3.9 is too old for this Django.

The PR adds model field fetch modes (`FETCH_ONE`, `FETCH_PEERS`, `RAISE`). It touches 29 files (about 1050 added lines). The earlier `code-review` run only saw `main` and found no diff. I fetched `refs/pull/17554/head` from `origin` instead.

**Likely bugs, ordered by severity**

1. **`DeferredAttribute.fetch_many` can raise `KeyError`** (`django/db/models/query_utils.py`, new `fetch_many`). It does `value_by_pk[instance.pk]` for every peer. If any peer's row was deleted after the queryset was evaluated, the lookup fails. Reading a deferred field on a different, still-existing instance then raises `KeyError`. A missing peer should be skipped, and `fetch_one` should still run for the instance that was accessed.

2. **`fetch_many` overwrites unsaved changes on peers** (same function). It runs `setattr(instance, attname, ...)` on every peer. Peers whose deferred field was already loaded or modified have those values silently replaced. It should only touch peers where the field is still deferred, as the related-object `fetch_many` methods do with `is_cached`.

3. **`in_bulk` on a `values_list()` queryset** (same function). I haven't confirmed that `.values_list(attname).in_bulk(...)` returns `{pk: value}` on this base. If `in_bulk` returns `{pk: (value,)}` tuples, the `setattr` assigns tuples. The tests may catch this, so run `defer` first.

4. **`ForwardManyToOneDescriptor.__get__` skips the null check after a fetch** (`related_descriptors.py`). After `fetch_mode.fetch(...)` it returns `get_cached_value(instance)` directly, so the "`rel_obj is None and not self.field.null` → `RelatedObjectDoesNotExist`" check below it never runs. `FETCH_ONE` is safe because `get_object` raises `DoesNotExist` itself. Under `FETCH_PEERS`, `fetch_many` goes through `prefetch_related_objects`. A dangling or missing target would leave `None` cached, and a non-nullable FK would return `None` instead of raising.

5. **Generic relations ignore the fetch mode of a custom queryset** (`contenttypes/fields.py`, GFK prefetch). `queryset.fetch_mode(instances[0]._state.fetch_mode)` always overrides the mode on a user-supplied custom queryset. The same happens in the `ForwardManyToOneDescriptor.get_queryset` path.

6. **Pickling and `peers`.**
   - `ModelState.__getstate__` drops `peers`, so unpickled instances in `FETCH_PEERS` mode silently fall back to `fetch_one`. This is probably intended, but it is undocumented.
   - `peers` is a list shared across every instance from one queryset. It is rebuilt per `ModelIterable.__iter__` call, but `iterator(chunk_size=...)` holds weakrefs to the whole result set.

**Minor**
- `QuerySet.create()` sets `fetch_mode` after `save()`, so signals fired during the save see the default mode.
- `fetch_modes.py`: `Raise.fetch` uses `from None`, which hides the original context, and relies on `fetcher.field.name`. That is why the `ReverseOneToOneDescriptor.field` shim was added.
- Tests for items 1, 2 and 4 look absent from the diff (I haven't read the whole test diff).

I couldn't remove the temporary `pr-17554` branch because `.git/config` is locked in the sandbox. Your working tree still has only `README.rst` and `notes.local.txt` as before.

I haven't posted anything to the PR. To confirm items 1–4, run `tests/runtests.py defer many_to_one one_to_one generic_relations prefetch_related` in an environment with Django's dependencies installed.

Findings submitted with the ReportFindings tool:
