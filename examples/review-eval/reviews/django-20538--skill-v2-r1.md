# django-20538: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

Quick status: I've read the PR diff and checked the form-field code it relies on. I'm writing up the findings now.

### [High] `BooleanField` exact search now matches every `True` row for any non-empty term
`django/contrib/admin/options.py:1190-1200` (introduced in this PR)

Trigger: `search_fields = ["bool__exact"]` and the admin search term is `foo`.
- `BooleanField.formfield()` returns `forms.BooleanField`.
- Its `to_python` only maps `false` and `0` to `False`. Every other string becomes `True`, so `foo` converts to `True` instead of raising `ValidationError`.
- The query becomes `bool = True`, so every `True` row is returned. Before the PR, the cast comparison matched nothing for `foo`.

Impact: the new validation step doesn't validate anything for boolean fields.
- The search returns unrelated rows.
- The PR's own `test_exact_lookup_with_more_lenient_formfield` checks `false` and ignores this case.

Fix direction: validate with the model field's `to_python` where it is stricter, or fall back to it when the form field's conversion isn't a strict parse.

### [Medium] Empty quoted term (`""`) turns into an `IS NULL` search
`django/contrib/admin/options.py:1190-1200` (introduced in this PR)

Trigger: a search for `""` on `int_field__exact`.
- `smart_split` plus `unescape_string_literal` yields `""`.
- `forms.IntegerField.to_python("")` returns `None` rather than raising an error.
- The lookup becomes `int_field__exact=None`, which Django turns into `IS NULL`. The same applies to the other numeric, UUID and date form fields.
- Before the PR, the empty string matched nothing.

Impact: a quoted empty term unexpectedly returns every row with a NULL value.

Fix direction: skip the lookup when the converted value is `None`.

### [Medium] Relational `__exact` fields now run extra queries and hand ORM objects to the lookup
`django/contrib/admin/options.py:1190-1200` (introduced in this PR)

Trigger: `search_fields = ["fk__exact"]` or `["m2m__exact"]`.

**Foreign key**
- `ForeignKey.formfield()` is a `ModelChoiceField`. Its `to_python` runs a database `.get()` for every search term.
- It also applies `limit_choices_to`, so valid ids outside that limit are silently dropped.

**Many-to-many**
- `ModelMultipleChoiceField.to_python` expects a list, but it gets a string.
- `_check_values` does `frozenset("12")`, which gives `{"1", "2"}`. Each character is treated as a separate pk, and the result is a queryset.
- The queryset is then passed to `m2m__exact`, which is nonsensical.

Impact: this adds a query per term and field, and can return wrong results. It also goes against the PR's goal of avoiding needless queries.

Fix direction: use `validate_field.to_python` (the model field) for relational fields, or limit form-field validation to non-relational fields.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `construct_search` now returns a tuple | changes return value | The only unpacking is in `get_search_results`. Overrides in `tests/admin_views/admin.py` and callers in `autocomplete.py` and `main.py` only use `get_search_results`. | No caller broken. `may_have_duplicates` unpacks `(search_spec, _)` correctly. |
| Cast removed in favor of validation | removes code; hands validation to a library call | Form-field `to_python` for Boolean, Integer, FK and M2M | Findings 1–3 |
| New `Q(pk__in=[])` when no lookup is valid | adds a branch | Sibling path with `bit_lookups`; `term_queries` is never empty when `search_fields` is set. | Correct, but `pk__in=[]` raises `EmptyResultSet` and gives an empty result as intended. |
| `formfield() is None` fallback to model `to_python` | iterates and parses input | AutoField and similar | Fine. |

Reviewed head `12157a328f` against base `f87c2055b4`. I didn't run any tests. I confirmed the form-field behavior by reading the code, not by running it. I didn't check CI.
