# django-21344: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

## Review of PR #21344: "Used ModelAdmin.get_queryset() for change form actions" (#37117)

**No actionable findings.** I found no defects I could prove.

**The change.** `django/contrib/admin/options.py:2106` replaces `self.model._default_manager.get_queryset()` with `self.get_queryset(request)` in the change form action path.

- **Selection is still narrowed to the one object.** `response_action` applies `queryset.filter(pk__in=selected)` when `select_across` is false, and `select_across` is forced to `False` for `CHANGE_FORM`. The view also checks that exactly one id was posted and that it equals `obj.pk`. The wider queryset therefore can't leak other rows to the action.
- **No new reachable gap.** The object itself comes from the admin's `get_object`, which already uses `get_queryset`. The action now sees the same row set as the change list, as the PR intends.
- **Behavior change.** An admin whose `get_queryset()` is narrower than the default manager now gives actions an empty queryset for rows it hides. That is intended, and the object couldn't be opened in that admin anyway.
- **Test fixtures.** The `FilteredManager` changes move the default manager to `deleted=False` and keep an `all_objects` manager. I found no other users of the removed `pk_gt_1` manager at the PR head.
- **New test.** `test_action_changeform_uses_modeladmin_queryset` posts a restore action on a soft-deleted object. It would get an empty queryset under the old code, so it covers the fix. The existing history test was rewritten to match the new fixtures.

**Minor, non-blocking.**
- The PR checklist leaves the docs/release-notes box unchecked. `docs/ref/contrib/admin/actions.txt` doesn't say which queryset change form actions receive. A short sentence saying it comes from `ModelAdmin.get_queryset()` would help. A release note is probably unnecessary if the change form actions feature hasn't shipped yet, since the commits say these are unreleased 6.1/6.2 changes.
- The PR body says the work follows #12090 and #37105 and is "consistent with the change list path". I didn't check those tickets.

**Scope and limits.**
- I reviewed `5364575...9f82b61` (PR head, fetched and verified against PR metadata). The diff is four files: one source line plus tests.
- I did this by reading source at the PR head, not the working tree.
- I did not run the tests or look at CI results. The test conclusion above comes from reading the test, not from running it.
- The PR had no comments.
