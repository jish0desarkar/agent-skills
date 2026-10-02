# django-20538: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] Boolean `__exact` search fields match on arbitrary text
`django/contrib/admin/options.py:1190-1203` (introduced in this PR)

**Trigger:** `search_fields = ["flag__exact"]` on a `BooleanField` or nullable `BooleanField`, and the user searches for a word such as `foo`. The new code validates terms with `validate_field.formfield().to_python(bit)` and only skips the lookup on `ValidationError`.
- **Non-null `BooleanField`:** `forms.BooleanField.to_python` (`django/forms/fields.py:816-826`) never raises. Anything other than `false` or `0` goes through `bool(value)`, so `foo` becomes `True`. The query becomes `flag = True`.
- **`null=True` `BooleanField`:** `forms.NullBooleanField.to_python` returns `None` for unrecognised strings, so the lookup becomes `flag__exact=None`, which Django turns into `IS NULL`.

**Impact:** The "skip invalid terms" behaviour the PR describes doesn't hold for these fields. Searching `foo` returns every row where the flag is true, or every row where it is NULL, instead of nothing. In a multi-term search the term is also treated as satisfied for those rows. The base's `Cast` comparison returned no rows for these terms.

**Fix direction:** For these fields, validate with the model field's `to_python`, which raises on bad input, or compare the form field's result against the allowed values. A test for `foo` on a `BooleanField` and a `NullBooleanField` is also needed. `test_exact_lookup_with_more_lenient_formfield` only covers `false`.

### [Low] `ForeignKey` `__exact` search fields now hit the database for every term
`options.py:1164-1168` and `1190-1203`

**Trigger:** `search_fields = ["author__exact"]`, or any FK or OneToOne followed by `exact`.
- `prev_field` is the relation field, so `formfield()` returns a `ModelChoiceField`.
- Its `to_python` runs `queryset.get(pk=bit)` once per search term, per request, and then returns a model instance.

**Impact:** There is one extra query per term for each such field. The returned instance is passed as the lookup value, which changes behaviour from the base's string comparison. It is a minor performance and behaviour change, but not an error.

**Fix direction:** Validate against the relation's target field (`prev_field.target_field`), or skip form-field conversion for relations.

### Scope and checks
- **Reviewed revision:** PR head `12157a328fdb9801fbc99ff549630040baf2d089` against base `f87c2055b45356378a7c2a020eb872352d20f85e`. The merge base equals the base, and I used these SHAs from `gh` metadata and a local fetch. The PR has no comments.
- **What I did:** I read the full diff (`options.py` and the tests), and read `construct_search` and the form `BooleanField` and `NullBooleanField` code at the head SHA.
- **What I did not do:** I did not run the tests or inspect CI. The Boolean finding comes from reading the source, not from executing it.
- **Other points:**
  - The empty-lookups fallback `Q(pk__in=[])` looks correct.
  - `DateField` and `DateTimeField` exact matching now depends on the form's input formats rather than a string cast. I did not trace this.
  - I did not check whether the PR adds a release note or doc change. The diff shows none.
