# django-20538: stock Claude Code (built-in code-review)

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #20538 ("Fixed #36865 -- Removed casting from exact lookups in admin searches"). It has two real behavior problems. I read the diff but didn't run the tests. The first attempt to run something failed because `python` isn't on the PATH here.

The PR drops the `Cast`-to-`CharField` approach in `ModelAdmin.get_search_results`. For non-text `__exact` search fields it now converts each search term with the field's `formfield().to_python()`, and it skips the lookup if conversion raises `ValidationError`.

**Findings**

1. **`bool__exact` matches every `True` row for any search term.** `forms.BooleanField.to_python` treats everything except `"false"` and `"0"` as `True`. A search for `foo` on a `BooleanField` therefore becomes `bool=True`, and all `True` rows are returned. Before, the cast-to-string comparison matched nothing. The new test `test_exact_lookup_with_more_lenient_formfield` only covers `"false"` and never checks that garbage input is rejected. In a multi-field search, an unrelated term like `xyz` also pulls in every `True` row through the boolean field's OR branch. The same applies to `NullBooleanField` and to `BooleanField(null=True)`, which uses the nullable form field. Suggested fix: validate boolean fields with the model field's `to_python`, or accept the lenient strings explicitly. `options.py` around the new `formfield.to_python(bit)` call.

2. **An empty term matches `NULL` rows.** A quoted empty term (`""`) is unescaped to `""` by the existing code. `forms.IntegerField.to_python("")` returns `None`, so the lookup becomes `age__exact=None`, which is `IS NULL`. The same applies to the other form fields that return `None` for empty input, such as decimal, date and UUID. Suggested fix: treat `None` (or empty) results as invalid and skip them. The tests use only non-null values, so this isn't covered.

3. **Lower-severity: `fk__exact` now runs a query per term.** For a foreign key, `prev_field` is the FK. `ModelChoiceField.to_python` then does a database query for each search term. It also respects `limit_choices_to` and the default manager. The lookup is skipped if the row isn't in that queryset, which differs from a plain exact match on the key. Consider using the FK's target field, or `to_python` on the model field.

4. **Minor: `formfield()` is rebuilt for every term and lookup.** Resolving it once per field in `construct_search` would avoid that.

5. **Minor: the new tests cover a narrow set.** The model-field `to_python` fallback for `AutoField` is covered only through `pk__exact`. There is no test for the empty term, garbage booleans, or `fk__exact`. A release note or doc mention is also worth considering, since search semantics changed.

Findings 1 and 2 should be fixed before merge. The rest of the logic holds up: per-term validation, the `Q(pk__in=[])` fallback when no lookup is valid, and the independent per-field validation test.

**Local checkout state**

- I fetched the PR as local branch `pr-20538`.
- To try switching to it, I ran `git stash -u`, then `checkout`, then `checkout main` and `stash pop`. That sequence ended with your uncommitted `README.rst` change and untracked `notes.local.txt` both still present.
- Nothing was committed or posted.

Findings submitted with the ReportFindings tool:
