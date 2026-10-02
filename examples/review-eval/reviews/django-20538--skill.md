# django-20538: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

I've read the diff and checked the form-field behavior it depends on. I'm writing up the review now.

## Review of PR #20538: "Fixed #36865 -- Removed casting from exact lookups in admin searches"

Reviewed head `12157a328fdb` against base `f87c2055b453` (merge-base diff, 3 files). I did this by reading source only. I didn't run the tests, and the PR has no comments.

### [Medium] Invalid terms now match rows on `BooleanField` exact searches
`django/contrib/admin/options.py`, in the new validation loop (introduced in this PR)

Trigger: `search_fields = ["flag__exact"]` and the search term is `foo`, where `flag` is a non-null `BooleanField`.
- The code validates with `formfield().to_python(bit)`. `forms.BooleanField.to_python` only maps `false` and `0` to `False` and runs `bool(value)` on everything else. It never raises `ValidationError`.
- So `foo` becomes `True`, and the search returns every row where `flag=True`.

For a nullable `BooleanField`, the form field is `NullBooleanField`. It maps unrecognised strings to `None`, and an exact lookup on `None` becomes `IS NULL`. Searching `foo` then returns every row where the value is NULL.

Impact: the PR's stated goal is "searching a field for a nonsensical term yields nothing". Before this PR, the cast version matched nothing for `foo`. Now it returns a large, unrelated set of rows.

Fix direction: validate with the model field's `to_python`, which raises for unknown strings. Use a form field only to be more lenient for specific cases such as `true`/`false`. Or special-case boolean fields explicitly.

### [Low] Empty quoted terms turn into `IS NULL` lookups
Same block.

Trigger: the search term is `""` (an empty quoted string), and the field is an `IntegerField`, `DecimalField`, `DateField` or a `ForeignKey`.
- `unescape_string_literal` yields `""`.
- Those form fields' `to_python("")` return `None` without raising.
- The lookup becomes `field__exact=None`, which is `IS NULL`.

Impact: an empty quoted search matches rows with a NULL value, where the cast version matched nothing.

Fix direction: treat `None` returned for a non-empty input, or an empty `bit`, as invalid.

### [Low] Relation fields now cost an extra query per term
`foreign_key__exact` (or `pk__exact` on a `OneToOneField` primary key) gives a `ForeignKey` as `validate_field`. Its form field is a `ModelChoiceField`, and its `to_python` runs `queryset.get(pk=value)`.
- Each search term therefore adds a query for each such lookup, and a model instance is passed into the filter.
- A term that is a valid id with no matching related row is silently skipped.

Fix direction: for relations, validate against the target field instead (`field.target_field`). Also consider calling `formfield()` once per lookup rather than once per term.

### Notes
- **Skipped terms:** if every lookup for a term is skipped, the code adds `Q(pk__in=[])`. That correctly makes the ANDed result empty.
- **Tests:** they cover the invalid value, mixed terms, boolean leniency and cross-field leakage. They don't cover a non-matching boolean term, a nullable boolean, an empty quoted term, or FK exact lookups, which are the cases above.

**Scope and limits:** I traced the changed hunk in `options.py` and the related form-field code at the PR head. I didn't run the tests or inspect CI. I didn't check docs or release notes for the behavior change.
