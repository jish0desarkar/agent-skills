---
name: complexity-check
description: >-
  Measure and reduce cyclomatic (Ruff C901) and cognitive (complexipy) complexity in Python,
  with equivalents for JS/TS and Go. Use after writing or refactoring non-trivial code, before
  declaring a feature complete, when a function has many branches or nested loops/try blocks,
  when C901 or complexipy reports a violation, when asked to reduce complexity, or for the
  complexity part of a user-requested code review. Scores only added or modified functions,
  works in repos that are already deep in complexity debt, never suppresses warnings, never
  invents a score, and forbids metric-gaming splits.
---

# Complexity check

Keep every function readable top to bottom. Metrics are signals that point at design
problems, not targets to turn green. A green number with worse code is a failure.

This skill owns *how complex* a function may be. `avoid-and-separate` owns *what state and
layering* is allowed; `progressive-search` owns *whether new code should exist*. Use them
together when installed; when they conflict, the simpler code that respects the layering wins.

## Limits

| Metric | Python tool | Preferred | Hard limit |
|---|---|---|---|
| Cyclomatic | Ruff `C901` (McCabe) | ≤ 5 | 10 |
| Cognitive | `complexipy` (Sonar-style) | ≤ 10 | 10 |

Cyclomatic complexity counts independent paths. Cognitive complexity estimates how hard the
control flow is to follow, and punishes nesting. A function under both limits still needs
work if it is hard to follow — three levels of nesting, or one flag tested in five places.

If the repo's `AGENTS.md`, `CLAUDE.md` or lint config sets different limits, use those.

## Scope: most repos start in debt

Real codebases usually already have dozens of functions over 10. Before the first change in
a repo, take a baseline so you know where the hotspots are:

```bash
ruff check --no-cache --no-fix --select C901 --config 'lint.mccabe.max-complexity = 10' --output-format concise . | wc -l
uvx complexipy . --max-complexity-allowed 10 --failed --plain -C no | head -30
```

Hotspots are typically: route handlers that do everything (parse, validate, persist, render),
"god" `run()` methods taking mode flags, and row-mapping code full of `x if len(row) > i else None`.

What you owe depends on what you touched:

| Function | Rule |
|---|---|
| New (including helpers you extract) | Must meet both limits. |
| Existing, under the limit before your edit | Must still be under it. If your change pushes it over, restructure the part you touched first, then make the change. |
| Existing, already over the limit | Must not get worse. Put new logic in a flat block or one named, cohesive function. Do not refactor the rest of the body unasked — report it as a hotspot and ask before a larger refactor. |
| Untouched | Leave it alone. |

Never, unless the user explicitly asks:

- enable C901 or set `max-complexity` in the repo's lint config when it is not already there
  (pre-commit runs for everyone; a baseline of existing violations would block every commit),
- add `# noqa: C901`, `# complexipy: ignore` or any other suppression, or raise a limit,
- add a complexity tool to the project's declared dependencies.

## Step 1 — Find what changed

List the files this session changed — `git status --short` and `git diff --name-only HEAD`
(or `but status -fv` in a GitButler workspace). Score only the functions you added or
modified, including nested functions and helpers you extracted. Run the checks below
**before** your first edit to an existing function and again after, so you can show it did
not get worse.

## Step 2 — Cyclomatic complexity (Ruff)

Run from the repo root:

```bash
ruff check --no-cache --no-fix --select C901 --ignore-noqa \
  --config 'lint.mccabe.max-complexity = 10' --output-format concise path/to/changed_file.py
```

`--select` on the command line replaces the configured rule set, so only C901 runs; the
`--config` limit applies to this command only; `--ignore-noqa` exposes existing suppressions
on the functions you touched (report any that hide a violation). Ruff prints only functions
over the limit — rerun with `max-complexity = 0` to see every function's exact score.

Use the project's Ruff (`.venv/bin/ruff`, `uv run ruff`) when there is one. If tooling only
exists inside the app container, run the same command through `docker compose exec <service>`.
Do not start the application, touch databases or install packages just to measure complexity.

## Step 3 — Cognitive complexity (complexipy)

```bash
uvx complexipy path/to/changed_file.py --max-complexity-allowed 10 --failed --plain -C no
```

Drop `--failed` to see every function's score. Add `--diff-only origin/main` to see which
functions are new or changed versus the base branch — that mode only displays, it does not
enforce. Add `--report-ignored` to expose existing complexipy suppressions on touched code.

`uvx` fetches complexipy on first use and writes to the uv cache; in a sandbox, run it
outside the sandbox. If it cannot run at all, estimate by hand: +1 for each `if`, `elif`,
`else`, `for`, `while`, `except`, ternary and run of `and`/`or`, plus +1 more for each level
of nesting it sits inside. **Say the score is a manual estimate.** Never present an estimate
as a measurement.

### Other languages

| Language | Cyclomatic | Cognitive |
|---|---|---|
| JS / TS | ESLint `complexity: ["error", 10]` | `eslint-plugin-sonarjs` `cognitive-complexity` |
| Go | `gocyclo -over 10 .` | `gocognit -over 10 .` |
| Anything else | `lizard -C 10 path/` | manual estimate (rules above) |

Same rules apply: command-local limits, no config edits, no suppressions.

## Step 4 — Diagnose the cause

Name the cause before changing code:

| Symptom | Cause | Usual fix |
|---|---|---|
| A route parses the form, validates, writes a cache, calls the domain layer and builds template context (30+ `if`s) | Multiple responsibilities | Route orchestrates only: guard-clause validation first (raise the project's client-error exception early), then one call per step. Context building goes to the existing view/presenter layer; domain decisions go to a pure function |
| Function takes boolean flags and re-tests them throughout (`run(..., apply_filters, dry_run, simulate)`) | Mode flags | Decide the mode once at the top and return early, or split into one function per mode. Never add another boolean parameter to an already-flagged function — it adds a path through every branch |
| `if/elif` chain on an enum, record type, status, provider or operator string | Branching business rules | Existing enum metadata (a method or property on the enum) or a dict lookup / dispatch table. Keep the chain when branches do genuinely different multi-step work. Don't add domain conditions to generic enums; filter at the call site |
| Row mapping reads every column as `row[i] if len(row) > i else None` | Positional row mapping | Name the columns once (named tuple, row factory, ORM). This is mapping, not logic — a high score does not always mean "extract functions" |
| Chains of `payload.get(...)` with fallbacks | Untyped dict payload | Typed dataclass or explicit arguments; the missing-key branches disappear |
| `None` guards on values that are always set, `if data:` around a whole body, `except` that only logs and re-raises | Branches that cannot happen | Delete them. Keep tenant/account scoping, input validation at trust boundaries, and error handling that prevents data loss |
| LLM tool / command handler mixes argument checks with execution | Validation mixed with execution | Guard clauses that return the error response first, then the happy path |
| `for` loop with accumulator flags filtering candidates | Imperative filtering | Comprehension with a named predicate |
| `try` around a network/queue/LLM call with branching inside it | `try` doing too much | Keep the `try` body to the call that can raise; branch after it |
| Same branching in a sync module and its async twin | Duplicated domain logic | One pure helper, two thin callers (`avoid-and-separate` §3). Never simplify one twin and leave the other to drift |

Guard-clause example:

```python
# Before
async def handle_update(account_id: int, order_id: int | None, args: dict) -> ToolResult:
    if order_id:
        draft = await load_order_draft(account_id, order_id)
        if draft:
            if args.get("items"):
                ...

# After
async def handle_update(account_id: int, order_id: int | None, args: dict) -> ToolResult:
    if not order_id:
        return missing_order_response()
    draft = await load_order_draft(account_id, order_id)
    if not draft:
        return inactive_draft_response()
    if not args.get("items"):
        return nothing_to_update_response()
    ...
```

Name a compound condition with a local variable first (`is_internal_webhook = ...`) and test
it once. Extract a function only when the concept deserves a name in the domain.

## Step 5 — Refactor, smallest change first

Stop at the first step that brings the function within limits and reads clearly:

1. Guard clauses and early returns.
2. Delete impossible and dead branches.
3. Name compound conditions; test each condition once.
4. Separate validation from execution.
5. Dict lookup or existing enum metadata for branches that only select a value or callable.
6. Extract one cohesive responsibility into a named function **in the same module**.
7. One function per mode for flag-driven functions.

Rules for extraction:

- Check the repo's reuse map (`REUSE_INDEX.md`) and the neighboring module first; an owner
  often already exists.
- No new file or class just to hold extracted helpers. No strategy objects, base classes or
  factories for branching that a dict or two functions can express.
- Each new helper gets a domain name, an explicit return type and a docstring describing
  what the caller gets. Match the file's indentation and style.
- Pure domain decisions go in a pure module; never move I/O into a helper that looks pure.

Preserve behavior while flattening:

- authorization checks and tenant/account scoping,
- session and transaction ownership, write order and rollback,
- exception types and messages callers depend on,
- idempotency and task dispatch — an early return must not skip a required write,
  rollback, cleanup or enqueue.

Delete code the refactor makes dead.

## Do not game the metrics

Bad — splits that communicate nothing and only hide branches:

```python
def accept_result(...):
    _part_1(...)
    _part_2(...)
```

Good — each step is a domain concept a reader can understand on its own:

```python
async def accept_result(...) -> HTMLResponse:
    parsed_request = parse_acceptance(form_data)
    saved_item = await persist_accepted_item(session, account_id, parsed_request)
    return render_item_panel(request, saved_item)
```

Complexity moved into another function is still complexity: the extracted function must
also pass the limits. If the helper would need the same branches, the fix is upstream — a
typed input, an earlier decision, or fewer modes.

## Completion checklist

```
- [ ] Listed this session's changed files
- [ ] Cyclomatic ≤ 10 for every added/modified function (tool named)
- [ ] Cognitive ≤ 10 for every added/modified function (tool named, or marked manual estimate)
- [ ] Touched pre-existing hotspots are no worse than before the edit
- [ ] No suppressions, config edits or raised limits; existing suppressions on touched code reported
- [ ] Each extracted helper has a domain name, return type and docstring, and lives in the same module
- [ ] Complexity was removed, not relocated; dead code deleted
- [ ] Re-ran both checks after refactoring
- [ ] Tests run only if the user asked; otherwise name the tests that cover the refactor and say they were not run
- [ ] After a structural refactor of imported code: an import smoke check of the app entry point (e.g. python -c "import app.main")
```

## Reporting

Report only actionable hotspots, most severe first. Include the before score for modified
existing functions so the reader can see whether the change made it worse:

```
Complexity findings

path/to/changed_file.py:function_name
- Cyclomatic complexity: 8 (Ruff C901)
- Cognitive complexity: 14 (complexipy)
- Main cause: validation nested inside the persistence branch
- Refactor: guard clauses first, then the write

routes/update.py:update_content (pre-existing hotspot)
- Cyclomatic complexity: 17 (before: 17, unchanged)
- Cognitive complexity: not worsened
- Main cause: one route handling every inline-edit mode
- Refactor: out of scope unless requested
```

In a user-requested code review, follow that review's format (e.g. `verified-code-review`)
and use this skill only for the complexity findings. Distinguish a maintainability concern
from a demonstrated correctness defect. Reviews are read-only: report, do not refactor.
