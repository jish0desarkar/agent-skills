# django-21420: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

### [High] `save()` replaces a `db_default` primary key with `None`, so the insert sends NULL
`django/db/models/base.py:712-723`, read together with `_save_table` at `base.py:1097-1099` (introduced in this PR)

Trigger: save a new instance whose single-field primary key uses only `db_default`, for example `ParentUUIDPk()` or `PrimaryKeyWithDbDefault()` followed by `.save()`.

- Before this PR, `_is_pk_set()` returned True for the `DatabaseDefault` placeholder. `_save_table` skipped the key-generation branch and the INSERT used the database default.
- Now `_is_pk_set()` returns False, so `_save_table` calls `meta.pk.get_pk_value_on_save(self)`.
- `Field.get_pk_value_on_save` (`fields/__init__.py:794-796`) returns `None` when the field has no Python `default`, and `_save_table` does `setattr(self, attname, None)`.
- That overwrites the `DatabaseDefault`. `pk_set` stays False, but `insert_fields` only excludes `meta.auto_field`, and a UUID or Integer pk field isn't one. The pk column is therefore inserted as NULL.

Impact: plain `Model.save()` and `create()` on models with a `db_default` primary key would likely fail with an IntegrityError or store a wrong key. This is the exact feature the PR is trying to fix. Composite pks are unaffected because `CompositePrimaryKey.get_pk_value_on_save` keeps non-None values.

Fix direction: skip `get_pk_value_on_save` when the pk value is a `DatabaseDefault`. Alternatively, leave `_is_pk_set` alone and fix the inline-formset caller instead. Add a save-and-refresh test for a single-field `db_default` pk.

I traced this from source and did not run it, so I'm marking it likely rather than proven.

### [Low] `_is_set` is inverted
`django/db/models/base.py:712-716`

The helper returns True when the value is unset (`None` or `DatabaseDefault`) and is used as `not (_is_set(...) ...)`. The result is correct but misleading. Rename it to `_is_unset`.

### [Low] Inline-formset test is weak
`tests/inline_formsets/tests.py:116-126`

The test only asserts `is_valid() is False` for a form with `INITIAL_FORMS=1` and no pk. That doesn't show the crash is gone or that the right error is raised. Assert on the specific formset or form errors.

**Scope:** PR #21420 at head `667250d4`, diffed against base `4bbc27c` (`main`). Source inspection only, using `git show` and `git grep` on the PR head. There were no PR comments, I did not look at CI, and I ran no tests.
