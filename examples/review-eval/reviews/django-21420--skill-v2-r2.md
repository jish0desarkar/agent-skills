# django-21420: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

### [High] `save()` overwrites a `db_default` primary key with `None`, so the INSERT sends NULL
`django/db/models/base.py:710-723` (the new `_is_pk_set`) feeds `_save_table` at `base.py:1097-1099` (introduced in this PR)

Trigger: save a new instance whose pk has `db_default` and which was not given a pk. `PrimaryKeyWithDbDefault().save()` in `tests/basic` is one example, and a UUID pk with `db_default=Func(uuid4)` is another.

Trace at head:
1. The pk attribute holds a `DatabaseDefault`. Before this PR, `_is_pk_set()` returned True, so `_save_table` kept it and the compiler (`sql/compiler.py:1809-1852`) emitted `DEFAULT` or the expression.
2. With this PR, `_is_pk_set()` returns False.
3. `if not self._is_pk_set(meta)` then runs `pk_val = meta.pk.get_pk_value_on_save(self)` and `setattr(self, meta.pk.attname, pk_val)`.
4. For a field with no Python `default`, `get_pk_value_on_save` returns `None` (`fields/__init__.py:794-796`). The `DatabaseDefault` is replaced by `None`.
5. `pk_set` is False. `insert_fields` still includes the pk, because it is not an `auto_field` (`base.py:1174`). `pre_save` then returns `None`, so the INSERT sends NULL for the pk.

Impact: an `IntegrityError`, or a wrong pk if the backend coerces NULL. This breaks every `save()` and `create()` of a new object with a `db_default` pk, not only inline formsets. The existing tests `test_save_primary_with_db_default` and `test_save_primary_with_falsey_db_default` (`tests/basic/tests.py:199-214`) appear to exercise this path, and I expect them to fail. I did not run them (see below). `tests/inline_formsets/tests.py:test_add_form_uuid_pk` only asserts `is_valid() is False`, so it never reaches `save()`.

Fix direction: leave `_is_pk_set` alone and make the inline-formset or `BaseModelFormSet` check treat a `DatabaseDefault` pk as unset. Alternatively, keep the new semantics but skip the `get_pk_value_on_save` and `setattr` step when the pk is a `DatabaseDefault`. The 12+ other `_is_pk_set` callers (`delete`, `_prepare_related_fields_for_save`, `contenttypes/forms.py:34`, the deferred-field save at `base.py:893`) were written for the "pk is None" meaning, so changing the shared predicate affects all of them.

### [Low] Composite pk with a `DatabaseDefault` member is routed differently in `bulk_create`
`django/db/models/query.py:726-733` (introduced in this PR)

For a composite pk such as `PostDbDefault`, `obj.pk` is a tuple, so the `isinstance(obj.pk, DatabaseDefault)` shortcut no longer matches. The object now goes through `get_pk_value_on_save` and `obj.pk = ...`, which can overwrite the `DatabaseDefault` member with `None` or a value. It is the same mechanism as the finding above, only reachable through composite pks. I traced it statically.

### Trace log
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `_is_pk_set` now returns False for `DatabaseDefault` (including tuple members) | changes meaning; removes/reorders code | `_save_table`, `bulk_create`, `delete`, `_prepare_related_fields_for_save`, `contenttypes/forms.py`, the deferred save at `base.py:893`, `get_pk_value_on_save`, the compiler | finding 1 and finding 2 |
| New tests | attack | `test_add_form_uuid_pk` only checks `is_valid()`; the `basic` test only checks `_is_pk_set()` | `save()` is not covered; the existing `db_default` pk save tests are the ones at risk |

Reviewed head `667250d4ac`, base `4bbc27c8`.

Not checked: I did not run any tests, per the review rules, so finding 1 comes from reading the code path rather than a failing run. I did not look at CI. I did not review the new test models under `tests/composite_pk` and `tests/inline_formsets` beyond their use in the tests.

Smaller note, not counted as a finding: the inner helper `_is_set` returns True when the value is *not* set, so its name is inverted.
