# Repository map

Choose a starting point here, then use [REUSE_INDEX.md](REUSE_INDEX.md) for existing owners.

Search both sections. Provenance says where knowledge is implemented, not how reliable it
is. Use local knowledge when it describes the current checkout's behavior.

> **Template.** One row per directory responsibility. Name entry points and the direction
> of imports. Replace every example row below; keep the table short enough to scan.

## Master knowledge

| Location | Responsibility |
| --- | --- |
| `app/main.py`, `app/routes/` | HTTP app assembly, auth/session handling, feature routes |
| `app/models.py`, `migrations/` | ORM schema and migration history (essential state) |
| `app/db.py`, `app/repositories/` | Async sessions and entity operations used by routes |
| `app/sync_db.py`, `app/workers/repositories/` | Sync sessions and entity operations used by background jobs (twin of the above) |
| `app/domain/` | Pure business rules shared by both paths — no I/O |
| `app/cache/` | Per-user drafts and caches (accidental state; system must stay correct without it) |
| `app/clients/` | External API and LLM clients |
| `app/tasks/`, `app/worker.py` | Background job definitions and the worker/scheduler entry point |
| `templates/`, `static/` | Server-rendered views, shared components, design-system CSS |
| `DESIGN.md` | UI contract and primitives |
| `tests/` | Fixtures and tests |
| `Dockerfile`, CI config, `pyproject.toml`, `.pre-commit-config.yaml` | Build, runtime and check configuration |

### Key flows

<!-- Optional: 3–6 sentences per important flow, naming the entry point and each owner it
passes through, e.g. "Webhook ingestion: `routes/webhooks.py:receive` validates and
enqueues `tasks/ingest.py:ingest_event`, which dedupes on (tenant_id, event_id) and writes
through `repositories/events.py`." -->

## Local knowledge

<!-- Branch: <name> @ <short sha>. Facts that exist only on this branch; mark entries that
depend on uncommitted work. Move entries up once merged. -->
