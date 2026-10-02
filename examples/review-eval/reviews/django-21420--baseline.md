# django-21420: stock Claude Code (built-in code-review)

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #21420 ("Fixed #37139 -- inlines crash on parent models with `db_default` on primary key") and found no correctness bugs. I read the diff only and didn't run the tests.

The skill's first pass found nothing to review, because it looked at the local `main` branch. I fetched the PR ref from the local mirror and reviewed that diff.

The fix in `Model._is_pk_set()` now treats a `DatabaseDefault` value as unset. It does this for a single primary key and for each part of a composite one. `DatabaseDefault` is already imported in `base.py`, and the logic is correct.

I have two minor findings:
1. **Inverted helper name** (`django/db/models/base.py:713`): the nested helper `_is_set` returns True when the value is not set. The call `not (_is_set(pk_val) or ...)` therefore reads backwards. I'd rename it to `_is_unset` or `_is_empty`.
2. **Weak inline test** (`tests/inline_formsets/tests.py:127`): `test_add_form_uuid_pk` posts `INITIAL_FORMS=1` with no primary key and only asserts the formset is invalid. The name says "add form", which doesn't match that setup. The test would also pass for unrelated validation failures, so it should check the actual error or the `INITIAL_FORMS=0` path.

Findings submitted with the ReportFindings tool:
- django/db/models/base.py:713 (simplification) The nested helper `_is_set` returns True for None/DatabaseDefault, i.e. when the value is unset, so its name is inverted. The call site `not (_is_set(pk_val) or ...)` therefore reads backwards.
  Failure scenario: No runtime failure. The logic is correct, but a later maintainer who trusts the name could 'fix' the condition and break `_is_pk_set()` for None and db_default primary keys. Rename it to `_is_unset` or `_is_empty`. The helper could also be a module-level or static function instead of being redefined on every call.
- tests/inline_formsets/tests.py:127 (test-coverage) `test_add_form_uuid_pk` posts INITIAL_FORMS=1 with no pk and only asserts `is_valid()` is False. The name says 'add form', which doesn't match that setup, and the test doesn't check the error or that the formset no longer crashes.
  Failure scenario: The test would also pass if the formset were invalid for an unrelated reason, such as a missing parent pk field. Assert on the specific formset error, or on the add-form (INITIAL_FORMS=0) path that the ticket describes. Rename the test to match what it checks.
