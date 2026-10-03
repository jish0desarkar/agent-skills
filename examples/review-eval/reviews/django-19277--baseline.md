# django-19277: stock Claude Code, run 1

The session's final review, unedited except that scratch paths were removed.

---

PR #19277 looks correct, and I found no bugs. I read the diff but didn't run the tests.

The code-review skill found nothing at first, because it looked for the branch locally. I fetched `refs/pull/19277/head` from the `origin` mirror and reviewed the two commits directly. They are "Fixed #36260 -- Made bulk_create() work with DB-generated primary keys" and a follow-up that moves the `_is_pk_set` checks into `_prepare_for_bulk_create()`.

**What the PR does:**
- **Detection:** `_prepare_for_bulk_create()` now checks `isinstance(obj.pk, DatabaseDefault)` and puts those objects in the "no pk" group. This check has to come first. `_is_pk_set()` returns True for a `DatabaseDefault` value, so these objects would otherwise go in the "has pk" group and the database would never return their generated primary key.
- **Partitioning:** The method now returns `(objs_with_pk, objs_without_pk)`. The `partition` import is dropped because nothing else in `query.py` uses it.
- **Callers:** `bulk_create` is the only caller of `_prepare_for_bulk_create`, so the new return value is safe.
- **Insert path:** Objects without a pk drop only `AutoField` columns from the insert. A `DatabaseDefault` pk therefore stays in the column list and is emitted as `DEFAULT`. The returned pk is then set through `db_returning_fields`.
- **Behavior otherwise unchanged:** Objects with an explicit pk, and callable defaults resolved by `get_pk_value_on_save()`, behave as before.

**Nits (non-blocking):**
- The new test uses `DateTimeField(primary_key=True, db_default=Now())` and is gated on `can_return_rows_from_bulk_insert`. It only checks that `obj.id` is a `datetime`. A check that the value was actually saved, such as refetching by pk, would be stronger.
- The docs now mention `db_default`, but the PR has no release note. That is probably fine for a bugfix.
- The test doesn't cover the case where the database can't return rows. Docs say the pk "will not be set" there.

Your uncommitted `README.rst` change and the untracked `notes.local.txt` aren't part of this PR, and I didn't review them. I also left the fetched `pr-19277` branch in your local repo.

Findings submitted with the ReportFindings tool:
