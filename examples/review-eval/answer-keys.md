# Answer keys (written before any review run)

Scoring for each known defect: CAUGHT (names the mechanism and a concrete trigger or
failure), PARTIAL (points at the right code or risk without a concrete failure, or with the
wrong consequence), MISSED. Other findings are classified as valid, false positive (claim
contradicted by the code or not reachable), or noise (style, docs, test nits presented as
defects). Ground truth comes from the maintainers' later fix commits.

## aiohttp-12988 — aio-libs/aiohttp#12988 (1 known defect)

K1: a control frame that arrives before the first data frame latches
`_compressed = COMPRESSED_FALSE` while `_frame_fin` stays False, so the first compressed
message is rejected with 1002 "non-zero reserved bits". Fix: aio-libs/aiohttp#13302.

## fastapi-15030 — fastapi/fastapi#15030, "Add support for Server Sent Events" (3 known defects)

- K1 (introduced): the SSE branch in `fastapi/routing.py` builds `EventSourceResponse`
  without `_build_response_args()`, so a declared `status_code` on the path operation and a
  status set by a dependency on `Response` are ignored (always 200) while OpenAPI documents
  the declared code. Raw `StreamingResponse` honors both. Fix: fastapi/fastapi#15937. (The
  JSONL branch had the same gap before this PR; credit SSE as introduced, JSONL as pre-existing.)
- K2 (introduced): `format_sse_event` in `fastapi/sse.py` splits `data` and `comment` with
  `str.splitlines()`: a payload ending in a newline loses its last `data:` line, and
  `\v \f \x1c \x1d \x1e \x85 U+2028 U+2029` are treated as line breaks, though SSE only
  recognizes `\n`, `\r\n`, `\r`. Fix: fastapi/fastapi#15515.
- K3 (newly exposed): a typed SSE endpoint registered through `include_router()` loses its
  stream item type in OpenAPI, because `stream_item_type` is computed in `APIRoute.__init__`
  and not passed through `add_api_route()`/`include_router()`. Root cause predates the PR
  for JSONL. Fix: fastapi/fastapi#15077.

## django-17554 — django/django#17554, "Added model field fetching modes" (2 known defects)

- K1: query iteration (`ModelIterable`, `RawModelIterable`, `RelatedPopulator`) now calls
  `Model.from_db(..., fetch_mode=...)`. Models that override `from_db()` with the documented
  signature `from_db(cls, db, field_names, values)` crash with `TypeError` on every query.
  Fix: d992705f9e (#37259).
- K2: related descriptors' `get_prefetch_querysets()` used to call
  `queryset._add_hints(instance=instances[0])` on every queryset, including a custom
  `Prefetch` queryset. After "Simplified related descriptor get_queryset() methods" only the
  default queryset gets the instance hint, so database routers lose the parent instance hint
  for custom `Prefetch` querysets (wrong database in multi-db setups). Fix: 60a17fccf4 (#37300).

## django-20009 — django/django#20009, top-level JSONField `__in` on MySQL/Oracle (1 known defect)

- K1: `FieldGetDbPrepValueIterableMixin.get_prep_lookup()` now iterates `self.rhs` twice:
  `any(hasattr(value, "resolve_expression") for value in self.rhs)` and then the list
  comprehension / loop. When `rhs` is an iterator (e.g. a generator passed to `__in` on an
  annotation), `any()` consumes it and values are lost, so the lookup prepares an empty or
  partial list and the query returns wrong rows. Fix: 0751d5fed1 (#37311).

## django-20718 — django/django#20718, boolean icons for related BooleanFields (1 known defect)

- K1: `lookup_field()` now sets `f = get_fields_from_path(opts.model, name)[-1]` for every
  `__` path. Two failures follow: (a) when the last part is not a model field (a property,
  method or `__str__` reached through a relation), `get_fields_from_path` raises
  `FieldDoesNotExist`, uncaught; (b) when the last part is a relation (e.g. `site__parent`),
  callers such as `items_for_result()` treat `f` as a field of the row's own model and read
  it from the root object. Either way the changelist crashes for `list_display` entries that
  used to work. Fix: 92470ad374 (#37230), which moved the lookup into `admin_list.py` behind
  `try/except FieldDoesNotExist`. CAUGHT for either (a) or (b) with a concrete entry.

## django-20538 — django/django#20538, removed casting from exact lookups in admin search (2 known defects)

- K1: non-text `__exact` search fields are validated with `formfield().to_python(bit)`. For
  fields with `choices` the form field is `TypedChoiceField`, whose `to_python()` returns
  the raw string unvalidated, so a term like `"john"` against an `IntegerField(choices=...)`
  reaches the ORM and raises `ValueError` (HTTP 500 on the changelist).
- K2: for `BooleanField`, `forms.BooleanField.to_python()` maps almost any string to
  `True`, so an arbitrary search term OR-matches every row whose value is True instead of
  matching nothing.
  Fix: fe81969e83 (#37263).

## django-19534 — django/django#19534, deprecated double-dot variable lookups (1 known defect)

- K1: the check `".." in str(filter_expression.var)` also runs for constants. For string
  literals (and translated literals) `filter_expression.var` is the literal value, so
  `{{ "a..b" }}` or `{{ 'a..b'|upper }}` emit a false `RemovedInDjango70Warning` (an error
  under `-W error`, and an error for real when the deprecation ends).
  Fix: b5388a3a80 (#37257).

## django-21420 — django/django#21420, inlines crash with db_default on primary key (1 known defect)

- K1: `_is_pk_set()` now treats a `DatabaseDefault` value as "not set". `_save_table()`
  then takes the "pk not set" branch and assigns `meta.pk.get_pk_value_on_save(self)`, so a
  primary key with both a Python `default` and a `db_default` gets the Python default instead
  of the database default (wrong key / wrong related row). `_is_pk_set()` has many callers
  (save, delete, related-object checks, `bulk_create`), so its meaning changed for all of
  them. Fix: 9465349120 (#37238). CAUGHT needs a caller whose behavior changes concretely;
  PARTIAL for "callers may be affected" without one.

## Clean controls — django/django#21344, fastapi/fastapi#15863

No defect is known (no later fix references them). Every finding is checked against the code:
valid, false positive or noise.

# Holdouts (keys written before any holdout run; these PRs were not used to design the v2 trace table)

## pandas-63473 — pandas-dev/pandas#63473, read_json follows the microsecond default (1 known defect)

- K1: the string-column path in `Parser._try_convert_to_date` now tries
  `to_datetime(..., format=f)` for `f in (None, "iso8601", "mixed")` and returns the first
  parse that succeeds, dropping the nanosecond-bounds check (`.dt.as_unit("ns")`) the old path
  had. That check rejected dateutil parses filled with default dates. Without it, ordinary
  strings such as `"Jan"`, `"1st"`, `"T1"` in an index or date-eligible column parse to year-1
  timestamps, so `read_json(df.to_json())` turns string labels into `0001-01-01...`.
  Fix: pandas-dev/pandas#67975. CAUGHT needs the bogus-date acceptance (non-date strings now
  become dates) with a concrete input.

## pandas-64529 — pandas-dev/pandas#64529, fast path for full-slice setitem in ArrowExtensionArray (1 known defect)

- K1: for a full (null) slice, `__setitem__` now sets `data = value`, adopting the boxed
  value as the array's own `_pa_array` without a copy. Boxing can be zero-copy over memory the
  caller still owns (`pa.array(numpy_array)`, masked arrays via `__arrow_array__`, or a
  passed-in `pa.Array`/`ArrowExtensionArray`), so the array shares a buffer with the input:
  mutating the numpy array afterwards changes the pandas array, and two DataFrames can end up
  linked, violating Copy-on-Write. Fix: pandas-dev/pandas#67990.

## django-19277 — django/django#19277, bulk_create with DB-generated primary keys (1 known defect)

- K1: `_prepare_for_bulk_create()` now partitions objects with `_is_pk_set()` before calling
  `obj._prepare_related_fields_for_save(operation_name="bulk_create")`, the call that copies a
  late-saved related object's primary key onto the field (for example a primary-key
  `OneToOneField` whose target was saved after the object was built). Such objects land in
  `objs_without_pk`, which fails (an assertion on backends that return rows from bulk
  inserts). Fix: c9ff757a55 (#37234), which moves the preparation call first. CAUGHT needs the
  ordering problem with a concrete case.

## django-19925 — django/django#19925, database-level delete options for ForeignKey (1 known defect)

- K1: the PR removes `"on_delete"` from `Field.non_db_attrs` because the new database-level
  options change the schema. As a result an `AlterField` that changes only a Python-level
  `on_delete` (for example `CASCADE` to `PROTECT`) is no longer a no-op and performs schema
  changes (rebuilding the constraint), where it used to touch nothing. Fix: 07d4f69c94 (#37260).
