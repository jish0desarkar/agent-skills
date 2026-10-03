# django-21344: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

I found no actionable defects in PR #21344, "Fixed #37117 -- Used ModelAdmin.get_queryset() for change form actions." I didn't run any tests.

The one production change is in `django/contrib/admin/options.py:2106`. It replaces `self.model._default_manager.get_queryset()` with `self.get_queryset(request)` for change-form actions.

| Behavior | Checked | Result |
|---|---|---|
| Queryset passed to change-form actions now comes from `get_queryset(request)` | The object is already fetched through `get_object()`, which uses `get_queryset(request)`, so the action queryset now matches the object that was loaded. `response_action` always narrows to `pk__in=selected`. | No problem |
| Change-form actions could apply to more than the one object | `selected` must equal `[str(obj.pk)]`, and `response_action` forces `select_across = False` for `CHANGE_FORM`. | The queryset can only ever hold the one object, so a custom `get_queryset()` can only narrow it or add annotations |
| Subclasses and overrides | `get_queryset(request)` is the documented overridable hook and is already called with `request` elsewhere in the same view. | Compatible |
| Test changes (`FilteredManager` gets a `deleted` flag, with `objects` filtering on it and `all_objects` unfiltered; `CustomManagerAdmin` uses `all_objects`) | Grepped for `pk_gt_1` and `FilteredManager` at the head commit. | No stale references remain. The new test fails on the old code, because `_default_manager` would exclude the soft-deleted row. |

Reviewed head `9f82b61ef217` against merge base `5364575041`. The PR checklist leaves docs and release notes unchecked. A one-line behavior change like this probably needs no release note, but a maintainer may want to confirm.

Findings submitted with the ReportFindings tool:
