# django-19925: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] Changing a Python-level `on_delete` now drops and recreates the FK constraint
`django/db/models/fields/__init__.py:155` (introduced in this PR)

Trigger: a migration that only changes a ForeignKey's `on_delete` between Python-level variants, for example `CASCADE` to `PROTECT`, or `SET_NULL` to `CASCADE`.

Impact: the PR removes `"on_delete"` from `Field.non_db_attrs`. The generated SQL for those variants is identical, because none of them emits an `ON DELETE` clause. Previously `_field_should_be_altered()` (`base/schema.py:1671`) ignored the change. Now `on_delete` stays in the deconstructed kwargs and the two fields compare as different. `_alter_field` (`base/schema.py:955`) then drops and re-adds the FK constraint, and SQLite remakes the whole table. That is expensive on large tables, and the migration holds locks for no schema change. The fix could keep `on_delete` ignored unless either side is a `DatabaseOnDelete`, or compare the emitted `on_delete_sql` instead.

I traced this by reading the head commit. I could not run it, because the sandbox Python lacks `datetime.UTC`.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `on_delete` removed from `non_db_attrs` | changes meaning; removes code | `_field_should_be_altered`, `_alter_field` FK drop path | finding 1 |
| `%(on_delete_db)s` added to the FK SQL templates | adds a parameter | every template and call site: base `sql_create_fk`, the inline and column-inline FK templates, `add_field`, `create_model`, `_create_fk_sql`, and the mysql, oracle, postgresql and sqlite3 overrides | passed everywhere. The split Oracle literal is concatenated at import, so it is valid |
| `DatabaseOnDelete` and `SKIP_COLLECTION` in `Collector` | adds a mode; changes meaning | `can_fast_delete`, `collect`, `NestedObjects`, `remove_stale_contenttypes`. The old `can_fast_delete` overrides are replaced by `force_collection`, and both callers pass it | consistent. `DB_SET_NULL` and `DB_SET_DEFAULT` are skipped under forced collection, which is deliberate because the database handles them |
| `_check_on_delete` rewritten as an `elif` chain | adds a branch beside siblings | the E320 and E321 messages are unchanged for the old cases. `DB_SET_NULL` reuses E320 | no defect |
| `Model._check_related_fields` (E050) | iterates inputs | `get_fields()` includes reverse relations, but their `remote_field` has no `on_delete`, so they are skipped. M2M and GFK are skipped too | no defect. A multi-table-inheritance child's implicit `CASCADE` parent link counts as Python-level, so it cannot also have a DB-level FK. That is a design limitation, not a bug |
| `DatabaseOnDeleteSerializer` | handles a new input type | registered by `isinstance`. It emits `django.db.models.deletion.DB_*`, matching how the function variants serialize | no defect |
| `GenericForeignKey` check E006, and `supports_on_delete_db_default` | adds a feature flag | the flag is `False` on MySQL and Oracle, and E324 honours `required_db_features` | no defect |

**Reviewed:** head `482e53c0a5ad0d7c216a067c2cb5eeaeabf3e5f7`, base and merge base `56977b466c33ca3da14a1ed2609172425a76a34e`.

**Not checked:**
- I did not run the tests, so no database backend was exercised.
- I did not read the tests and docs hunks line by line.
- I did not see CI results.
- I did not execute `DatabaseOnDelete` identity behaviour under `deepcopy`. I read the code instead, and the field paths I read (`Field.__deepcopy__`, `clone`) don't deep-copy `on_delete`.

I found no other actionable defects.
