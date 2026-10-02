# django-20718: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

### [High] FK as the final segment of a related lookup crashes the changelist
`django/contrib/admin/utils.py:316-318` (introduced in this PR); consumer at `django/contrib/admin/templatetags/admin_list.py:~240`

Trigger: `list_display = ["parent__other_fk"]`, where the final field is a `ForeignKey` on the related model. `lookup_field` now returns that `ForeignKey` as `f` instead of `None`. `items_for_result` then takes the `else` branch. Because `f.remote_field` is a `ManyToOneRel`, it runs `getattr(result, f.name)`. `f.name` is `other_fk`, which is not an attribute of `result` (the row's model), so this raises `AttributeError`.

Impact: the whole changelist page fails to render. Before this PR the same config rendered the related object's `str()`.

Fix direction: only expose `f` when it is a `BooleanField`/`NullBooleanField`. Alternatively, make the FK branch in `items_for_result` use `value` rather than `result.<f.name>`.

### [High] `get_fields_from_path` raises `FieldDoesNotExist` for related attributes that aren't fields
`django/contrib/admin/utils.py:316-318` (introduced in this PR)

Trigger: a `list_display` or `readonly_fields` entry such as `parent__some_property`, `parent__get_label` or `parent__parent_id`. The `getattr` traversal succeeds, so it reaches the new line. `get_fields_from_path` calls `_meta.get_field()`, which doesn't know properties, methods or attnames, and raises `FieldDoesNotExist`.

Impact:
- This exception was already caught at the top of `lookup_field`. It was not caught inside the `except` handler, so it propagates out.
- Changelist: 500 error.
- Read-only fields: `AdminReadonlyField.contents` catches only `AttributeError`, `ValueError` and `ObjectDoesNotExist`, so it crashes too.
- Dunder traversal to related properties works today, so this is a regression.
- A related `__str__` or callable attribute also reaches this line when `callable(attr)` is false.

Fix direction: wrap the lookup in `try/except FieldDoesNotExist` and leave `f = None` on failure.

### [Medium] Every related lookup now goes through `display_for_field`, not just booleans
`django/contrib/admin/utils.py:316-318`; `admin_list.py:~230-255`; `django/contrib/admin/helpers.py:~286-296`

Trigger: any `a__b` lookup in `list_display` or `readonly_fields`. It now gets a non-`None` `f`.

Impact:
- Fields with `choices`, dates, decimals and the like are rendered by `display_for_field`, and DateField/TimeField/FK columns get the `nowrap` class.
- `AdminReadonlyField` now treats `f.remote_field`/M2M/reverse-relation endpoints specially (`get_admin_url`, `value.all()`).
- For example, `parent__children` (reverse relation) hits the M2M and `ForeignObjectRel` paths with values that don't fit.
- That is a wider change than the title describes, and no release note or test covers it. The test checks only the boolean case.

### [Low] Test and docs gaps
`tests/admin_changelist/tests.py:1771`
- The new test doesn't cover FK-final, non-field attribute, `None` parent, or read-only field cases, which are the paths above.
- `assertNotContains(">False<")` is weak.
- The checklist leaves the docs/release-note box unchecked, and the change is user-visible. The `list_display` docs and release notes should mention it.

**Scope:** `4b6c998..43d4371` (PR head `43d4371`), all 3 changed files. I traced `lookup_field`, `items_for_result` and `AdminReadonlyField.contents` by source reading at that revision. There were no PR comments to check.

**Limits:** I did not run the tests or reproduce the crashes; they come from code tracing. I did not inspect CI.
