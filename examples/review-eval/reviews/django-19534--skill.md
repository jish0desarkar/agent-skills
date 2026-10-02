# django-19534: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] The deprecation warning also fires for string literals and translated strings that contain `..`
`django/template/base.py:558` (introduced in this PR)

Trigger: a template such as `{{ "Loading..." }}`, `{{ "Wait.."|upper }}` or `{{ _("Please wait..") }}`.
- `FilterExpression.__init__` resolves quoted constants at parse time (`Variable(constant).resolve({})`, base.py:~769), so `filter_expression.var` is the plain string `Loading...`, not a `Variable`.
- `_("...")` is a `Variable` whose `.var` is the whole `_("Wait..")` text.
- `".." in str(filter_expression.var)` therefore matches both cases.

Impact: templates with ellipsis-style text, which is common in UI strings, get a `RemovedInDjango70Warning` claiming "double-dot lookups" when no lookup is involved. The commented-out follow-up, which raises `TemplateSyntaxError("Variable contains '..'")` once the deprecation ends, would then reject valid templates outright. Running with `-W error` makes the warning an error today.

Fix direction: only check real variable lookups. Test `filter_expression.is_var` (and `var.lookups is not None`) and look for an empty segment in `var.lookups`, e.g. `"" in var.lookups`. Add a test for `{{ "a..b" }}`, `{{ _("a..b") }}` and `{{ x|default:"a..b" }}` that asserts no warning.

### Notes (not defects)
- Only `{{ }}` variable tokens are checked. `{% if a..b %}`, `{% for x in a..b %}` and filter-argument variables (`|default:a..b`) still resolve through `Variable("a..b")` without a warning, so the deprecation is incomplete. The PR description says this is a deliberately smaller patch, so I'm not treating it as a bug.
- The warning's `Template:` line uses `self.origin.name`. Check that `origin` is never `None` for string-constructed templates. `Template("...")` normally creates an `Origin`, and I did not find a failing path.

**Scope:** PR #19534 at head `628c6dab`, merge-base `017d7f6` (the current `main`). I read the full diff (`base.py`, the docs, and the tests in `test_basic.py`) and traced `FilterExpression.__init__` and `Variable.__init__` at the head SHA with `git show`.

**Limits:**
- I did not run any tests. My first attempt to execute the PR code failed because the shell has no `python` on PATH, so the finding rests on source tracing, not a runtime reproduction.
- I did not inspect CI.
- The PR had no comments to verify.
