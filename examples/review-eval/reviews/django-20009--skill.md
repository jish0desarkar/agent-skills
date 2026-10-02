# django-20009: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

### [High] Oracle `__in` with `JSONNull()` emits an unparenthesized `OR` chain
`django/db/models/fields/json.py:480` (introduced in this PR)

Trigger: on Oracle with `supports_primitives_in_json_field`, run `Model.objects.filter(value__in=[JSONNull(), [1]], other=1)`. The same happens for `value__key__in=[JSONNull(), ...]` combined with any other condition.

Impact: `JSONIn.as_oracle` returns `"(a) OR (b)"` without an outer pair of parentheses. `WhereNode` joins leaf lookups with ` AND ` and does not wrap them. The SQL becomes `(a) OR (b) AND other = 1`, and `AND` binds tighter than `OR`. The query then returns rows that don't satisfy `other=1`. The new tests don't catch this because they filter on the `__in` lookup alone, and the negated form is wrapped by `NOT (...)` anyway. Other Django code that joins with `OR` wraps the result, for example the max-in-list-size splitting in `lookups.py:563`.

Fix direction: return `"(%s)" % " OR ".join(sql_parts)`, and add a test that combines the lookup with another filter.

### [Low] `JSONNull()` detection in `as_oracle` is limited to a bare `JSONNull()` in the list
`django/db/models/fields/json.py:466`

Trigger: on Oracle, pass `value__in=[Value(JSONNull(), JSONField()), [1]]`.

Impact: `JSONNull() in self.rhs.get_source_expressions()` relies on expression equality, so a `Value`-wrapped `JSONNull` never matches. It falls through to `as_sql`, which has the original Oracle problem of not being able to extract a JSON scalar null in an `IN` clause. This is an edge case, and I did not run it.

## Reviewed and found no problem

The `get_prep_lookup` change in `lookups.py` applies to every field type, not only JSON. Previously a non-string literal mixed with an expression was passed raw into `ExpressionList`. Now every literal is wrapped in `Value(v, lhs.output_field)`. I found no regression from this. It removes the earlier `isinstance(str)` special case, which mattered for the JSON `None` case. `get_prep_value` is no longer applied to those literals. `Value.as_sql` goes through `output_field.get_db_prep_value` instead. That is equivalent for the fields I traced, but it is a broad change with no non-JSON test coverage in this PR.

## Scope and limits

- Reviewed `e726254...e732971` (base to head). The head SHA matched PR metadata, and the PR had no comments.
- I read the diff and traced `JSONExact.as_oracle` and the `OR` joining by source inspection.
- I ran no tests and could not exercise MySQL, MariaDB or Oracle.
- I did not check CI.
- I did not verify the MariaDB `JSON_UNQUOTE` handling on the left-hand side for top-level string values. That behavior is inherited from the old `KeyTransformIn`, but `JSONIn` now applies it to top-level fields as well.
- The PR checklist leaves docs and release notes unchecked. Whether this fix needs a release note is a maintainer call.
