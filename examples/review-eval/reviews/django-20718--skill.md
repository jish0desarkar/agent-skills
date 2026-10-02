# django-20718: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

### [High] Related FK or OneToOne targets in `list_display` now crash the changelist
`django/contrib/admin/utils.py:316-317` (introduced in this PR), which feeds `django/contrib/admin/templatetags/admin_list.py:~243`

Trigger:
- `lookup_field` now returns the last field of the path as `f` for any `a__b` lookup, not only booleans.
- `items_for_result` then takes its `else` branch and runs `isinstance(f.remote_field, models.ManyToOneRel)` followed by `getattr(result, f.name)`.
- `f` belongs to the related model, but `getattr` is called on the row's own model.
- Example: `GrandChildAdmin.list_display = ["parent__parent"]`, where `Child.parent` is a ForeignKey. `f` is `Child.parent`, and `getattr(grandchild, "parent")` happens to resolve (wrong object). With `["parent__other_fk"]`, where the name is absent on the row's model, it raises `AttributeError`, and the changelist returns a 500.
- Before this PR, `f` was `None` for these columns, so they went through `display_for_value` and rendered as text.

Impact: a configuration that worked before can now crash the page or show the wrong object. OneToOne fields hit the same branch, because `OneToOneRel` subclasses `ManyToOneRel`.

Fix direction: either set `f` only when the last field is a `BooleanField`, which is all this PR needs, or make the changelist resolve FK values from the related object instead of `result`. Also add a test with an FK or OneToOne final segment.

### [Medium] Every non-boolean related column is now formatted by `display_for_field`
`django/contrib/admin/utils.py:316-317` (introduced in this PR)

Trigger: `parent__name`, `parent__birthday`, and any related field with `choices`, a DateField, and so on.

Impact: all of these now render via `display_for_field` instead of `display_for_value`. Choice fields show their labels, dates and numbers are localized, and the cell gets the `nowrap` class.
- This is arguably an improvement, but it is a visible change for every existing related column that the ticket and the release notes don't mention.
- The existing `parent__name` tests pass only because CharField output is unchanged.

### [Low] Extra work per row, and no docs
`django/contrib/admin/utils.py:316-317`, plus the PR checklist, where the docs box is unchecked
- `get_fields_from_path` re-resolves the whole path for every row and column. It could be computed once per column.
- `docs/ref/contrib/admin/index.txt` (`list_display`) and the release notes aren't updated, even though this changes user-visible behavior.

**Scope and checks**
- I reviewed the merge-base-to-head diff of `43d4371` against `4b6c998`, which matches the PR metadata. I did not recheck the live head afterwards.
- I traced `lookup_field` and its callers: `admin_list.items_for_result` and `helpers.AdminReadonlyField.contents`.
- I did not trace `readonly_fields`. I believe the system checks reject `a__b` there, so the helper path is likely unreachable. I did not verify that.
- I did not run any tests. The crash finding comes from reading the source, not from executing it.
- I did not look at CI.
