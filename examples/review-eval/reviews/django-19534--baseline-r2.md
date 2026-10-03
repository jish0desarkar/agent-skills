# django-19534: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

Confirmed by reading the code: for a quoted literal, `FilterExpression.var` is the resolved string, not a `Variable` (`base.py:755`). I couldn't run it, because the sandbox's `python3` is too old for this Django checkout (`datetime.UTC` is missing).

## Review of PR #19534: "Fixed #35738 -- Deprecated double-dot variable lookups"

The PR adds a `RemovedInDjango70Warning` in `Parser.parse()` when a `{{ ... }}` variable contains `..`. It also adds the deprecation timeline, release notes and tests.

### Findings

**1. False positives on string literals (correctness, likely the main issue).** `django/template/base.py`, in the new `if ".." in str(filter_expression.var)` check.
- The check runs on the whole `filter_expression.var`. For a quoted constant that is the resolved literal string, so any literal containing `..` triggers it.
- `{{ "Wait..." }}`, `{{ "a..b" }}` and `{{ _("Loading...") }}` would all emit the deprecation warning, although none of them is a lookup.
- The commented-out future code raises `TemplateSyntaxError` for this case. When the deprecation ends, templates with ellipsis literals would stop compiling.
- Fix: only check when `filter_expression.is_var` is true, and ideally check the lookup parts of the `Variable` (`.lookups`) for an empty string, not a substring. Add a test with `{{ "Wait..." }}`.

**2. Coverage gap (design).** The check only covers `{{ }}` output nodes.
- `{% if a..b %}`, `{% for x in a..b %}`, `{% with v=a..b %}`, and filter arguments such as `{{ x|default:a..b }}` still resolve the lookup silently.
- The cleaner place is `Variable.__init__`, or `FilterExpression.__init__` where `Variable(var)` is built. There the lookups are split and an empty one can be detected for every tag.
- If the narrow scope is intentional ("smaller patch" than #18551), say so in the docs.

**3. Possible `AttributeError` on `self.origin.name` (minor).** `Parser.origin` defaults to `None` when `Parser` is built directly, so `self.origin.name` would raise instead of warning. `Template` always sets it, so this only affects direct `Parser` use.

**4. Warning attribution (nit).** The warning is emitted at parse time with `skip_file_prefixes=django_file_prefixes()`. With the cached loader it fires only on the first compile, which the test acknowledges. That is fine, but the message embeds template name and line, so the default warning filter won't deduplicate repeats.

### Docs and tests
- The `deprecation.txt` entry is in the 7.0 section and the 6.1 release note is placed correctly. The wording "is removed" in `deprecation.txt` matches the surrounding entries.
- The tests cover debug on and off, and the cached loader. They don't cover string literals (finding 1) or non-output tags (finding 2).

Nothing was posted to the PR, and I left the checkout on `main`. The PR is fetched locally as the branch `pr-19534`.

Findings submitted with the ReportFindings tool:
