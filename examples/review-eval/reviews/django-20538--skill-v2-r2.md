# django-20538: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] Boolean fields now match arbitrary search terms
`django/contrib/admin/options.py:1195` (introduced in this PR)

Trigger:
- `search_fields = ["flag__exact"]` (or `"=flag"` is unaffected, but `flag__exact` is not), where `flag` is a `BooleanField`.
- The admin user searches for `foo`.

`BooleanField.formfield()` returns `forms.BooleanField`, whose `to_python` never raises. It turns any non-`"false"`/`"0"` string into `True` via `bool(value)`. For `null=True` it returns `forms.NullBooleanField`, which maps any unrecognized string to `None`.

Impact:
- The term is never skipped, so the filter becomes `flag__exact=True`. A search for `foo` returns every row where `flag` is true.
- With `null=True`, the filter becomes `flag__exact=None`, which is `IS NULL`, so the search returns every row where `flag` is null.
- This is the case the PR's validation is meant to prevent. Under the old `Cast` code, junk terms matched nothing.
- In a multi-field OR search, one boolean field makes every row with a true value show up for any term.

Fix direction: validate with the model field's `to_python` (`validate_field.to_python(bit)`), which raises for non-boolean strings. Alternatively, special-case fields whose form field coerces instead of validating.

### [Medium] Related-field exact lookups now run a DB query per term, with different semantics
`django/contrib/admin/options.py:1195` (introduced in this PR)

Trigger:
- `search_fields = ["author__exact"]`, where `author` is a `ForeignKey`.
- Any search term.

`ForeignKey.formfield()` returns a `ModelChoiceField`. Its `to_python` runs `queryset.get(pk=value)` at `django/forms/models.py:1588`.

Impact:
- There is one extra query per term per related-field lookup, plus a fresh `formfield()` construction each time.
- The query uses the field's `limit_choices_to` and the default manager. A term that is a valid FK id but excluded by those is silently dropped, where the old exact lookup would have matched it.
- It also adds an N+1 pattern to a changelist search, which works against the PR's performance goal.

Fix direction: for relations, validate against the target field (`prev_field.target_field.to_python`) instead of the form field.

### Trace log
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `construct_search` returns `(lookup, field)` tuples instead of `(lookup, alias)` | changes return meaning; signature | Only caller is the loop in `get_search_results`. It is a nested closure, so there are no overrides. | Updated consistently. `lookup_spawns_duplicates` unpacks correctly. |
| `Cast`/`alias` removed, replaced with `to_python` validation | removes code; hands validation to a library | Read `forms.BooleanField`, `NullBooleanField` and `ModelChoiceField.to_python` | Findings 1 and 2 |
| Terms with no valid lookups add `Q(pk__in=[])` | adds a branch; iterates input | Single-field and multi-field OR cases, and the empty `term_queries` guard | The guard is harmless. An invalid term is ANDed in and returns nothing, matching the old behavior. |
| `get_search_results` callers | changes what a function returns | `views/main.py:573`, `views/autocomplete.py:60`, and the override at `tests/admin_views/admin.py:785` | The public signature and return type are unchanged. |
| Fields without a form field (`AutoField`) | handoff to a library | Falls back to `Field.to_python`, which raises `ValidationError` for non-integers | OK |

Reviewed head: `12157a328fdb`. Base (merge base): `f87c2055b453`.

Not checked: I did not run the tests or the reproduction, so both findings come from reading the source. I did not look at the added tests' coverage of boolean or FK fields. Nothing was edited or posted.
