# django-20718: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

**PR #20718 — "Fixed #36926 -- Made admin use boolean icons for related BooleanFields in list_display"**

I read the diff and the code around it. I haven't run any of this. The first two problems below come from reading the code paths, not from reproducing them.

The PR makes `lookup_field()` return the real final field for `a__b` paths, so the changelist can show boolean icons. The goal is fine, but the method is too broad. It sets `f` for every related lookup, not only booleans. Both callers of `lookup_field()` use `f is None` to mean "not a model field", so every `__` lookup now takes the model-field display path.

**Bugs**

1. **Crash on `__` lookups that end in a property or other non-field attribute** (`django/contrib/admin/utils.py:316-318`).
   - The `getattr` loop accepts anything that resolves, such as a property or a reverse manager.
   - `get_fields_from_path()` then calls `_meta.get_field()`, which raises `FieldDoesNotExist`.
   - Example: `list_display = ["parent__some_property"]`, or a path ending in `child_set`.
   - These lookups worked before. Now they raise an uncaught `FieldDoesNotExist`, which becomes a 500.
   - `admin_list.py` only catches `ObjectDoesNotExist`. `helpers.py` catches `AttributeError`, `ValueError` and `ObjectDoesNotExist`, so it doesn't catch this either.

2. **Crash on `__` lookups that end in a ForeignKey** (`admin_list.py:~238`).
   - When `f` is a ForeignKey, `f.remote_field` is a `ManyToOneRel`, so the changelist runs `getattr(result, f.name)`.
   - `f.name` belongs to the related model, not to `result`.
   - Example: `parent__category`, where `category` is a FK on `Parent`. The changelist raises `AttributeError`, because `Child` has no `category`.

3. **Behavior changes for other field types** (`helpers.py:~278-300` and `admin_list.py`).
   - Readonly fields: a related ForeignKey or M2M now goes through `get_admin_url(f.remote_field, …)` or `value.all()`. Those paths expect a model-level relation or a manager, not a related-path value.
   - Changelist: related fields with `choices`, dates and so on now get `display_for_field` formatting and `nowrap` classes. Related-path values used to be formatted as plain values.
   - Some of this may be an improvement, but nothing tests it, and the ForeignKey and M2M cases are likely wrong.

**Suggested fix**
- Resolve the field only when it's safe, and fall back to `f = None` otherwise:
  - Wrap `get_fields_from_path` in `try/except (FieldDoesNotExist, …)`.
  - Keep the result only if it is a concrete, non-relational field. For example, accept `isinstance(f, models.BooleanField)`, or at minimum `not f.is_relation`.
- Alternatively, leave `f` as `None` and pass the boolean-ness through another way. One option is to return a lightweight `attr` with `.boolean = True`, which the `f is None` branch already reads.

**Tests**
- The new test only covers the happy path (`parent__is_active`).
- Add cases for a related property, a related FK, a related `choices` field and a related date. Add a readonly-field case too.
- The `assertNotContains(">True<")` check is brittle. It would also fail if unrelated page content contained that text.
- The new test has no ticket reference, and the PR adds no release note or docs update. `docs/ref/contrib/admin/index.rst` documents `list_display` lookups.

**Housekeeping**
- I fetched the PR head into a local branch, `pr-20718`.
- The first review pass looked at the wrong thing: only your uncommitted `README.rst` change, not the PR. That review also couldn't find the PR ref.
- Nothing was posted to GitHub.

Findings submitted with the ReportFindings tool:
