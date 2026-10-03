# django-20009: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

**Review of PR #20009** (Fixed #36689, top-level JSONField `__in` on MySQL and Oracle). I read the diff only and ran no tests. The earlier skill run reviewed the wrong thing, so I fetched the PR ref (`pr-20009`) myself.

## Bug

**Oracle: the `OR` expansion for `JSONNull` isn't parenthesised.** This is in `JSONIn.as_oracle`, `django/db/models/fields/json.py`.

- **Problem:** it returns `"(a) OR (b)"` with no outer parentheses. `WhereNode` joins sibling lookups with ` AND ` and doesn't wrap them, so the `OR` binds wrongly.
- **Example:** `filter(value__in=[JSONNull(), [1]], pk=1)` compiles to `(a) OR (b) AND pk = 1`. That returns any row matching `a`, whatever its `pk`.
- **Fix:** return `"(%s)" % " OR ".join(sql_parts)`.
- **Tests:** the new Oracle `JSONNull` tests have no sibling condition, so they wouldn't catch this. Adding `pk=obj.pk` to `test_filter_in` or `test_key_in` would.

## Minor points

- **Wider change in `FieldGetDbPrepValueIterableMixin.get_prep_lookup`** (`django/db/models/lookups.py`):
  - **What changed:** when an `__in` list mixes expressions and plain values, every plain value is now wrapped in `Value(v, lhs.output_field)`. Before, only strings were. This affects all fields, not only JSON.
  - **What I didn't check:** I didn't confirm that fields with custom `get_prep_value` or `get_db_prep_value` behave the same on that path. A test with `F()` mixed with plain ints, dates and FK values would help.
- **Missing tests:** `test_in` only covers lists and dicts. It has no top-level scalars (string, int, bool) or `None`. Those take different branches in the SQLite, MySQL and Oracle `JSON_EXTRACT`/`JSON_VALUE` handling that `JSONIn` introduces.

The refactor into `ProcessJSONLHSMixin` looks behaviour-preserving for `KeyTransform`.

Findings submitted with the ReportFindings tool:
