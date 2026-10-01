---
name: progressive-search
description: Find the existing implementation before adding a helper, service, type or schema — with a small, explicit search budget that widens only on evidence — and maintain a compact ARCHITECTURE.md and REUSE_INDEX.md so the next search is cheaper. Use for non-trivial code navigation, reuse discovery, or when the user asks to set up or refresh the repository maps; not for trivial text edits.
---

# Progressive search

The cheapest code is code that already exists. This skill makes an agent look for it in
widening circles — and stop looking as soon as the evidence is good enough.

Work from the repository root. Read `AGENTS.md` / `CLAUDE.md` first. Use `ARCHITECTURE.md`
to pick a domain and the matching `REUSE_INDEX.md` section to identify likely owners. Never
embed a second copy of those maps in a skill or prompt. If a map is missing, use the current
file's imports and nearby filenames instead of reconstructing the whole repository — and
offer to bootstrap the maps (below).

If the maps have `## Master knowledge` and `## Local knowledge` sections, search both. The
labels record provenance, not reliability or priority. Local knowledge is fully valid for
the current checkout: reuse applicable local owners and follow local decisions without
waiting for merge. Where local code changes default-branch behavior, the checkout decides.

## Find an existing owner

1. Start with the relevant part of the current file, its neighbors and its direct imports.
2. Use filenames or symbols to identify candidates before opening implementation sections.
3. Start with about **3 focused searches and up to 5 candidate files**. Expand only for
   concrete missing evidence or cross-boundary behavior, and say briefly why you expanded.
4. Once a candidate fits, check its signature, callers, tenant/account scoping and session
   type. When behavior is shared across twin paths (async web vs sync worker, preview vs
   run), inspect both implementations.
5. If no candidate fits after a reasonable attempt, implement the simplest solution. State
   the new abstraction, what you searched, and the unmet requirement — in the work update,
   not in code comments.

Do not read large files end to end or try to prove exhaustively that reuse is impossible.
The budget is a starting point, not a correctness limit.

## Choose the cheapest useful search

Run from the repository root. Replace the example domain (`invoice`) with the task's area.

```bash
# Locate files before reading them.
rg --files src lib -g '*invoice*'

# Discover owners, then get exact matching lines.
rg -l 'normalize_currency|validate_line_items' src lib
rg -n 'normalize_currency|validate_line_items' src/billing/invoice.py

# Follow one imported symbol into the likely caller layer.
rg -n -F 'validate_line_items' src/api src/workers

# Syntax search when text cannot express the shape (read-only).
ast-grep run --lang python --pattern 'get_connection($$$ARGS)' --files-with-matches src/

# Fallback when rg is unavailable (tracked files only).
git grep -n -e 'normalize_currency' -- src lib
```

Use single quotes around patterns with shell metacharacters, especially ast-grep's `$`
metavariables. Prefer the full `ast-grep` command over the ambiguous `sg` alias. Never use
rewrite/update flags for discovery. `rg -l` reduces noisy output to paths; `rg -n` keeps
matching lines with locations. **A truncated search is not evidence of absence** — narrow
the path or pattern, then read the relevant range with `sed -n 'START,ENDp' file`.

Search code, not vendored/minified assets, generated files or runtime databases, unless
they are the subject of the task. Respect ignore rules; name a needed ignored file
explicitly rather than disabling ignores across the repository.

## Maintain the maps

During implementation, after moving an indexed owner or adding a broadly reusable operation,
update only the relevant `REUSE_INDEX.md` entry. Verify its path, symbol and boundary. Keep
paired owners explicit where behavior differs; do not invent a universal canonical helper.
Update `ARCHITECTURE.md` only when a directory's responsibility changes. Keep the index
curated — it is a map of owners, not a function catalog. New facts that exist only on the
current branch go under `## Local knowledge`.

During a read-only review, suggest map corrections instead of editing files.

For a full refresh of the maps against the default branch and local work, use the
`knowledge-sync` skill as a separate maintenance task. Per-task map edits never advance
its `KNOWLEDGE_STAMP.json`.

## Bootstrap the maps (only when asked or agreed)

When a repository has no maps and the user wants them:

1. Copy [templates/ARCHITECTURE.md](templates/ARCHITECTURE.md) and
   [templates/REUSE_INDEX.md](templates/REUSE_INDEX.md) to the repository root.
2. Fill `ARCHITECTURE.md` from the top-level layout (`rg --files | cut -d/ -f1-2 | sort -u`),
   entry points (app factory, worker app, CLI) and import direction. One row per directory
   responsibility, not per file.
3. Fill `REUSE_INDEX.md` with the owners agents most often re-implement: persistence
   sessions and repositories, auth/tenant helpers, error handling and logging, validation
   and typed contracts, time/timezone helpers, pagination/listing, external clients, UI
   primitives. Verify every path and symbol with `rg` before writing it down.
4. Add one line to `AGENTS.md`/`CLAUDE.md` telling agents to check the maps before adding
   abstractions. Show the drafts before saving.

Validate documentation links and example commands without importing the application or
connecting to databases. Using this skill does not itself authorize project tests,
commits or pushes.
