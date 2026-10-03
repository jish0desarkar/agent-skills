# django-17554: stock Claude Code, run 1

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #17554 ("Fixed #28586 -- Added model field fetching modes") and found three possible bugs, all from reading the diff. I couldn't run the PR's tests because the system `python3` is too old for this Django (no `datetime.UTC`).

The `/code-review` skill found nothing at first because it only looked at the local checkout. I fetched the PR from the local mirror's `refs/pull/17554/head` instead.

1. **Forward FK, `related_descriptors.py`, line ~260:** `ForwardManyToOneDescriptor.__get__` now returns the cached value straight after the fetch. That skips the check that raises `RelatedObjectDoesNotExist` for a non-null FK. With `FETCH_PEERS` and a dangling FK, the prefetch caches `None` and the access returns `None` instead of raising.
2. **Deferred fields, `query_utils.py`, line ~285:** `DeferredAttribute.fetch_many` calls `setattr` on every peer. That includes peers whose field is already loaded, so it can overwrite their unsaved edits. It also raises `KeyError` for a peer whose row was deleted. The other `fetch_many` implementations skip peers that are already cached.
3. **Generic foreign keys, `contenttypes/fields.py`, line ~259:** the generic foreign key's `__get__` now goes through the fetch mode even when `content_type` or the object id is `None`. Under `RAISE`, that case now raises `FieldFetchBlocked` where it used to return `None` with no query.

I did not run any of the three, so treat them as plausible rather than confirmed. I stashed your working-tree changes (`README.rst`, `notes.local.txt`) while checking the branch out. I've restored them and put you back on `main`. The fetched PR branch is still there as `pr17554`.

Findings submitted with the ReportFindings tool:
- django/db/models/fields/related_descriptors.py:260 [PLAUSIBLE] (correctness) ForwardManyToOneDescriptor.__get__ returns the cached value directly after fetch, skipping the later `rel_obj is None and not self.field.null` check that raises RelatedObjectDoesNotExist.
  Failure scenario: With FETCH_PEERS and a non-null FK whose target row is missing (e.g. no DB constraint), fetch_many runs prefetch_related_objects. That caches None, and __get__ returns None instead of raising RelatedObjectDoesNotExist. FETCH_ONE raises in get_object. I did not run this.
- django/db/models/query_utils.py:285 [PLAUSIBLE] (correctness) DeferredAttribute.fetch_many overwrites the field on every peer, including peers where it is already loaded or modified, and raises KeyError for peers deleted since load.
  Failure scenario: With FETCH_PEERS and defer('value'), peer p2 loads value and is modified in memory (p2.value = 'changed'). Accessing p1.value then runs fetch_many, which calls setattr on all peers and replaces p2's unsaved change with the DB value. If a peer row was deleted, `value_by_pk[instance.pk]` raises KeyError. Other fetch_many implementations filter to uncached instances, and this one doesn't. I did not run this.
- django/contrib/contenttypes/fields.py:259 [PLAUSIBLE] (correctness) GenericForeignKeyDescriptor.__get__ now delegates to fetch_mode.fetch even when ct_id or fk value is None, so RAISE mode raises FieldFetchBlocked for a GFK that would return None with no query.
  Failure scenario: Under fetch_mode(RAISE), accessing obj.content_object where content_type_id is None raises FieldFetchBlocked, though no query is needed. The old code returned None. I did not run this.
