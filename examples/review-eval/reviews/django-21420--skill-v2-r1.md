# django-21420: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

### Review of PR #21420 — "Fixed #37139 -- Fixed inlines crash on parent models with db_default on primary key"

I found no defect I could prove, and one risk I could not test.

**[Low, unverified] On backends without `RETURNING`, a saved db_default-pk instance still reads as pk-unset**
`django/db/models/base.py:712-723` (introduced in this PR)

- **Trigger:** a model whose primary key has a `db_default`, saved on a backend where `can_return_columns_from_insert` is False (MySQL, older MariaDB). In `_save_table`, the pk field is dropped from `returning_fields` (the `elif field.db_returning and not can_return_columns_from_insert` branch). The pk attribute therefore stays a `DatabaseDefault` object after the INSERT.
- **Impact:** `_is_pk_set()` now returns False for the saved instance. Before this PR it returned True.
  - `hash()` raises `TypeError`.
  - `delete()` raises `ValueError`.
  - A second `save()` is not routed to an UPDATE, because `pk_set` is False and `_state.adding` is already False. It would INSERT a duplicate row.
- **Why it is low:** before the PR the same instance held a bogus `DatabaseDefault` pk, so it was already broken. The new behaviour fails more loudly on some paths. I could not run it on MySQL here, so this is a code-read inference.
- **Fix direction:** check this case, or add a test using `skipUnlessDBFeature("can_return_columns_from_insert")` to document the limit.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `_is_pk_set()` now False for a `DatabaseDefault` pk, including inside a composite pk tuple | changes what a function returns; adds a branch | All 26 non-test callers from the change map. `_save_table` (`base.py:1097-1100`): `pk_set` is False, so `get_pk_value_on_save` is a no-op for db_default. `force_insert` is set because `has_db_default()` is true for all pk fields. The pk field is kept in `insert_fields` and `pre_save` yields `DatabaseDefault`. With RETURNING, `_assign_returned_values` fills in the real pk. | Works on RETURNING backends. See the finding for the others. |
| Same change, `__hash__`, `delete`, `_prepare_related_fields_for_save`, `validate_unique`/`validate_constraints`, contenttypes forms | changes meaning; sibling comparison | Each now treats an unsaved db_default-pk instance like a `None` pk. That is consistent with the goal of fixing the inline crash. | No other defect found |
| `force_update` or `update_fields` on an unsaved db_default-pk instance | attack | Now raises "Cannot force an update... no primary key". Before, it ran an UPDATE with a `DatabaseDefault` as the pk value. | Better behaviour |
| Composite pk with only some columns using `db_default` | iterates tuple | `any(_is_set(f))` covers a mix of None and `DatabaseDefault`. `test_pk_not_set_db_default` exercises it. | OK |

The helper `_is_set` returns True when the value is *unset*. Its name is inverted, which will mislead readers. I did not count that as a defect.

**Revisions:** head `667250d4ac`, base and merge-base `4bbc27c868`. I did not run tests, did not see CI, and did not test any non-RETURNING backend. The read-only constraint held: no checkout, no edits, nothing posted.
