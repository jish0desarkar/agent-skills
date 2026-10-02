# django-21344: stock Claude Code (built-in code-review)

The session's final review, unedited except that scratch paths were removed.

---

**PR #21344 — "Fixed #37117 -- Used ModelAdmin.get_queryset() for change form actions": no blocking issues found.** I couldn't run the tests, so the verdict comes from reading the diff.

**The fix.** In `_changeform_view` (`django/contrib/admin/options.py:2106`), change form actions were given `self.model._default_manager.get_queryset()`. The PR changes that to `self.get_queryset(request)`. This is correct and matches how the changelist builds the queryset. Without it, an overridden `ModelAdmin.get_queryset()` is bypassed. That means an action can receive an empty queryset for an object the admin can show, or reach objects the admin deliberately excludes. `obj` is already fetched through `get_object()`, which uses `get_queryset()`, so the page and the action now use the same queryset.

**The tests.** The new test, `test_action_changeform_uses_modeladmin_queryset`, would fail without the fix:
- It builds a soft-deleted object that the default manager hides.
- `CustomManagerAdmin` exposes it through `all_objects`.
- It posts a "Restore" action and checks the object is restored.

`setUp` logs in with `force_login`, so the missing explicit login in the new test is fine.

I also looked at the reworked `FilteredManager` model. The only other references are the admin registration and `test_history_view_custom_qs`, which the PR updates.

**Minor, non-blocking:**
- Making `deleted=False` the default manager changes what other code sees. I found no other users in the repo, so this is fine.
- If this is a ticketed Django change, it may need a release-notes or docs mention. The diff has none, and it's a small bugfix, so that may be intentional.

**Not verified.** I couldn't run `admin_views` tests: the system Python is too old (no `datetime.UTC`) and Django isn't installed. Please run `./runtests.py admin_views.tests.AdminCustomQuerysetTest` in a proper environment.

**State of your checkout.** I fetched the PR as local branch `pr-21344` and switched back to `main`. Your uncommitted `README.rst` change and `notes.local.txt` are untouched. The review skill noted that the `README.rst` change is just a stray local comment line.

Findings submitted with the ReportFindings tool:
