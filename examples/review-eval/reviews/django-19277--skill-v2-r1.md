# django-19277: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

## Review of PR #19277: "Fixed #36260 -- Made bulk_create() work with DB-generated primary keys"

### [Low] Objects are now classified as with-pk or without-pk before `_prepare_related_fields_for_save()` runs
`django/db/models/query.py:672-686` (introduced in this PR)

**Trigger:** a model whose primary key is a `OneToOneField` or `ForeignKey`. Assign an unsaved related object to it, save that object, then pass the model to `bulk_create()`. The pk attname is still empty at that point.

**What changes:**
- Before this PR, the loop only prepared the objects. `partition(_is_pk_set)` ran afterwards in `bulk_create`. `_prepare_related_fields_for_save` (`base.py:1200`) had already copied the related pk into the attname, so the object landed in `objs_with_pk`.
- Now the pk check happens before that call. The pk is still `None`, and `get_pk_value_on_save` returns `None`. The object goes to `objs_without_pk`.

**Impact:** limited to a case that is unusual and mostly harmless.
- The insert still includes the pk column, because only `AutoField` is filtered out of `fields`. The row is written correctly.
- The batching and the way returned columns are applied differ slightly between the two paths.
- I did not run this, so I could not confirm any visible difference.

**Fix direction:** call `obj._prepare_related_fields_for_save(...)` before classifying each object. Alternatively, keep the old approach and add a `DatabaseDefault` check to the partition.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `_prepare_for_bulk_create` now returns the two lists and replaces `partition` | changes what a function returns; removes or reorders code | Only caller is `bulk_create` (`query.py:799`). The old `partition` ran after the prepare loop. Order within each list is preserved. | Finding above |
| A `DatabaseDefault` pk goes to `objs_without_pk` | adds a branch beside existing ones; hands conversion to a framework call | `_is_pk_set` returns True for a `DatabaseDefault` value, so it was previously treated as set. `Field.db_returning` is true when the field has a `db_default` and the backend can return columns. The compiler (`compiler.py:1801-1840`) emits `DEFAULT` or the expanded default. The pk is then set from the returned row. | Correct. Without returning support (for example MySQL) the pk stays a `DatabaseDefault` object, which is the same as before and is now documented. |
| Pk set by a field default such as `UUIDField(default=uuid4)` | adds a branch | `get_pk_value_on_save` sets it, then `_is_pk_set` routes it to with_pk | Same as before |
| Composite pk | iterates or parses input | `obj.pk` is a tuple, so the `DatabaseDefault` check is false. Partial tuples are handled by `_is_pk_set`. | Unchanged |
| Docs and test | not applicable | The test is gated on `can_return_rows_from_bulk_insert`, and the `DateTimeField` pk is checked only through `isinstance` | Fine |

**Reviewed:** head `5f6736d8`, base and merge base `9608678`.

**Not checked:** I ran no tests and saw no CI. The Low finding is traced by reading the code, not reproduced. I found no other actionable defects.
