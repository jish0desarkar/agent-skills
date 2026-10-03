# django-20009: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] User-supplied non-JSON `Value()` in a JSON `__in` list is now wrapped as JSON on MySQL and Oracle
`django/db/models/fields/json.py:413-428` (introduced in this PR; I could not run it on MySQL or Oracle)

Trigger: `Model.objects.filter(value__key__in=[Value("x")])` or `[Value(1), ...]` on MySQL, MariaDB or Oracle. The `Value` has an inferred `CharField` or `IntegerField` output field, not `JSONField`.

Impact:
- The old `KeyTransformIn` skipped anything with `as_sql`, so these values were compared as-is.
- `JSONIn.resolve_expression_parameter` now also treats every `expressions.Value` as a direct value.
- On Oracle it builds `JSON_OBJECT('value' VALUE %s FORMAT JSON)`, which fails for the non-JSON string `x`.
- On MySQL it builds `JSON_EXTRACT(%s, '$')`, which fails with "Invalid JSON text".
- The new tests only pass `Value(..., JSONField())`.

Fix direction: take the new branch only when `param.output_field` is a `JSONField`, or when the `Value` was built from a raw value in `get_prep_lookup`.

### Trace log
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `FieldGetDbPrepValueIterableMixin.get_prep_lookup` now wraps every value in `Value(v, lhs.output_field)` when any element is an expression | changes meaning; removes or simplifies code | The 4 overriding or super-calling `get_prep_lookup` implementations (`related_lookups`, `postgres/lookups`, `array`, `tuple_lookups`). `Value.as_sql` calls `get_db_prep_value`, which calls `get_prep_value`, so prep still happens at compile time. `None` still compiles to `NULL`. Non-string values used to keep their raw type and now take the field's output type. | No defect found. The type change for non-strings is intended. |
| New `JSONIn` lookup, with `KeyTransformIn` as a subclass | adds a branch beside siblings; hands conversion to a library call | The lhs wrapping is skipped for `KeyTransform`, so there is no double wrap. The `params * 2` and `(*params, path) * 3` parameter ordering is correct. Postgres is untouched. | No defect found for the lhs paths. |
| `JSONIn.resolve_expression_parameter` now also handles `Value` | changes what a function accepts | `JSONNull` returns a one-element `params`, so the sqlite `params[0]` access is safe. | Finding 1 |
| New `JSONIn.as_oracle` that splits the lookup into OR'd exact lookups when `JSONNull` is present | adds a branch | `Lookup` can't compile via `as_oracle` unless the exact lookup defines it. I did not verify every exact lookup class. | Not confirmed. I couldn't run Oracle, so this is a residual risk. |
| `KeyTransform` helpers moved into `ProcessJSONLHSMixin` | removes or moves code | The SQL templates and parameter tuples are identical to the old code. `tuple(params)` became `params * 2`, which is fine for the list or tuple that callers pass. | Equivalent |

Reviewed head `e732971cc8a1`, base `e726254a380f`. I did not run tests, and I did not see CI. No MySQL or Oracle backend was available, so the SQL for those two is read, not executed. Apart from the finding above, I found nothing else actionable.
