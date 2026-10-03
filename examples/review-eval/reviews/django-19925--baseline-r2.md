# django-19925: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #19925, "Fixed #21961 -- Added support for database-level delete options for ForeignKey", and reported three findings. I read the diff but didn't run any code or tests, because the local Python is too old to import this Django. The `/code-review` skill found nothing at first because it only looked at local branches. I fetched `refs/pull/19925/head` from `origin` myself, read the full diff against `main`, then switched back to `main`.

1. **`DatabaseOnDelete.__call__ = DO_NOTHING`** (`django/db/models/deletion.py:89`): assigning a plain function as a class attribute makes it a bound method. Calling `DB_CASCADE(collector, field, sub_objs, using)` would pass 5 arguments to a function that takes 4, and raise `TypeError`. `Collector` skips these values, so nothing in Django triggers it today, but third-party code that calls `on_delete` directly would break. The fix is a proper `__call__` method or `staticmethod`.
2. **Mixed-chain check (E323) skipped for some fields** (`django/db/models/fields/related.py:1093`): the check sits in an `elif` after the `SET_NULL`, `SET_DEFAULT` and `DB_SET_DEFAULT` branches. A `DB_SET_DEFAULT` field that references a model using Python-level `CASCADE` therefore never gets E323.
3. **Broad `except AttributeError`** (`django/db/backends/base/schema.py:1633`): `_create_on_delete_sql` uses it to tell database variants from Python ones. It would also hide a real `AttributeError` inside `fk_on_delete_sql`, and the foreign key would be created without `ON DELETE`. An `isinstance(..., DatabaseOnDelete)` check would avoid that.

Everything else I checked looked fine:
- the SQL templates on each backend,
- the migration serializer,
- the alter-field path, which now recreates the foreign key when only `on_delete` changes because `on_delete` was removed from the ignored attributes,
- the `force_collection` replacement for the old `can_fast_delete` overrides.

Your `README.rst` edit and `notes.local.txt` are untouched.

Findings submitted with the ReportFindings tool:
- django/db/models/deletion.py:89 [PLAUSIBLE] (correctness) `__call__ = DO_NOTHING` assigns a plain function as a class attribute, so it binds `self` and receives 5 positional args instead of the 4 DO_NOTHING accepts.
  Failure scenario: Any code that invokes `field.remote_field.on_delete(collector, field, sub_objs, using)` with a DB_CASCADE/DB_SET_NULL/DB_SET_DEFAULT value raises TypeError (takes 4 positional arguments but 5 were given). Collector currently skips these via SKIP_COLLECTION, so the bug is latent, but third-party code or later changes that call on_delete directly will break. Fix: define `def __call__(self, collector, field, sub_objs, using): pass`, or wrap it in staticmethod. I found this by reading the code and did not run it, because the local Python is too old to import this Django.
- django/db/models/fields/related.py:1093 [PLAUSIBLE] (correctness) The mixed database/Python on_delete chain check (E323) sits in an `elif` after the SET_NULL, SET_DEFAULT and DB_SET_DEFAULT branches, so it is skipped for those fields.
  Failure scenario: A model has `FK(Parent, DB_SET_DEFAULT, db_default=...)`, and Parent has `FK(Grandparent, CASCADE)`. The `on_delete == DB_SET_DEFAULT` branch is taken, so fields.E323 is never raised and the unsupported mixed chain passes the system checks. The same happens for a FK with SET_NULL or DB_SET_NULL that also has an E320 or E321 error: only that one error is reported, and E323 appears later, once the first error is fixed.
- django/db/backends/base/schema.py:1633 [PLAUSIBLE] (correctness) `_create_on_delete_sql` uses `try/except AttributeError` to detect non-database variants, which can hide real AttributeErrors raised inside `on_delete_sql` or `fk_on_delete_sql`.
  Failure scenario: A backend's `ops.fk_on_delete_sql` has a bug that raises AttributeError. The error is swallowed and the FK is created without ON DELETE, so the schema silently differs from the model. Use `isinstance(on_delete, DatabaseOnDelete)` instead.
