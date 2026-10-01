---
name: build-with-ownership
description: Implement software features with AI assistance while preserving the engineer's architectural understanding, debugging ability, and ownership. Use manually for feature work, significant fixes, refactors, or reviews where the user wants Claude to inspect, design, implement, verify, and teach without becoming a blind code generator.
argument-hint: "[feature, bug, refactor, review, or quiz request]"
disable-model-invocation: true
---

# Build With Ownership

Work on the following request while keeping the human engineer in control of requirements, architecture, invariants, failure handling, and final approval:

$ARGUMENTS

## Core contract

Optimize for both delivery speed and retained engineering skill.

You may do substantial repository exploration, boilerplate generation, repetitive edits, test fixture creation, command execution, and documentation. Do not silently take ownership of product behavior, architecture, transaction boundaries, consistency semantics, security decisions, or production-risk tradeoffs.

The human must retain a causal model of the change:

- why it exists;
- where state lives;
- how data and control flow through the system;
- which invariants must always hold;
- what can fail;
- how failures are observed and recovered;
- how the change is verified and rolled back.

Do not equate passing tests with correctness. Do not weaken tests, broaden scope, add frameworks, introduce dependencies, or perform unrelated refactors merely to make implementation easier.

## Modes

Infer the mode from the request:

- **feature**: new behavior or capability;
- **bug**: diagnose and fix a defect;
- **refactor**: improve structure while preserving behavior;
- **review**: evaluate an existing diff or implementation without editing unless explicitly requested;
- **quiz**: test the engineer's understanding one question at a time.

When ambiguous, use **feature**. Do not ask for a mode selection.

## Change classification

Before editing, classify the task:

### Tiny

Localized, low-risk, obvious behavior; typically one or two files with no schema, concurrency, security, distributed-state, migration, or external-side-effect concerns.

Use the fast path. Still identify expected behavior and inspect the diff.

### Medium

Several files or a meaningful behavior change, but bounded to one subsystem.

Use the standard workflow with a human design gate before production edits.

### High risk

Any change involving authentication, authorization, money, destructive operations, schema migration, concurrency, distributed state, queues, retries, idempotency, external side effects, privacy, production infrastructure, or difficult rollback.

Use the full workflow with explicit human gates before implementation and before final approval.

State the classification and one-sentence reason.

## Phase 1 — Establish the feature contract

Do not edit production files yet.

Translate the request into a concise contract containing:

1. **Behavior** — externally observable behavior and API semantics.
2. **Invariants** — facts that must always remain true.
3. **Edge cases** — empty, duplicate, stale, unauthorized, invalid, concurrent, delayed, retried, and partially failed cases as relevant.
4. **Non-goals** — behavior intentionally excluded.
5. **Definition of done** — evidence required to call the work complete.
6. **Assumptions** — facts not established by the request or repository.

Do not invent business rules when the repository or request can answer them. Resolve uncertainty by inspecting code, tests, documentation, issue context, and adjacent implementations first.

Ask the human only about a genuinely blocking product or risk decision that cannot be resolved from available evidence. Otherwise proceed with explicit assumptions.

For medium and high-risk work, present the contract and stop for human approval before production edits. For tiny work, continue unless a meaningful ambiguity remains.

Use [templates/feature-brief.md](templates/feature-brief.md) as the format when useful.

## Phase 2 — Map the existing system

Do not propose code until the current behavior is understood.

Inspect the repository and report exact files and symbols for:

- request or event entry points;
- validation, authentication, and authorization;
- business logic and ownership boundaries;
- persistence models, repositories, and migrations;
- transaction boundaries and consistency patterns;
- queues, jobs, retries, caches, locks, and external calls;
- error mapping and failure recovery;
- logs, traces, metrics, and alerts;
- the closest tests and fixtures;
- existing conventions that the change should follow.

Produce a compact flow such as:

`input → validation → authorization → service → state transition → external effect → response/recovery`

Separate repository facts from assumptions. Point out conflicting patterns or hidden coupling.

The goal is not a generic repository summary. Trace the exact path relevant to this task.

## Phase 3 — Design before implementation

For tiny work, state the intended change and why it is safe.

For medium and high-risk work, propose at least two materially different designs when a real tradeoff exists. Do not manufacture alternatives when only one sensible implementation exists.

For each design cover:

- data and control flow;
- ownership and source of truth;
- state machine or lifecycle where applicable;
- transaction boundaries;
- idempotency, ordering, locking, and concurrency semantics;
- partial-failure behavior;
- retries, timeouts, compensation, and recovery;
- schema and compatibility impact;
- security and authorization impact;
- operational visibility;
- rollout and rollback;
- complexity and maintenance cost.

Recommend a design, but require the human to own the final decision for medium and high-risk work.

After approval, restate the selected design in a short decision record in your own words. Use [templates/decision-record.md](templates/decision-record.md) when useful.

## Phase 4 — Define verification before production code

Create a behavior-oriented test matrix before implementation.

Every important invariant must map to evidence. Include, where relevant:

- happy path;
- validation failures;
- authorization boundaries;
- duplicate and retry behavior;
- real concurrent operations;
- transaction rollback;
- dependency outage;
- timeout and partial completion;
- migration compatibility;
- observability and recovery.

Prefer integration or system-level evidence for cross-component behavior. Do not mock away the database, queue, lock, transaction, or dependency behavior that the test claims to prove.

Identify tests that may be nondeterministic and explain how to stabilize them.

Encourage the human to personally write or fully reconstruct at least one high-value test covering the most important invariant or failure path. Generate fixtures and repetitive setup freely.

For medium and high-risk work, show the matrix before implementation. Use [templates/verification-matrix.md](templates/verification-matrix.md).

## Phase 5 — Implement in bounded slices

Never implement a medium or high-risk feature as one unbounded change.

Create small conceptual slices, usually in this order when applicable:

1. schema, types, and constraints;
2. repository and transaction logic;
3. domain or service behavior;
4. API, event, or UI integration;
5. external effects, queues, workers, and recovery;
6. observability;
7. tests and documentation.

Before each slice state:

- exact scope;
- files likely to change;
- invariant or behavior implemented;
- explicit non-scope;
- verification to run afterward.

During implementation:

- follow existing conventions;
- prefer the smallest coherent diff;
- do not add dependencies without an explicit decision;
- do not create generic abstractions for a single use case;
- do not change architecture silently;
- do not alter or delete tests merely because they fail;
- do not conceal uncertainty;
- stop when the approved design would need to change.

After each slice report:

- files changed;
- purpose of each change;
- behavior now supported;
- invariants enforced and where;
- unresolved risk;
- commands run and actual outcomes.

For high-risk changes, pause after each meaningful slice for human inspection. For medium changes, pause after the first architectural slice and then continue in small batches unless redirected. Tiny changes may be implemented in one pass.

## Phase 6 — Human-first diff inspection

Before providing an explanatory summary, prompt the engineer to inspect the diff directly. Do not make the explanation a substitute for reading.

Organize the review around these questions for every important file:

- Why did this file need to change?
- What state does it read?
- What state does it modify?
- What can fail here?
- What happens after failure?
- Which invariant is enforced here?
- Is that invariant enforced at the correct layer?
- What hidden behavior comes from a library or framework?

Then trace at least one complete happy path and one important failure path through exact functions and files.

Flag any section that is difficult to explain. Treat unexplained code as unfinished, even when tests pass.

## Phase 7 — Adversarial review

Review the completed diff against the approved contract and design. Do not review it as a stateless generic diff.

Look specifically for:

- incorrect transaction boundaries;
- races, lost updates, duplicate work, and ordering bugs;
- authorization or trust-boundary gaps;
- state transition violations;
- retry storms and non-idempotent retries;
- timeout and cancellation bugs;
- success responses before durable acceptance;
- mismatches between database and external systems;
- backward-incompatible migrations;
- poor rollback behavior;
- missing logs, metrics, traces, or recovery mechanisms;
- tests that pass without establishing the claimed property;
- accidental complexity and invented abstractions.

Rank findings by severity. Every finding must include a concrete failure scenario, the violated requirement or invariant, and the smallest defensible correction.

Do not edit while conducting the first adversarial review. Present findings first.

## Phase 8 — Verify with evidence

Run the relevant tests, type checks, linters, builds, and application-level checks available in the repository.

For each invariant provide:

- automated evidence;
- exact command;
- actual result;
- what the evidence does not prove;
- manual or fault-injection evidence where useful.

For important features, exercise at least one real failure path, such as:

- dependency unavailable;
- concurrent requests;
- retry after timeout;
- process restart during work;
- migration against old data;
- unauthorized access;
- malformed external response.

Never say a command passed unless it was run successfully. Clearly distinguish not run, failed, blocked, and passed.

Use [templates/verification-matrix.md](templates/verification-matrix.md) for the final evidence table.

## Phase 9 — Reconstruct understanding

After implementation and verification, make the engineer explain the system rather than merely read your summary.

Ask them to explain, in their own words:

- request or event flow;
- state ownership and source of truth;
- transaction boundary;
- invariants and enforcement points;
- concurrency and retry behavior;
- most important failure mode;
- observability and recovery;
- rollback strategy.

Then critique gaps and point to exact code that resolves them.

Offer a one-question-at-a-time quiz covering architecture, state, concurrency, failure handling, security, verification, and rollback. Do not reveal an answer before the engineer responds.

Use [templates/knowledge-check.md](templates/knowledge-check.md).

## Bug mode — Hypothesis before fix

When the request is a bug, do not immediately modify code.

First produce:

1. observed behavior;
2. expected behavior;
3. known evidence;
4. affected boundaries;
5. ranked hypotheses;
6. contradicting evidence for each hypothesis;
7. the smallest discriminating check;
8. localization result.

Run checks that distinguish hypotheses. Modify code only after the failure is localized or after explicitly stating why localization is not possible.

Apply the smallest fix that addresses the root cause. Add a regression test that fails for the original reason, not merely for a copied symptom.

Use [templates/debugging-note.md](templates/debugging-note.md).

## Refactor mode — Preserve behavior first

Before refactoring:

- identify the behavior that must remain unchanged;
- establish characterization tests where evidence is weak;
- define the structural goal and non-goals;
- separate mechanical movement from semantic changes;
- keep each step reversible.

Do not combine a broad refactor with new product behavior unless explicitly approved.

## Review mode — No edits by default

When reviewing existing work:

- recover the intended contract from the request, issue, tests, and surrounding code;
- inspect the actual diff;
- trace important flows;
- identify unsupported assumptions;
- rank concrete risks;
- describe verification gaps.

Do not edit unless the user explicitly asks for corrections after reviewing findings.

## Fast path for tiny changes

For tiny changes, compress the workflow to:

1. state expected behavior and assumptions;
2. inspect the relevant path;
3. implement the smallest diff;
4. inspect the diff;
5. run focused verification;
6. explain one happy path and one failure path.

Do not force architectural ceremony onto trivial edits.

## Completion standard

Do not declare the task complete until all applicable statements are true:

- behavior is explicit;
- important invariants are explicit;
- architecture and transaction boundaries are understood;
- the diff is bounded and explainable;
- important tests prove behavior rather than implementation details;
- at least one meaningful failure path has been considered or exercised;
- review findings are resolved or consciously accepted;
- actual verification results are reported;
- the engineer can explain the change without relying on your summary.

End with a compact **Ownership Handoff**:

- What changed
- Why this design
- Critical invariants
- Most likely failure mode
- How to diagnose it
- Verification performed
- Remaining risks
- Questions the engineer should be able to answer

## Supporting resources

Load only when relevant:

- [references/responsibility-split.md](references/responsibility-split.md) — what the human must own versus what the agent may delegate.
- [templates/feature-brief.md](templates/feature-brief.md) — requirements and invariant template.
- [templates/decision-record.md](templates/decision-record.md) — design decision template.
- [templates/verification-matrix.md](templates/verification-matrix.md) — evidence mapping template.
- [templates/debugging-note.md](templates/debugging-note.md) — hypothesis-driven debugging template.
- [templates/knowledge-check.md](templates/knowledge-check.md) — reconstruction and quiz template.

## Companion skills

When these are installed, use them at the matching phase instead of improvising:

- Phase 2 — `progressive-search` to find existing owners within a small search budget.
- Phases 3 and 5 — `avoid-and-separate` for state and layering; `complexity-check` for function-level complexity; `design-system` for UI work.
- Phase 7 / review mode — `verified-code-review` for evidence-backed findings.
- Phase 8 — `verify-in-browser` for runtime evidence on user-facing changes.
