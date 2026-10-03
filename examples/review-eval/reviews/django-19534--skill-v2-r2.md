# django-19534: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] Quoted string literals containing `..` trigger the deprecation warning
`django/template/base.py:558` (introduced in this PR)

Trigger: a template containing `{{ "wait.. what" }}`, `{{ 'a..b' }}` or `{{ _("Loading...") }}`. Anything with two consecutive dots inside a quoted or translated literal does it.
- `FilterExpression.__init__` resolves a quoted constant straight to a plain `str` (`base.py:770-775`), so `filter_expression.var` is that string and not a `Variable`.
- The new check, `".." in str(filter_expression.var)`, then matches the literal's text, not a lookup.
- The `Variable.__str__` path (`base.py:962`) only covers real variables. The literal path has no `is_var` guard.

Impact: a `RemovedInDjango70Warning` with the message "double-dot lookups … maps to a lookup of the empty string". There is no lookup in that template, so the user can't act on it. Ellipsis-style text (`...`) in literals is common, and in Django 7.0 the commented-out `raise` would make those templates fail to compile. Warnings-as-errors setups, including Django's own test runner, hit this immediately.

Fix direction: only check when `filter_expression.is_var` is true, or check `".." in filter_expression.var.var` on the `Variable`. Add a test with a quoted literal containing `..`.

### [Low] `self.origin` can be `None`, which makes the warning path raise `AttributeError`
`django/template/base.py:562` (introduced in this PR)

Trigger: `Parser(tokens)` built directly. `origin` defaults to `None` (`base.py:502`) and the parser is then driven through `parse()` with a `{{ a..b }}` token.
- `Template` always sets an `Origin`, so normal rendering is unaffected.
- A direct `Parser` user such as third-party tooling would hit it.

Impact: `AttributeError: 'NoneType' has no attribute 'name'` in place of a warning.

Fix direction: use `getattr(self.origin, "name", ...)`, or skip the Template line when there's no origin.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `Parser.parse` warns on `..` in variable tokens | iterates, indexes, splits or parses an input; hands conversion to a callee | `FilterExpression.__init__` (constant vs variable branch), `Variable.__str__`, `Template.__init__` origin handling, direct `Parser(` callers in `tests/template_tests/test_parser.py` | findings 1 and 2 |
| Added branch beside the existing `{{ }}` handling | adds a branch beside siblings | Block-tag arguments (`{% if %}`, `{% for %}`, `{% with %}`) build their own `FilterExpression`/`Variable` objects and don't go through this hunk, so `{% if a..b %}` is not warned about. The PR text only mentions `{{ }}` and the tests only cover that, so I'm not reporting it as a defect. | noted, not a finding |
| `RemovedInDjango70Warning` with `skip_file_prefixes=django_file_prefixes()` | changes meaning of a call | Other uses of `django_file_prefixes` in the repo | consistent |
| Cached loader | state across calls | The new test shows the warning fires only on the first load, which is expected. | fine |

Reviewed head `628c6dab82` against base `017d7f6f12` (merge base). I did not run any tests or check CI. I confirmed finding 1 by reading the code, not by running it.
