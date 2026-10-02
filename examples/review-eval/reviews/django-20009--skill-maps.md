# django-20009: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

I've traced the diff and found two issues. This is a read-only review of PR #20009 (head `e732971`, base `e726254`). I didn't run any tests, since no Oracle or MySQL is available and a review request doesn't authorize running them.

### [Medium] Oracle `__in` expansion into `OR` has no outer parentheses
`django/db/models/fields/json.py`, in `JSONIn.as_oracle` (introduced in this PR)

Trigger: on Oracle with `supports_primitives_in_json_field`, run `filter(value__in=[JSONNull(), [1]], other=1)`, or any `Q` that combines this lookup with another condition. `as_oracle` returns `"(a) OR (b)"` with no wrapper.

`WhereNode.as_sql` (`where.py`) joins child SQL without wrapping each child. It only parenthesizes the whole node when it has more than one child or is negated. In an AND node this produces `(a) OR (b) AND other = 1`, and AND binds tighter than OR.

Impact: wrong rows come back silently. Rows matching `value = JSONNull` are returned regardless of the other conditions. The new tests don't catch it because they use a single-condition filter.

Fix direction: return `"(%s)" % " OR ".join(sql_parts)`. `In.as_sql` already wraps its large-list expansion the same way. Add a test that ANDs this lookup with another condition.

### [Medium] Top-level `value__in` now wraps only the left side on SQLite and MySQL
`json.py`, in `JSONIn.process_lhs` and `resolve_expression_parameter` (introduced in this PR)

Trigger: `filter(value__in=<queryset or F('other_json_field')>)`, where the right side is a subquery or a plain column rather than a literal or a `KeyTransform`.

- `process_lhs` now wraps the column in `JSON_EXTRACT` (MySQL) or a `CASE ... JSON_EXTRACT` (SQLite).
- `resolve_expression_parameter` leaves right-side expressions that have `as_sql` untouched, unless they are a `Value`. A subquery or `Col` on the right side therefore stays raw.
- On SQLite, `JSON_EXTRACT` returns minified text for objects and arrays, and unquoted text for strings.
- Django stores the raw column as `json.dumps` output with spaces, and strings keep their quotes.
- So `'{"a":"b"}'` is compared with `'{"a": "b"}'`, and `foo` with `"foo"`. These don't match.

Impact: `__in` against a subquery or another JSON column can stop matching on SQLite. Before this PR the comparison was raw-to-raw. The added tests only use `F('value__bax__foo')`, which is a `KeyTransform` and so is extracted on both sides. I traced this from the source but didn't run it, so treat it as plausible rather than reproduced. MySQL has a similar mismatch risk.

Fix direction: skip the left-side wrapping when the right side is a query or a non-`Value` expression. Otherwise apply the same extraction to the right side. Add a test for `value__in=Model.objects.values("value")`.

### Low, worth confirming
`lookups.py`, `FieldGetDbPrepValueIterableMixin.get_prep_lookup`: when any list item is an expression, every plain item is now wrapped as `Value(v, self.lhs.output_field)`. Before, only strings were wrapped. If the left side has no resolvable `output_field`, that is now read for non-string items too, where it previously wasn't. This could raise `FieldError` on lookups like `__in` or `__range` that mix expressions with ints. It is unconfirmed, and it changes behaviour for every field type, not just JSON.

### Scope and limits
- Reviewed: the full three-file diff (`json.py`, `lookups.py`, `test_jsonfield.py`), including the `KeyTransform` refactor into `ProcessJSONLHSMixin`.
- The refactor preserves the previous SQL for `KeyTransform` on all backends. The only change there is `tuple(params)` becoming `params * 2`, which is equivalent.
- Not done: no tests run, CI not inspected, and there are no PR comments to triage.
- The PR checklist leaves docs and release notes unchecked, and the description says "Not sure if a release note is required". This is a bug fix, so a note may not be needed.
