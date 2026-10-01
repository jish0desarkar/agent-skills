# Canonical reuse index

Check the relevant section before adding a helper, service, type or schema. Each entry is a
starting point: inspect its signature, callers and tenant/session assumptions. Paired
sync/async implementations below are existing owners, not proof of behavior parity.

Search both provenance sections before creating code. Local entries are equally valid for
the current checkout; reuse them whenever their behavior fits the task.

> **Template.** List *owners*, not every function: the module and the few symbols an agent
> would otherwise re-implement. Verify every path and symbol before writing it down.
> Replace all examples below.

## Master knowledge

### Persistence

- Models: `app/models.py`. Async session/dependency: `app/db.py` (`SessionLocal`, `get_session`). Sync: `app/sync_db.py` (`Session`).
- Entity operations: `app/repositories/<entity>.py` (async) and `app/workers/repositories/<entity>.py` (sync). Inspect both when changing shared decisions.
- Drafts/cache: `app/cache/` — never use as durable persistence.

### Contracts, validation and time

- Typed request/record contracts: `app/schemas/` (`InvoiceCreate`, `LineItem`).
- Shared validation: `app/domain/validation.py` (`validate_line_items`).
- Timezones: `app/time.py` (`to_user_time`, `to_utc`). Check naive/aware semantics before reuse.

### HTTP, auth and errors

- Current user / tenant: `app/routes/deps.py` (`get_current_user`, `get_tenant_id`). Still check authorization in the calling route.
- Client errors: `app/errors.py` (`ClientError`, registered handler in `app/main.py`).
- Logging: `app/log.py` (`get_logger`).
- Pagination: `app/pagination.py` (`Page`, `paginate`).

### Integrations and background work

- External clients: `app/clients/<provider>.py`. LLM calls: `app/clients/llm.py` (`complete`, `stream`).
- Task registration: `app/worker.py`; jobs in `app/tasks/`.

### UI

- Primitives: `templates/components/`, `static/css/design-system.css`; follow `DESIGN.md`.

## Local knowledge

<!-- Branch: <name> @ <short sha>. Owners that exist only on this branch. -->
