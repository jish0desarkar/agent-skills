# django-19925: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

## Review of PR #19925 (Fixed #21961, database-level `on_delete` for ForeignKey)

I found two defects, both in the check logic. I did not run tests.

### [Medium] A `DB_SET_DEFAULT` FK skips the mixed-variant chain check (E323)
`django/db/models/fields/related.py:1084` (introduced in this PR)

The E323 check sits in the final `elif` of `_check_on_delete`. A field with `on_delete=DB_SET_DEFAULT` takes the earlier `elif on_delete == DB_SET_DEFAULT:` branch, so it never reaches the E323 check.

- **Trigger:** `A.fk = ForeignKey(B, DB_SET_DEFAULT, db_default=...)`, where `B` has a Python-level FK such as `CASCADE` or `PROTECT`.
- **Impact:** the check passes silently, although `DB_CASCADE`, `DB_SET_NULL` and Python variants in the same position are rejected. Deleting a `B` then goes through a Python collector that can't account for the DB-level `SET DEFAULT`, which is the problem E323 exists to prevent.
- **Fix direction:** run the chain check after the branches (an `if`, not the last `elif`), so every non-`DO_NOTHING` variant gets it.

### [Low] Changing only a Python `on_delete` now alters the column and drops/re-creates its FK
`django/db/models/fields/__init__.py:155` (introduced in this PR)

The PR removes `"on_delete"` from `non_db_attrs`. `_field_should_be_altered` therefore sees `CASCADE` → `PROTECT` (or any Python-to-Python change) as a schema change. I read `_alter_field` and confirmed it then drops and re-creates the FK constraint, because `fks_dropped` is non-empty.

- **Impact:** a no-op migration that used to emit no SQL now rebuilds the constraint on PostgreSQL, MySQL and Oracle. The `schema/tests.py` additions only cover DB-variant changes.
- **Possible mitigation:** keep ignoring `on_delete` when both the old and new values are non-`DatabaseOnDelete`. It may also be acceptable and simply worth documenting.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `NestedObjects.can_fast_delete` removed, replaced by `force_collection` | removes code; signature change | `NestedObjects`, `remove_stale_contenttypes` and the base `can_fast_delete` all force collection; nothing else subclasses it | no change |
| `DB_*` added to `SKIP_COLLECTION`, with a forced path in `Collector.collect` | adds a branch beside siblings | `DB_CASCADE` maps to `CASCADE` when forced; `DB_SET_NULL` and `DB_SET_DEFAULT` are skipped in the admin preview (deliberate, since the DB does the work) | OK |
| `_check_on_delete` rewritten | changes returns; branch beside siblings | the `elif` chain shadows the E323 check for `DB_SET_DEFAULT` | finding 1 |
| `Model._check_related_fields` (E050) | iterates input | reverse relations and M2M have no `on_delete` and are skipped | OK |
| `on_delete_db` placeholder added to the FK templates | adds a parameter | the base, MySQL, Oracle, PostgreSQL and SQLite templates, and all three `_create_fk_sql` call sites; a custom backend template without it would just ignore the key | OK |
| `on_delete` removed from `non_db_attrs` | removes a guard | `_field_should_be_altered`, `_alter_field` | finding 2 |
| `DatabaseOnDeleteSerializer` | adds a mode | serializes as `module.NAME`, and `__name__` is set | OK |

Reviewed head `482e53c0a5ad` against merge base `56977b466c33`.

Not checked: tests and CI were not run, and no backend other than SQLite was available. I did not verify the Oracle and MySQL SQL beyond reading the templates. The docs and tests were not reviewed in depth.
