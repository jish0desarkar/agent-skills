# django-20718: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

I've traced the change through `lookup_field` and both callers, `admin_list.py` and `helpers.py`, and found one real defect. Next I'm writing up the report.

### [High] A related ForeignKey in `list_display` now raises `AttributeError`
`django/contrib/admin/utils.py:318` (introduced in this PR)

**Trigger:** a `list_display` entry like `"parent__grandparent"`, where the last segment is a ForeignKey or OneToOne on the related model. The admin check `_check_list_display_item` accepts it, because `get_fields_from_path` resolves it. Before this PR it rendered as the related object's `str()`.

**Path:** `lookup_field` now returns `f` as the final ForeignKey field instead of `None`. In `admin_list.py`, `items_for_result` sees `f` set and not `auto_created`, then checks `isinstance(f.remote_field, models.ManyToOneRel)`. That is true for a ForeignKey. It then runs `getattr(result, f.name)`. `f.name` is `"grandparent"`, but `result` is the base-model row, which has no such attribute. The `AttributeError` is not caught: only `ObjectDoesNotExist` is handled around `lookup_field`, and this call sits outside that `try`.

**Impact:** the whole changelist page fails with a 500. This breaks setups that worked before. If the base model happens to have a same-named attribute, it silently shows the wrong object instead.

**Fix direction:** limit the new `f` lookup to `BooleanField` results, for example by checking `isinstance(final, models.BooleanField)` before assigning `f`. Alternatively, make the `ManyToOneRel` branch in `items_for_result` use `value` rather than `getattr(result, f.name)`.

### [Medium] Every related lookup now goes through `display_for_field`, not just booleans
`django/contrib/admin/utils.py:316-318` (introduced in this PR)

**Trigger:** any `"rel__field"` entry in `list_display`, including fields with choices, dates, decimals and URL fields.

**Impact:** the output of these entries now differs from before, when they went through `display_for_value`. Choice fields show the human label, URL fields render as links, and the `nowrap` row class is added. Some of this is arguably an improvement, but it is a behaviour change the PR doesn't mention. There are no release notes, and the docs checklist item is unticked. The fix above also removes most of this.

### Smaller point
`helpers.py` (`AdminReadonlyField`) has the same `f is None` branching. A readonly field like `"parent__is_active"` now also gets `display_for_field`, so it shows an icon, and the `linebreaksbr` wrapper still applies. The PR has no test for this path. A related ForeignKey there would also hit `get_admin_url(f.remote_field, value)` on the wrong model's field. I read this path but did not run it.

### Trace log
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `lookup_field` returns a non-`None` `f` for `a__b` paths | changes what a function returns; adds a branch next to siblings; hands conversion to a library | 2 callers (`admin_list.items_for_result`, `helpers.AdminReadonlyField.contents`), `display_for_field`, `get_fields_from_path`, admin check E108 | finding 1; finding 2; readonly note |
| `f = None` moved to the top of the `except` block | removes or moves code | all paths still set `f`; the callable and model_admin paths keep `None` | no change |
| `get_fields_from_path` can raise | iterates or parses an input | property paths are rejected by E108; the `getattr` walk succeeding implies the fields exist | not reachable in practice |
| New test and model field | — | the test only covers a `BooleanField` | finding 1 is not covered |

**Reviewed:** head `43d4371bee497b59147a77f30e31177cdf5ddb13`, base `4b6c998301fedec279ec97b6547e67c3e88b7ff0`.

**Not checked:** I did not run the tests, and I did not reproduce finding 1 at runtime. It comes from reading the code at the head commit. I did not check CI.
