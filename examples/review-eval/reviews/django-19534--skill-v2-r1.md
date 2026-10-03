# django-19534: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] A string literal containing `..` triggers the double-dot warning
`django/template/base.py:558` (introduced in this PR)

Trigger: `{{ "see more.." }}` or `{{ "a..b" }}`. This is a quoted constant at the start of the expression.

- `FilterExpression.__init__` resolves a leading constant with `Variable(constant).resolve({})` (`base.py:~772`) and stores the resulting `str` in `filter_expression.var`.
- The new check, `".." in str(filter_expression.var)`, runs on that string, so it matches the text content.
- No lookup is involved, so the `RemovedInDjango70Warning` is a false positive. A literal ending in an ellipsis, such as `{{ "Loading.." }}`, is a realistic case.
- Once the deprecation ends and the commented-out `raise` is enabled, those templates would fail to compile.

Fix direction: check only when `filter_expression.is_var` is true, and test `filter_expression.var.lookups` for an empty-string component. That is more precise than a substring check, and it also stops `{{ ._x }}`-style edge cases from matching by accident.

I could not run this. The only interpreter here is Python 3.9, and this Django needs a newer one. The finding comes from reading the code at the head commit.

### [Low] The check covers only `{{ }}` variable nodes
`django/template/base.py:558` (introduced in this PR; may be intentional)

Tags that take a variable argument go through `compile_filter` too, for example `{% if a..b %}`, `{% for x in a..b %}` and `{% with v=a..b %}`. They never reach this branch, so they still resolve `..` silently. Once the deprecation ends, the error will cover `{{ }}` but not these tags. The PR description presents this as a smaller patch than the parse-time alternative in #18551, so this may be a deliberate trade-off. Either way, say it in the release note.

### [Low] `self.origin` can be `None`
`django/template/base.py:562` (introduced in this PR)

`Parser.__init__` defaults `origin=None`. `Template` always passes an origin, so normal use is fine. A third-party caller that builds `Parser(tokens)` directly and parses `{{ a..b }}` would now get `AttributeError: 'NoneType' object has no attribute 'name'` instead of a warning. The existing `self.origin.template_name` use at `base.py:620` has the same exposure, so this is minor. Guarding with `getattr(self.origin, "name", ...)` would avoid it.

### Trace log
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `Parser.parse` warns on `..` in a variable token | changes meaning; parses input; hands conversion to library | `FilterExpression.__init__` (constant vs `Variable`), `Variable.__init__`, `Template.compile_nodelist` | findings 1 and 3 |
| Warning only on the `{{ }}` branch | adds a branch beside siblings | the BLOCK branch and `compile_filter` users | finding 2 |
| `skip_file_prefixes=django_file_prefixes()` | handles caller-visible state | the usage matches the existing deprecation helper | no issue |
| Tests and docs | — | the test uses the cached loader and checks the warning fires only once | fine; no test covers a string literal |

Reviewed head `628c6dab82d779506d3ba38c12243441dadd0d1c`, merge base `017d7f6f12e597e6179de7ffdf330a52c2b22053`.

I did not run the tests, and I did not see CI. The finding in the first section is verified by code reading only.
