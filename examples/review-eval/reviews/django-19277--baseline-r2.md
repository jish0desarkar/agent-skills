# django-19277: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

Status: the local Python is too old to run Django's test suite (`datetime.UTC` is missing), so I can't run the tests. I'll finish the review from the diff alone.

**PR #19277 review: "Fixed #36260 -- Made bulk_create() work with DB-generated primary keys"**

I found no blocking bugs. I couldn't run the tests, so this is from reading the diff against the surrounding `bulk_create()` code.

**What the change does:** `_prepare_for_bulk_create()` now returns `(objs_with_pk, objs_without_pk)`.
- An object whose `pk` is a `DatabaseDefault` goes to `objs_without_pk`. Before, `_is_pk_set()` treated it as set, because it isn't `None`.
- An object with no pk gets a Python-side default via `get_pk_value_on_save()`, and is then classified by whether that produced a pk.
- This replaces the later `partition(...)` call, so `partition` is no longer imported.

**Checks that hold up:**
- The `objs_without_pk` branch only drops `AutoField`s. A `db_default` primary key therefore stays in the insert field list and is resolved by the compiler's `DatabaseDefault` handling.
- That pk is copied back from `db_returning_fields`, which the new test exercises.
- Objects with explicit pks and objects relying on the DB default can be mixed in one call. Each group is inserted separately.

**Minor suggestions (non-blocking):**
1. **Mixed-batch test:** `test_db_default_primary_key` only covers a single object with the default. A test mixing an explicit pk with a `DatabaseDefault` pk would cover the new classification logic.
2. **Docstring:** `_prepare_for_bulk_create()` now returns a tuple. It's private, but a short note on the return value would help. Also check that no other callers expect `None`. I didn't search for any.
3. **Doc wording:** the `querysets.txt` caveat says the pk can't be retrieved on some databases, such as MySQL. In that case `obj.pk` stays a `DatabaseDefault` expression rather than being unset. That is the same as before the PR, but "will not be set" is slightly imprecise.

I left your checkout on `main`. The PR is fetched locally as the branch `pr-19277`.

Findings submitted with the ReportFindings tool:
