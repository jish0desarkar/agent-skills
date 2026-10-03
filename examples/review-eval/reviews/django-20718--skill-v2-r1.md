# django-20718: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

### [High] Related FK as the last `list_display` segment now reads the wrong attribute, or crashes
`django/contrib/admin/utils.py:316-317` (introduced in this PR), exposed in `django/contrib/admin/templatetags/admin_list.py:241-246`

`lookup_field` now returns the terminal field `f` for any `a__b` path. Before, it always returned `f = None`. `items_for_result` treats a non-None `f` as a field on `result` itself. For a ForeignKey or OneToOne `f` it runs `getattr(result, f.name)`, where `f.name` is the name on the related model, not on `result`.

- **Trigger:** `list_display = ["parent__owner"]`, where `parent` is a FK on the listed model and `owner` is a FK on the parent's model. This passes the `admin.E108` check, because `get_fields_from_path` resolves it.
- **Impact:** if the listed model has no attribute named `owner`, the changelist raises `AttributeError` and returns a 500. If it has an attribute with the same name, the cell silently shows that object instead of the related one. It worked before this PR, showing `str(value)`.
- **Same-name case:** in the PR's own test models, `GrandChild.parent` and `Child.parent` share a name, so `list_display = ["parent__parent"]` would show the wrong object.
- **Fix direction:** only pass `f` back when it is not a relation, or have `items_for_result` ignore `f.remote_field` when the lookup was a `__` path. The ManyToOneRel branch should use `value`, not `getattr(result, f.name)`.

### [Medium] Every related field type now goes through `display_for_field`, and the new path uses `f` for more than the boolean case
`django/contrib/admin/utils.py:316-317` and `admin_list.py:239-252` (introduced in this PR)

Returning `f` changes the rendering for all related fields, not only BooleanFields.

- Fields with `choices` now show the choice label instead of the raw value.
- Date and time fields get localized formatting and the `nowrap` class.
- `link_to_changelist` is now passed as `avoid_link`.

This is probably the better output, but it is undocumented. The PR's checklist leaves docs and release notes unchecked, and the tests cover only booleans.

The same `lookup_field` is used by `AdminReadonlyField.contents` (`helpers.py:278`). A non-None `f` there takes the `else` branch, so `f.remote_field` is checked against `ManyToManyRel` and `ForeignObjectRel`. That could mis-handle a terminal relation. In practice `readonly_fields` checks reject `__` paths, so I couldn't trigger it.

### Trace log
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `lookup_field` now returns `f` for `a__b` paths | changes return meaning; hands conversion to a callee | 2 callers (`items_for_result`, `AdminReadonlyField.contents`); `display_for_field`; FK branch | finding 1; finding 2 |
| `f = None` moved to the top of the `except` | removes/moves code | all three branches (callable, admin attr, model attr) still get `f = None` | no change |
| New `get_fields_from_path` call | parses input | the chain walk (`getattr` over the parts) runs first; `list_display` checks (`checks.py:931-967`) require the path to resolve, so a bad path would raise `NotRelationField`/`FieldDoesNotExist` at runtime only if checks are silenced | no finding |
| Test and model change | adds a field | `Child.is_active` has a default, and the other `admin_changelist` tests don't depend on it | fine |

**Reviewed:** head `43d4371`, base `4b6c998` (merge base is the `main` tip). I did not run tests or see CI. The FK failure follows from reading the code and I did not run it.
