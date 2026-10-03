# django-21344: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

## Review of PR #21344: "Fixed #37117 -- Used ModelAdmin.get_queryset() for change form actions."

I found no correctness bugs, and the fix is the right one. I couldn't run the tests: the sandbox has no network and `asgiref` isn't installed, so this is a static review only.

**The fix** (`django/contrib/admin/options.py:2106`): the change form action path now uses `self.get_queryset(request)` instead of `self.model._default_manager.get_queryset()`. That matches the change list, and it matches how `get_object()` already loads `obj` earlier in the same view. Because the queryset comes from `get_queryset()`, the action runs against the same rows and the same filtering and annotations as everywhere else in the admin.

The `selected[0] != str(obj.pk)` check still runs before the queryset is used. `response_action` then filters the queryset by the selected pk, so there is no widening of scope.

**Tests:**
- The new `test_action_changeform_uses_modeladmin_queryset` fails on the old code. `FilteredManager.objects` now hides soft-deleted rows, while the admin's `get_queryset()` uses `all_objects`, so the old queryset would be empty and the restore action would do nothing.
- The test is logged in through `setUp`'s `force_login`.
- The model changes touch only the `FilteredManager` test fixture. The only other users of it are `admin.py` and `test_history_view_custom_qs`, which the PR updates. The old `pk_gt_1` manager had no other references.

**Nits, none blocking:**
1. The PR's own checklist leaves docs and release notes unchecked. The earlier change (#37105) is a new feature, so this is probably covered by its existing notes. Still, a note in `docs/ref/contrib/admin/actions.txt` saying that change form actions receive `get_queryset()` would be useful.
2. The PR title says #37117 but the branch is named `refs-ticket-37105`. That is harmless.
3. `test_history_view_custom_qs` was rewritten for the new fixture, and its history assertions are now less direct than before. It is still valid.

**Verdict:** looks good to merge, ideally after the tests have been run in CI or a full environment.

Findings submitted with the ReportFindings tool:
