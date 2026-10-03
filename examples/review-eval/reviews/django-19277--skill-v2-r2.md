# django-19277: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

No actionable findings in PR #19277 ("Fixed #36260 -- Made bulk_create() work with DB-generated primary keys"). I only read the code and did not run any tests.

**Trace log**

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `_prepare_for_bulk_create` now returns `(objs_with_pk, objs_without_pk)` and puts a `DatabaseDefault` pk in the without-pk list | changes what a function returns; removes/reorders code | Its only caller is `bulk_create` (`query.py:799`), and nothing in the repo overrides it or calls it elsewhere. The `partition` call it replaces is gone, and `partition` has no other use in `query.py`, so dropping the import is safe. | no issue |
| `bulk_create` takes a pk with a `db_default` through the without-pk path | adds a branch beside existing ones | The without-pk path filters out only `AutoField`, so the db_default pk column is still in the INSERT and is sent as `DEFAULT`. On backends that can return columns (PostgreSQL, MariaDB, SQLite 3.35+), `db_returning_fields` includes the field, so the pk is set from the returned row. The with-pk path skips the pk, which was the bug being fixed. | works as intended |
| Pk set by `get_pk_value_on_save` (for example a `UUIDField` default) | state across calls; adds a branch | It is classified after the hook runs: with-pk if the hook set a value, otherwise without-pk. This matches the old behavior. | unchanged |
| Composite pk, explicit pk, `pk=None` | iterates or indexes an input | `_is_pk_set` still handles tuples and `None`. The `isinstance` check runs first, so a composite pk (a tuple) doesn't trip it. | unchanged |
| Backends that cannot return columns (MySQL), or `ignore_conflicts` | introduces state across calls | The pk stays a `DatabaseDefault` object on the instance. The old code left it in the same state, and the updated docs describe this limitation. | pre-existing, not introduced here |

**Scope and limits**
- Head: `5f6736d8479f89dda97b8b5e4f06b1eb912d1f10`. Base: `9608678704a5f89b4c946eea93e90a0f6eb8e3ef`.
- The new test (`test_db_default_primary_key`) only runs where `can_return_rows_from_bulk_insert` is true. I did not run it, and I did not see CI.
- The test doesn't cover mixed batches (some objects with an explicit pk, some without), or the case where the backend can't return columns.
