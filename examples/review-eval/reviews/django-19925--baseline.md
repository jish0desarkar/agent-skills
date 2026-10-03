# django-19925: stock Claude Code, run 1

The session's final review, unedited except that scratch paths were removed.

---

This is a static review of PR #19925, "Fixed #21961 -- Added support for database-level delete options for ForeignKey". I read the Python changes in `django/` (33 files changed in total). I did not run the tests because the sandbox only has Python 3.9, and this Django needs 3.11 or later (`datetime.UTC`).

The code review skill reported nothing at first because it only looked at local branches. I fetched `refs/pull/19925/head` as the local branch `pr-19925` and reviewed that, then switched back to `main`. Your working tree is as it was (`README.rst` modified, `notes.local.txt` untracked).

I found no definite correctness bugs. These are the points I'd raise on the PR, most important first:

1. **`DB_SET_DEFAULT` skips the mixed-chain check** (`related.py`, `_check_on_delete`). The check for fields.E323 (database-level and Python-level `on_delete` mixed in a reference chain) sits in an `elif` after the `DB_SET_DEFAULT` branch. A `DB_SET_DEFAULT` FK pointing at a model with Python-level FKs is therefore never flagged, although `DB_SET_NULL` and `DB_CASCADE` are. The same applies to the `SET_NULL` and `SET_DEFAULT` error branches. Those fields also skip E323 whenever they have an error.

2. **`_create_on_delete_sql` swallows errors** (`base/schema.py`). It uses `try/except AttributeError` to detect a plain `CASCADE` function. An `AttributeError` raised inside `on_delete_sql` or `fk_on_delete_sql` would be silently turned into "no ON DELETE clause", so the FK would be created without the requested behaviour. `isinstance(on_delete, DatabaseOnDelete)` is safer.

3. **Public import removed.** `NoFastDeleteCollector` is deleted from `remove_stale_contenttypes.py`, and `NestedObjects.can_fast_delete` is deleted. Third-party code that imported or overrode them will break. This is probably fine, but it isn't mentioned in the release notes.

4. **Python-level changes now alter the schema.** Dropping `"on_delete"` from the non-database attributes in `fields/__init__.py` means a change like `CASCADE` to `PROTECT` now counts as a schema alteration. That drops and recreates the FK constraint, or remakes the table on SQLite, for a change that has no database effect. Check this is intended and covered by tests.

5. **Style:** the Oracle template splits `%(on_delete_db)` and `s` across two string literals (`oracle/schema.py`). It works but reads like a typo.

6. **Behaviour to confirm in the docs:**
   - `DB_SET_NULL` and `DB_SET_DEFAULT` have no `forced_collector`. With `force_collection=True`, as in the admin delete confirmation page, those relations are skipped.
   - Python-side signals and cascades don't run for any database-level variant.

The tests need Python 3.11 or later, so run `delete schema invalid_models_tests migrations admin_utils contenttypes_tests` in a suitable environment before merging.

Findings submitted with the ReportFindings tool:
