# Review-only risk map

Read only during a user-requested PR/code review. Do not load or apply during implementation
or routine self-checks. Select rows by changed behavior; this is not a checklist to run across
the whole repository for every PR. The questions are hypotheses to trace, not assertions of
existing bugs.

> **Template.** Copy to the repository root as `REVIEW_INDEX.md` and replace the
> "Start tracing here" column with real paths and symbols. Delete rows that do not apply and
> add rows for the repository's own recurring failure patterns. A row earns its place when it
> names where to look and the question that catches a real class of bug.

## Master knowledge

| Changed area | Start tracing here | Review question |
| --- | --- | --- |
| Tenant/auth boundary | auth dependency/middleware, changed route, its repository/service owner | Are record lookups, mutations and related IDs scoped to the authenticated tenant? Is ownership derived from trusted context rather than client-supplied IDs? |
| Twin code paths | sync worker module and its async web twin; preview vs run paths | Do both paths agree for the changed input? Did an async/return-shape change break a caller on the other path? |
| Database operations | models, session factories, changed repository | Do session type, transaction ownership, nullability, constraints and soft-delete/archive filtering match caller assumptions? |
| Migrations | migrations directory, migration env, models | Is ancestry valid with unique revisions and the intended heads? Does upgrade preserve existing data? Does downgrade recreate/drop the right constraints and implicit indexes? An autogenerate "no diff" check does not validate the graph or the reverse path. |
| Ingestion, retries and idempotency | job/consumer entry points and their producers | Can retries create duplicate records/actions, skip work or report false success? Does the idempotency key cover the intended event and tenant? |
| Draft/cache lifecycle | cache/staging modules, the entity's route and repository | Are preview, accept, reject and archive consistent? Can invalid/stale drafts be committed, or durable state become dependent on the draft cache? Does a read-only view avoid creating a draft? |
| Search/vector index lifecycle | indexing, deletion and rebuild jobs | Do shapes, empty results, index/delete/rebuild order and concurrent updates match the library and caller contracts? Can an index error hide or corrupt authoritative records? |
| Background tasks | worker app, task registry, changed job and its producer | Are registration, arguments, serialization, retry semantics and side effects compatible? Can a swallowed exception suppress a retry, or an async function go unawaited? |
| External APIs and LLM calls | API client, prompt/tool loop, caller | Are response types and failures handled? Are model/external IDs validated against trusted data? Can a fallback or retry repeat an external side effect? Are tool-call IDs and results paired across retries? |
| Listings and pagination | listing route, query builder, pagination helper | Do scope filters, counts, page membership and ordering agree? Can a status filter change between the count query and the page query? |
| Frontend fragments | changed template/component and the route that serves it | Are fragment targets, response types, bindings and empty/error states preserved? Do referenced UI classes exist and follow the design contract? |
| Time handling | timezone helpers, timestamp storage boundary | Are naive/aware timestamps, UTC storage and user-timezone conversion consistent, including DST and day-boundary cases relevant to the change? |
| CI and test claims | pre-commit config, CI pipeline files, Dockerfile, test config/fixtures | Which commands actually ran, on which revision? Do fixtures/mocks exercise the claimed contract? A green build or lint is not evidence that the test suite ran. |

## Local knowledge

<!-- Rows for behavior that exists only on the current branch. Move them up once merged. -->
