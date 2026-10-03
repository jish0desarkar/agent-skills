# django-21344: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

No actionable findings on PR #21344 (reviewed statically; I did not run tests).

**What the PR does:** `ModelAdmin._changeform_view` now builds the change-form action queryset with `self.get_queryset(request)` instead of `self.model._default_manager.get_queryset()` (`django/contrib/admin/options.py:2106`). The rest of the PR is test changes.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| Change-form action queryset now comes from `get_queryset(request)` | changes what a function returns/means; removes or "simplifies" code | `_changeform_view` is the only call site. `response_action` just applies `.filter(pk__in=selected)` and passes the result to the action. | No problem found. |
| Consistency with the object lookup | adds a branch beside existing ones | `obj` is loaded earlier through `get_object()`, which also calls `get_queryset(request)`. The action queryset is now built the same way, so `obj` is always in it. Before, a custom queryset could include `obj` while the default manager excluded it, so the action would silently get an empty queryset. | This fixes that mismatch. |
| Overrides of `get_queryset` | signature/overridable method | `get_queryset(request)` is the documented signature. The changelist already calls it the same way. A `get_queryset` that depends on the request, or one that is expensive, now runs once more per action POST. That is the same cost the changelist pays. | No problem found. |
| `select_across` | state across calls | `response_action` forces `select_across=False` for `CHANGE_FORM`, so the action never runs on the whole queryset, only on the one selected pk. | No problem found. |
| Test model and manager changes (`FilteredManager`) | adds a field | The `pk_gt_1` manager and the original `objects` manager are gone. Grep over `tests/` shows no other users. The history test is rewritten to use the new `all_objects` manager. | Consistent. |
| New test `test_action_changeform_uses_modeladmin_queryset` | adds a branch beside existing ones | The `setUp` in `AdminCustomQuerysetTest` already calls `force_login`, so the missing explicit login in the new test is fine. The test would fail on the old code, because `_default_manager` excludes the deleted row. | Valid regression test. |

### Not covered by the review
- The PR template shows the docs and release-notes checkbox unchecked. This is a bug fix to a feature added recently, so a release note is probably not needed. That is for a merger to decide, and I did not check it.
- I did not run the tests or see CI results.
- The review is at the head commit as fetched.

**Commits:** head `9f82b61ef21712bfc94af302d094fedbbea413f0`, base (merge base) `53645750412efa1e9013004040db328bd515e0f1`.
