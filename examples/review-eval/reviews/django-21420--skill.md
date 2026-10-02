# django-21420: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

### [High] `save()` on a model with a `db_default` primary key now inserts NULL
`django/db/models/base.py:712-723` (introduced in this PR)

Trigger: save a new instance whose pk has only `db_default` and no `default`. Examples are `PrimaryKeyWithDbDefault` in `tests/basic/models.py:51` and `ParentUUIDPk` added by this PR.
- Before this PR, `_is_pk_set()` returned True for the `DatabaseDefault` placeholder. `_save_table` (`base.py:1097-1100`) skipped the "no pk" branch and inserted `DEFAULT`.
- With the patch, `_is_pk_set()` returns False.
- `_save_table` then calls `meta.pk.get_pk_value_on_save(self)`. That method returns `None` when the field has no `default` (`fields/__init__.py:794-796`).
- `setattr` overwrites the `DatabaseDefault` with `None`.
- `insert_fields` still includes the pk, because it is not `meta.auto_field`. `pre_save` returns `None`, so the INSERT sends NULL for the pk.

Impact: creating a `db_default` pk model fails with an IntegrityError, or stores a NULL or wrong pk on backends that allow it. That includes `ParentUUIDPk(...).save()` and any `ModelForm` or inline save of such a model. This likely breaks existing tests such as the `PrimaryKeyWithDbDefault` save tests in `basic`. I traced this from source and did not run it.

Fix direction: leave `_save_table` and the pk placeholder semantics alone, and narrow the fix. For example, make the inline formset check (`forms/models.py:1131`, and probably line 963) treat a `DatabaseDefault` pk as unset. Or keep `_is_pk_set()` as it was and add a separate helper for the form callers. If the change stays in `_is_pk_set`, `_save_table` must skip the `get_pk_value_on_save` overwrite when the pk is a `DatabaseDefault`.

### [Medium] Other `_is_pk_set()` callers change behavior
About 25 call sites in `django/` (list from `git grep -n "_is_pk_set" "$HEAD_SHA" -- django`) are affected. Examples:
- `related_descriptors.py:534`, `799`, `1125` raise "needs a primary key" errors.
- `query.py:729-733`, `961` (`bulk_create`, `bulk_update`).
- `base.py:649`, `1323`, `1352`, `1442`, `1578`, `1613`.

Impact: these now treat an instance whose pk is a `DatabaseDefault` as having no pk. The update-vs-insert logic in `bulk_create` and `save` shifts on that path. I traced `_save_table` only, not the rest.

### [Low] The new inline test passes without exercising the fix
`tests/inline_formsets/tests.py:116-126` (introduced in this PR)

Trigger: the test posts data with the `child_set-` prefix. The formset's default prefix comes from `get_accessor_name`, which is `childuuidpk_set` for `ChildUUIDPk`.

Impact: the management form is missing, so `is_valid()` is trivially False. The test would pass without the fix and doesn't cover the crash from #37139. The asserted outcome is also a weak check: why should the formset be invalid? Pass `prefix=` or use the correct keys, and assert the intended behavior.

### Naming nit
In `_is_pk_set`, the inner helper `_is_set` returns True for the *unset* values (`None`, `DatabaseDefault`). It is used negated as `_is_set(pk_val) or ...`. The name is inverted, so rename it to something like `_is_empty`.

**Scope:** PR #21420 head `667250d4`, base `4bbc27c8` (merge-base equal to base). I read the diff and traced `_save_table`, `get_pk_value_on_save` and the formset code with `git show` and `git grep` at that SHA. I did not run tests, and the PR has no comments. I didn't recheck whether the head moved after fetching.
