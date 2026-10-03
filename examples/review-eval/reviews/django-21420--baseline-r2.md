# django-21420: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

I reviewed the PR's single commit (667250d, "Fixed #37139"). I didn't run the tests. The fix looks correct, and I have a few minor comments.

The first pass through the review skill only looked at your uncommitted `README.rst` edit, so I fetched `refs/pull/21420/head` from `origin` and reviewed it directly.

**What it does:** `Model._is_pk_set()` now treats a `DatabaseDefault` primary key value as "not set", for both single and composite keys. Before, a parent with `db_default` on its primary key looked like it already had a pk, and the inline formset crashed. `DatabaseDefault` is already imported in `base.py`, and `PrimaryKeyWithDbDefault` already exists in `tests/basic`, so the new tests have what they need.

**Comments:**
1. **Inverted helper name (`django/db/models/base.py:712`).** The nested `_is_set(value)` returns `True` when the value is *not* set (`None` or `DatabaseDefault`). The surrounding `not (_is_set(...) or ...)` is correct, but the name reads backwards. Rename it to `_is_unset`, or `_is_empty`. Also, "Empty value when db_default is used" sits oddly under the `or`. It would be clearer as a comment on the `DatabaseDefault` check.
2. **Weak inline test (`tests/inline_formsets/tests.py`, `test_add_form_uuid_pk`).** It only asserts `formset.is_valid() is False`. That passes for any validation failure and doesn't show that the crash is fixed. The data also sets `INITIAL_FORMS=1` with no `-0-id` or `-0-uuid` value, so the form is invalid because of the missing initial data. Assert on the specific error, or on the behaviour you actually want. A test that saves a valid new child under a parent that has a UUID default would be more convincing.
3. **Composite-key test (`tests/composite_pk/tests.py`).** `PostDbDefault` has `tenant` with `default=1`, and the test then passes a tenant explicitly. `assertIsNotNone(post.id)` mainly checks that `id` holds a `DatabaseDefault` object. Asserting `isinstance(post.id, DatabaseDefault)` would say what the test means. A case where only the second field is a `DatabaseDefault` is already covered by this model.
4. **Missing release note.** If the crash affects a released version, the PR has no `docs/releases/*.txt` entry. Django usually wants one for a backported regression fix.

I found no correctness bugs in the code change itself.

Findings submitted with the ReportFindings tool:
