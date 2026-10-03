# django-20009: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

### [High] Oracle `JSONIn.as_oracle` returns an unparenthesized `OR` chain
`django/db/models/fields/json.py`, `JSONIn.as_oracle` (introduced in this PR). I read this from the code and could not run it on Oracle.

- **Trigger:** on Oracle, filter on a `JSONField` with a `JSONNull()` in the list and any other condition ANDed with it. For example, `filter(value__in=[JSONNull(), [1]], pk__gt=0)`. Excluding the lookup or combining it with `|` or `~Q` is affected too.
- **Why it breaks:** each part is wrapped as `(sql)`, but the joined result `"(a) OR (b)"` is returned without an outer pair of parentheses. `WhereNode.as_sql` appends a lookup child's SQL as-is and joins siblings with `AND`. The query becomes `(a) OR (b) AND pk > 0`, and `AND` binds tighter than `OR`.
- **Impact:** rows matching the `JSONNull` branch ignore every other filter, so the query returns wrong rows. The new tests only filter on the lookup alone, so they would not catch it.
- **Fix direction:** return `"(%s)" % " OR ".join(sql_parts)`, which is what `In.split_parameter_list_as_sql` does for its `OR` chains.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `JSONIn.as_oracle` splits the lookup into exact lookups joined by `OR` | adds a branch beside siblings; changes what is returned | `WhereNode.as_sql` child joining, `In.split_parameter_list_as_sql` as the sibling | finding 1 |
| `get_prep_lookup` now wraps every direct value in `Value(v, lhs.output_field)` when any expression is present | changes meaning; hands conversion to a callee | `Value.as_sql` calls `output_field.get_db_prep_value`, which runs `get_prep_value`; `RelatedIn` and `RelatedLookupMixin` already prepare values with the target field before calling super; the 11 `super().get_prep_lookup()` callers are unchanged | no defect found. Wrapping non-`str` values is new, and the previous raw ints went into `ExpressionList` unprepared |
| `JSONIn.resolve_expression_parameter` also handles `Value` params | adds a branch; iterates and parses input | uses `param.value` on Oracle, and `JSON_EXTRACT(%s,'$')` on MySQL and SQLite | not verifiable without those backends. `JSONNull.value` is `None` on the Oracle path, which I could not check |
| Key-transform SQL builders moved into `ProcessJSONLHSMixin` | moves code; side effects | the Oracle path template and delimiter comment, MySQL, and SQLite output are the same as before; `tuple(params)` became `params`, which stays valid only if `params` is a tuple | the generated SQL is unchanged |
| `KeyTransformIn(JSONIn)` | signature or override change | `process_lhs` returns early for a `KeyTransform` lhs, so key lookups skip the new top-level wrapping; the `Value`-param branch and the Oracle `JSONNull` split now also apply to key transforms | no defect found |
| New top-level `value__in` on `JSONField` | adds a branch beside siblings | Postgres and native-JSON backends fall through to the base `process_lhs`, so they are unchanged | no defect found |

Reviewed head `e732971cc8a1` against base `e726254a380f`. I did not run the tests, and I could not exercise MySQL, MariaDB or Oracle here. One correction to the report text above: `JSONNull.value` being `None` is my reading, not something I confirmed.
