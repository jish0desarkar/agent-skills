# django-19534: stock Claude Code, run 1

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #19534 ("Fixed #35738 -- Deprecated double-dot variable lookups") and found two problems. I did not run the code: the local `python3` is too old for Django (`datetime.UTC` is missing), so both findings come from reading the code.

The `code-review` skill reported that the PR couldn't be found. The ref does exist on `origin` as `refs/pull/19534/head`, so I fetched it into a local branch named `pr-19534` and reviewed the diff myself. I switched back to `main` afterwards.

1. **False positive on string literals (`django/template/base.py:558`).** The check `".." in str(filter_expression.var)` also matches quoted literals. For a constant like `{{ "a..b" }}`, `FilterExpression` stores the already-resolved string as `var`, so the deprecation warning fires even though no lookup happens. When the deprecation ends and the commented-out `raise` is enabled, those valid templates would fail with a `TemplateSyntaxError`. The fix is to warn only when `var` is a `Variable` whose `lookups` contains an empty string.
2. **Test and coverage gaps (`tests/template_tests/syntax_tests/test_basic.py`).** The tests cover only `{{ doubledot..lookup }}`. There is no negative test for `{{ "a..b" }}` or `{{ x|default:".." }}`, so the first problem isn't caught. The warning also fires only for `{{ }}` variables, not for tags such as `{% if a..b %}` or `{% for x in a..b %}`, and the release note doesn't say so.

The release note, the deprecation timeline entry, the use of `skip_file_prefixes`, and the comments marking the code to change when the deprecation ends look fine.

Findings submitted with the ReportFindings tool:
- django/template/base.py:558 (correctness) The check `".." in str(filter_expression.var)` also matches quoted string literals, not just variable lookups.
  Failure scenario: For a constant such as `{{ "wait.." }}` or `{{ "a..b" }}`, FilterExpression sets `var` to the already-resolved string (see `Variable(constant).resolve({})` around line 755). The check then sees `..` and emits the double-dot lookup deprecation warning, even though no lookup happens. Once the deprecation ends and the commented-out `raise self.error(...)` is enabled, those valid templates would fail with a TemplateSyntaxError. The fix is to warn only when `var` is a `Variable` whose `lookups` contains an empty string, or at least to skip the check when `var` is a `str`. I did not run this, because the local Python is too old for Django.
- tests/template_tests/syntax_tests/test_basic.py:398 (test-coverage) The new tests cover only `{{ doubledot..lookup }}`.
  Failure scenario: There is no negative test showing that `{{ "a..b" }}` or `{{ x|default:".." }}` does not warn, so the false positive above is not caught. The check also covers only `{{ }}` variable tokens. Double-dot lookups inside tags, such as `{% if a..b %}` or `{% for x in a..b %}`, are not covered, and this is not documented in the release note.
