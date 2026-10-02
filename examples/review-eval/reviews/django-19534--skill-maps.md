# django-19534: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] Warning fires on string literals containing `..`, such as `"Loading..."`
`django/template/base.py:558` (introduced in this PR)

Trigger: the check is `".." in str(filter_expression.var)`. When the expression starts with a quoted constant, `FilterExpression.__init__` stores the resolved string in `.var`, not a `Variable` (`base.py:770-773`, `self.var = var_obj` at line 799). So `{{ "Loading..." }}`, `{{ "wait.."|upper }}` and `{{ _("Please wait...") }}` all contain `..` and match. None of these is a lookup.

Impact: the PR deprecates a variable lookup that maps to the empty string. This check also emits `RemovedInDjango70Warning` for valid literal text, including the common ellipsis case. The message ("double-dot lookups … lookup of the empty string") would send users looking for a bug that isn't there. The commented-out "elevate to error" step would later make `{{ "Loading..." }}` a `TemplateSyntaxError`, breaking valid templates.

Fix direction: only check when `filter_expression.is_var` is true, which is already set at `base.py:800`. Alternatively check `filter_expression.var.lookups` for an empty-string entry. Add a test with a quoted literal containing `..`. The new tests in `test_basic.py` only cover variable lookups, as far as I could see.

### Notes (not findings)
- Only `{{ … }}` variable nodes are checked. `{% if a..b %}`, `{% with x=a..b %}`, tag arguments and filter arguments (`|default:a..b`) are not. Those paths are still deprecated-in-name only, so the deprecation coverage is partial. This is probably intentional given the "smaller patch" framing in the PR description, but the release note could say so.
- `self.origin.name` assumes a non-`None` origin. `Template` always supplies one, and `base.py:620` already dereferences it, so I'm not reporting it.

### Scope and checks
- Reviewed PR #19534 at head `628c6dab82d779506d3ba38c12243441dadd0d1c` against base `017d7f6` (merge-base diff, 4 files). The PR is open with no comments.
- I read the diff and traced `FilterExpression.__init__` and `Variable.__init__` with `git show` at the PR head. I did not re-check the live head after fetching.
- I did not run any tests. A runtime probe of the finding was not possible because the sandbox only has Python 3.9, and Django needs a newer version. The finding comes from source inspection.
- I did not inspect CI. The docs entries (`deprecation.txt` under 7.0, `releases/6.1.txt`) look consistent with the change.
