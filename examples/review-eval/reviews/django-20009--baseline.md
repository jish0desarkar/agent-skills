# django-20009: stock Claude Code, run 1

The session's final review, unedited except that scratch paths were removed.

---

I read the diff for PR #20009 but couldn't run its tests, so these findings come from reading the code only. The system `python3` is too old for this Django checkout: it has no `datetime.UTC`. The PR changes three files (`json.py`, `lookups.py` and the JSONField tests). It makes top-level `JSONField__in` work on MySQL and Oracle by adding a `JSONIn` lookup and sharing the per-backend LHS handling with `KeyTransform`.

I found no definite bugs. There are two risks worth checking before merge:

1. **`lookups.py`, `FieldGetDbPrepValueIterableMixin.get_prep_lookup`:** When an `__in` list mixes expressions with plain values, every plain value is now wrapped as `Value(v, lhs.output_field)`. Before, only `str` values were wrapped, and they were run through `get_prep_value()` first. This code is shared by all `In` lookups, not only JSON ones.
   - Related-field `__in` lists that mix an `F()` or `Subquery` with model instances or pks could now fail or serialize differently. `ForeignKey.get_db_prep_value` may not accept a model instance.
   - Please run the `lookup`, `queries`, `expressions` and `foreign_object` suites, and add a test with a model instance mixed with an expression.
2. **`json.py`, `JSONIn.process_lhs`:** For a non-`KeyTransform` LHS, this now wraps the LHS in `JSON_EXTRACT` on MySQL and in the `JSON_TYPE` CASE on SQLite. On Oracle it wraps the LHS in `COALESCE(JSON_VALUE…, JSON_QUERY…)`. It does this even when the RHS is a subquery or a column reference rather than literal values.
   - That could change comparison semantics, or break, for `json_field__in=Model.objects.values("json_field")`.
   - I saw no test for this case.

Smaller points:
- `_process_as_oracle` returns `params * 2`. The old code returned `tuple(params) * 2`. This is harmless if `params` is a list, but it no longer normalizes the type.
- `JSONIn.as_oracle` only rewrites the lookup as ORs of exact lookups when the RHS holds a `JSONNull()` instance. That check relies on `Value` equality being identity-based, which works but is fragile. Also, a bare `None` in the list becomes `Value(None, JSONField)`, not `JSONNull`. Please confirm that's intended, given the deprecation note in `JSONExact`.

`git worktree remove` and `git branch -D` failed with "could not lock config file .git/config" (sandbox write limits), so the `pr-20009` branch, and probably the worktree, are still there. Your `README.rst` edit and `notes.local.txt` are untouched, and you're still on `main`.

Findings submitted with the ReportFindings tool:
