# django-20718: stock Claude Code, run 1

The session's final review, unedited except that scratch paths were removed.

---

I couldn't run the tests. The available `python3` is too old, because Django needs `datetime.UTC`. This review is from reading the code only.

## Review of PR #20718: boolean icons for related fields in `list_display`

The change makes `lookup_field()` return the final model field for `a__b` lookups, so the changelist renders `parent__is_active` with the boolean icon. The goal is reasonable, but the approach has problems.

### Problems

1. **`list_display = ["parent__parent"]` (a ForeignKey as the final field) probably breaks.**
   - `lookup_field()` now returns the final FK field. `items_for_result` (`admin_list.py:~238`) then takes the `ManyToOneRel` branch and calls `getattr(result, f.name)`.
   - `f.name` belongs to the related model, not to `result`. That raises `AttributeError` or reads the wrong attribute.
   - Before the PR, these lookups went through the plain-value path and rendered fine.
   - I'd expect the same trouble for one-to-one and many-to-many final fields. The PR adds no test for either.

2. **`get_fields_from_path()` can raise `FieldDoesNotExist` and crash the changelist.**
   - The attribute walk accepts anything reachable with `getattr`, including properties and methods on the related model.
   - The new `get_fields_from_path(opts.model, name)` call is unguarded. It raises on any such name. `items_for_result` only catches `ObjectDoesNotExist`.
   - Wrap it in `try/except FieldDoesNotExist`, or build the field while walking the path.

3. **The new call uses the wrong starting model and does a second traversal.**
   - It starts from `opts.model`, which is `obj._meta.model`. For deferred or proxy instances this can differ from the model the admin declares.
   - The path is also walked a second time, after the `getattr` walk.
   - Resolving the field during the existing `for part in ...` loop would fix both.

4. **Behaviour changes beyond booleans.**
   - Every related lookup (`parent__name`, dates, decimals, choices) now goes through `display_for_field` instead of `display_for_value`. Output may change slightly for fields such as `FileField`, `JSONField` and choice fields. This isn't mentioned in the PR or tested.
   - Related fields also lose the `attr.empty_value_display` and `short_description` handling, because `attr` is no longer the same object.
   - `nowrap` is now added for related date and FK columns.

5. **`AdminReadonlyField.contents()` in `helpers.py:278` shares `lookup_field`.**
   - A `readonly_fields = ["parent__x"]` entry will now get a non-None `f`. That sends it down the `ForeignObjectRel`/`display_for_field` branches.
   - The PR doesn't test or discuss this.

### Smaller points

- **Tests:**
  - The test asserts `alt="True"` and `alt="False"`. It should also check that `parent__name`, a non-boolean related field, still renders as plain text.
  - There are no tests for a FK final field, a `None` parent, or `readonly_fields`.
  - `assertNotContains(">True<")` is a weak check.
- **Model change:** adding `is_active` to `Child` in `tests/admin_changelist/models.py` is fine, but check that other tests aren't affected by the new column.
- **Docs:** the PR checklist leaves the docs/release-notes item unchecked. `docs/ref/contrib/admin/index.txt` should mention that related boolean fields get icons. The ticket may also warrant a release note.
- **Style:** `f = None` is moved to the top of the `except` block, which is correct. The `LOOKUP_SEP in name` check sits inside the branch where `attr is sentinel` was handled, which makes the control flow harder to follow.

### Verdict

Request changes. The FK-final-field regression (1) and the unguarded `get_fields_from_path` (2) are the blockers. A narrower fix would resolve the field and return it only when it is a `BooleanField` or a `NullBooleanField`-style field. Other related lookups would then keep the existing rendering path.

I only read the PR. I left `main` checked out and didn't post anything to GitHub.

Findings submitted with the ReportFindings tool:
