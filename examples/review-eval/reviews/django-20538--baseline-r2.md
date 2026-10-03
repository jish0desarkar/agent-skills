# django-20538: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #20538 from its ref on `origin`. The earlier skill run found nothing because it only looked at the local working tree, not the PR. This review is from reading the diff only; I haven't run the tests.

The PR is "Fixed #36865 -- Removed casting from exact lookups in admin searches". It removes the `Cast` to `CharField` that blocked index use on primary keys. In its place, `get_search_results` runs each search term through the field's `formfield().to_python()` (or the model field's `to_python()` when there's no form field) and drops lookups whose value doesn't validate. The approach is sound and the tests cover the main cases. Two things need attention:

1. **Related-field `__exact` lookups now cost a database query per term** (`django/contrib/admin/options.py`, the new validation loop). If a `search_fields` entry like `"author__exact"` or `"pk__exact"` ends on a `ForeignKey` or `OneToOneField`, `prev_field` is that relation. Its `formfield()` is a `ModelChoiceField`, whose `to_python` runs a `queryset.get()`.
   - Every search term therefore issues an extra query per such field. This also happens for a model whose primary key is a parent-link `OneToOneField`, as in multi-table inheritance.
   - The `formfield()` queryset also applies `limit_choices_to`, so an id that exists can be silently skipped.
   - The PR is meant to avoid needless queries, so I'd validate against the relation's target field (`prev_field.target_field`) instead, or skip validation for relations.
   - There is no test for this case.

2. **Validation uses form-field parsing, but the lookup is built from the converted value.** This is a minor point. The PR deliberately uses `formfield().to_python()` so that, for example, `"false"` is accepted for a `BooleanField`. That leniency is locale- and widget-dependent: a `DateField` parses the term using the active locale's input formats. Admin search behaviour could then vary by the user's language.
   - Using the model field's `to_python()` where it can parse the term and falling back to the form field would be more predictable.
   - It's a judgment call, not a bug.

Smaller notes:
- A term that is valid for no lookup adds `Q(pk__in=[])`. That works, but `queryset.none()` would be clearer. It also means the search returns no rows whenever any one term is invalid for every field.
- An empty quoted term (`""`) goes through `to_python` and becomes `None`, giving `exact=None`. That is a behaviour change from the old cast. It should be tested or documented.
- I didn't see a release note or docs change for the `search_fields` behaviour. Check whether `docs/ref/contrib/admin/index.txt` mentions casting.

Findings submitted with the ReportFindings tool:
