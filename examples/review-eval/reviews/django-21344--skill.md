# django-21344: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

I found no actionable defects in PR #21344.

**What changed:** `django/contrib/admin/options.py:2106` now builds the change-form action queryset with `self.get_queryset(request)`. Before, it used `self.model._default_manager.get_queryset()`.

**Why it holds up:**
- `get_queryset(request)` is the same source the change list uses. `response_action` then narrows it with `queryset.filter(pk__in=selected)` at `options.py:1881`, and the POST is already checked so that exactly one selected pk equals `obj.pk`. The action can only touch that one row.
- `obj` is fetched earlier in `changeform_view` through `get_object`, which also uses `get_queryset`. The action and the form now see the same object set. Before the fix, a custom `get_queryset()` that was looser or stricter than the default manager could make the two disagree.
- The test models were changed so the default manager differs from the admin's queryset: `FilteredManager.objects` now excludes soft-deleted rows, and `CustomManagerAdmin.get_queryset()` uses `all_objects`. `test_action_changeform_uses_modeladmin_queryset` restores a soft-deleted object, so it would have failed on the old code.
- I found no other users of the renamed `pk_gt_1` manager in `tests` or `docs`. The updated history test still covers the same behavior.

**Optional, not defects:**
- The PR description leaves the docs/release-notes box unchecked. This is a bug fix for a recent change from tickets #12090 and #37105. If that feature hasn't shipped in a release yet, no note is needed. If it has, a note may be wanted.
- Actions that call `queryset.update()` now run against whatever the `get_queryset()` override returns. That follows from the PR's intent and matches change-list behavior, so I don't count it as a problem.

**Scope and limits:**
- I reviewed merge-base `5364575` to head `9f82b61`. The head matched the PR metadata, and the PR has no comments.
- This was source inspection only. I didn't run the tests, and I didn't look at CI results.
- I didn't change your checkout and posted nothing to GitHub.
