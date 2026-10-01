---
name: avoid-and-separate
description: 'Use whenever generating, modifying, or reviewing backend code (written for Python; the rules carry to any language) — models, migrations, services, repositories, routes, background jobs, caches. Applies "Out of the Tar Pit" (Moseley & Marks, 2006): classify every piece of state as essential or accidental, avoid the accidental, and keep essential state, essential logic, and accidental state in separate tiers. Blocks the complexity patterns agents add most often — domain logic duplicated across sync/async or web/worker twins, hand-managed derived state, untyped dict payloads, hidden control flow.'
---

# Avoid and Separate

The governing rule for backend code. A design-system contract governs the frontend; this governs the backend.

Before writing anything, use the `progressive-search` skill (if installed) to find an existing owner. That skill governs *whether* you need to write new code at all; this one governs *how* you write it once you do.

**The thesis:** complexity is what makes a system hard to understand, and state is its biggest source. Complexity that the *user's problem* requires is essential. Everything else is accidental — and accidental complexity is a defect, not a tradeoff. Two rules follow:

> **Avoid** state and control you do not truly need.
> **Separate** what remains, so each part can be read without the others.

Simplicity is not a style preference. It is the thing that makes every future change, test, and debugging session cheaper.

## 0. Map this repo onto the tiers (once per repo)

The rules below speak in tiers, not paths. Before the first change in a repository, map its directories onto the four tiers in §2:

1. If `ARCHITECTURE.md`, `AGENTS.md` or `CLAUDE.md` already describes the layout, use it.
2. Otherwise infer it from directory names and imports (`models/`, `migrations/`, `services/`, `domain/`, `cache/`, `tasks/`, `routes/`, `api/`, `clients/` …), then state the mapping in one short table in your response.
3. Look for the repo's **twins** — pairs of modules that implement the same domain behavior on two execution paths: an async web layer and a sync worker layer, a "preview" path and a "run" path, an API and an admin command. §3 depends on knowing them.
4. Offer to record the mapping in `ARCHITECTURE.md` so the next session does not redo it. Do not write it without agreement.

## 1. Classify before you write

Before adding any field, column, cache entry, or attribute, answer: **would a user of this product describe this?**

| The data | Classification | What to do |
|---|---|---|
| Input a user typed, or a record an external system sent us | **Essential state** | Store it. This is the only thing that earns a database column by default. |
| Anything derivable from essential state | **Accidental state** | Derive it on read. Do not store it unless you can name what recomputes it. |
| Order in which things happen, when the result does not depend on it | **Accidental control** | Do not encode it. Let the caller or infrastructure decide. |

If a user would not recognize the concept — a session id, a cache row, an internal lookup key, a "needs sync" flag — it is accidental by definition. That does not make it forbidden. It makes it something you must **justify, isolate, and never let leak into domain logic**.

## 2. The layering contract

Every module belongs to exactly one tier. Reference flows **downward only**.

| Tier | Typical homes | May reference |
|---|---|---|
| **Essential state** | ORM models, schema, migrations | Nothing. Self-contained. |
| **Essential logic** | Pure domain modules: rules, calculations, validation, evaluation, algorithms | Essential state only. |
| **Accidental state & control** | Caches, draft/staging stores, memo tables, search/vector indexes, queues and schedulers | Both tiers above. |
| **Interfacing** | HTTP routes/controllers, background workers, external API clients, CLIs | All of the above. |

Absolute rules that fall out of this:

- **Essential logic must never import from the accidental tier.** A draft cache that holds a user's half-finished UI edits is accidental state by construction. If evaluation logic reads from it, a UI staging buffer has become load-bearing. Existing violations are debt to work away from, never precedent to follow — name them when you touch them.
- **Models must never import from services, repositories, routes, or caches.** Keep the bottom of the stack clean.
- **The deletion test:** deleting every cache and staging store should leave the system **correct but inconvenient** — slower, worse UX, no in-progress edits. If it would leave the system *wrong*, essential state has leaked downward, and that is the bug to fix.

Quick checks (adapt the paths to the §0 mapping):

```bash
# Essential logic importing from the accidental tier
rg -n '^\s*(from|import)\s+(cache|caches|drafts|staging)\b' domain/ services/
# Models importing from higher tiers
rg -n '^\s*(from|import)\s+(services|routes|api|tasks|cache)\b' models/
```

## 3. Never write domain logic twice

This is the most common source of drift in codebases that agents work on, so it gets the strictest rule.

Many backends run the same domain rules on two paths: an **async** web layer serving requests and a **sync** layer used by background workers, or a UI **preview** and the production **run**. When each path keeps its own copy of a method, the copies drift. A typical failure: the worker converts a date filter into a real timestamp window, the async copy does not, and the UI's "test this rule" preview now disagrees with what production actually does. Nobody notices until a customer does.

Therefore:

- **Never copy a method between twins.** Not "for now", not "to unblock the async path".
- Domain logic — anything that decides *what is true about the data* — must be a **pure function**: plain arguments in, plain value out, no session, no `self`, no I/O. Put it in a shared module that both paths can reach, and have both call it.
- Only the thin I/O wrapper differs between twins. `await session.execute(...)` vs `session.execute(...)` is the *only* legitimate difference.
- If you touch one half of an already-duplicated pair, check the other half. If they have drifted, say so in your response — do not silently pick one.

The same rule covers enums and constants. Two declarations of the same enum with different member casing are drift waiting to happen. **One definition, one home.** Import a symbol from the module that defines it, never through a re-export.

## 4. Do not create hidden state

- **No mutable default arguments.** `def build(self, options={})` is a shared mutable object living across every call — literally hidden state in a signature. Use `None` and build the default inside.
- **No stored derived columns without a named owner.** An LLM-generated summary stored beside the record it describes has nothing forcing the two to agree. If you must store derived data for cost or latency, write in the docstring exactly what recomputes it and when. Undocumented derived state is how a system ends up in a "bad state" that only a re-run can fix.
- **No caching inside a function that computes a value.** Compute purely; let a caller decide to memoize.
- **No `print`.** Use the project's logger, and route HTTP errors through its central error handler if it has one. `print` is untargetable output that survives into production.

## 5. Do not hide data in dicts

Passing a large untyped dict is the same problem as global state: the callee can read anything, and the call site shows nothing about what actually influenced the result.

A common shape: `build_query()` returns a 16-key dict, and `run()` then re-interprets it with `if/elif` branches that partly repeat decisions `build_query()` already made. Neither end can be read alone.

- Return a typed object (dataclass, Pydantic model, TypedDict at minimum) or the specific values the caller needs. Not a bag.
- A function should receive what it uses. If it needs three fields, pass three arguments, not the record.
- New JSON/JSONB columns need a written justification. Opaque blobs are invisible to every reader and to the type checker.
- Prefer flat, named values over nested structures. Nesting is a subjective grouping that will be wrong for the next caller.

## 6. Do not encode control you do not need

- Do not impose an order between independent steps. If two operations do not depend on each other, do not write them so a reader must work out whether the order matters.
- Express *what* holds, not *how* to reach it: a filter, a comprehension, or a query beats a loop with accumulator flags.
- Push branching to the edges. A function that starts with five `if`s about which mode it is in is five functions.
- Enforce invariants declaratively — database constraints and validators, not a check repeated at each call site. Declarative constraints compose linearly; scattered imperative checks interact.

## 7. Every line must earn its place

Volume is the complexity you can measure, and it compounds with the rest.

- Delete code that a change makes dead — unused fields, variables, functions, imports. A helper that returns a lambda where a bool is expected, shadowed by an inline lambda in a dispatch table, is what dead code looks like after drift.
- No abstraction for a caller that does not exist yet. No extension points, no speculative fallbacks.
- Keep changes minimal: change what the fix requires. Do not refactor surrounding code uninvited.
- Do not add a compatibility shim to avoid updating callers. Update the callers.

## 8. House conventions

Defaults. If the repo's `AGENTS.md` / `CLAUDE.md` says otherwise, the repo wins.

- Return type annotations on **every** function and method.
- A docstring on every new function or method, saying what a caller needs to know.
- Assemble view data in the route/controller, not with logic in templates.
- Follow the indentation and idioms already in the file you are editing.

## Detecting debt fast

Useful when reviewing, or before touching an unfamiliar module:

```bash
rg -n 'def \w+\([^)]*=\s*(\{\}|\[\]|set\(\))' --type py      # mutable defaults
rg -n '^\s*print\(' --type py                                  # stray prints
rg -c '\.get\(' --type py | sort -t: -k2 -nr | head            # dict-bag hotspots
```

Report what you find in the touched area only; do not fix untouched debt uninvited.

## Before you finish

Check each one against the code you just wrote:

1. Did I store anything derivable? → Derive it, or name its owner in the docstring.
2. Did I write logic that already exists in a twin? → One pure function, two thin callers.
3. Does any essential logic touch a cache or staging store? → Remove the dependency.
4. Did I add a mutable default, a `print`, or an untyped dict payload? → Fix it.
5. Does a reader have to know the order of my statements? → Say so explicitly, or remove the dependence.
6. Is anything now dead? → Delete it.
7. Could I explain this to a new developer without describing hidden state? → If not, simplify.

## In a review

Report each violation with its tier and rule (for example "essential logic → accidental tier import, §2"), the file and line, and the smallest fix. A review records violations; it does not refactor.

## When you cannot comply

Sometimes accidental state genuinely is required — performance, or a case where deriving on demand is truly unnatural. That is allowed, and the paper says so. What is not allowed is smuggling it in.

State it plainly in your response: what you added, that it is accidental, why it was necessary, and what keeps it consistent. Then keep it in the accidental tier where a future reader can find and remove it.

**Do not add complexity silently.** An early "compromise" is how a codebase ends up in the tar pit.
