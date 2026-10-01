---
name: verified-code-review
description: Review PRs, commits, branch diffs, local changes or specified code, and triage reviewer/bot comments — reporting only verified, reachable defects with a trigger, impact and file/line anchor. Read-only; never edits, switches branches or posts to GitHub unasked. Activate only for a user-requested PR/code review or comment triage; never for implementation, debugging, refactoring, PR-description writing or routine self-checks of your own edits. In review-and-fix requests, use only during the review phase.
---

# Verified code review

A review that reports what it can prove, on the exact revision under review, and nothing else.

## Activation boundary

Use only when the user asks for a PR/code review, code audit or reviewer-comment triage.
An ordinary implementation request does not activate this skill, even if it mentions a PR,
asks for tests, or requires checking the resulting diff. If invoked in that situation,
return to the implementation workflow without applying the review procedure.

For a combined review-and-fix request, apply this skill during assessment only; deactivate
it before the authorized fix phase. Do not silently turn a review into implementation.

## Load context only for the review

1. If the repository has its own review guide (`PR_REVIEW.md`, `REVIEW.md`, or a review
   section in `AGENTS.md`/`CLAUDE.md`), read it; it wins where it is more specific.
   Otherwise follow [references/review-procedure.md](references/review-procedure.md).
2. If the repository has a risk map (`REVIEW_INDEX.md`), read only the rows matching the
   changed behavior. Otherwise use the generic rows in
   [templates/REVIEW_INDEX.md](templates/REVIEW_INDEX.md) as tracing questions.
3. Do not load the whole architecture/reuse map unless navigation needs it. Do not run any
   implementation or index-maintenance workflow (e.g. `progressive-search` map edits)
   during a read-only review.

Do not copy guide files into a checkout to make a review possible. If the team would
benefit from a repo-specific risk map, suggest creating one from the template — after the review.

If repository knowledge files have `## Master knowledge` and `## Local knowledge` sections,
search both. They record provenance, not validity: local knowledge applies fully when the
reviewed revision includes that code.

## Core procedure

1. **Pin the target.** Establish the requested scope and preserve checkout state. For PRs,
   capture the actual base/head SHAs and relevant comments/checks. Fetch Git objects without
   switching branches; save each resolved SHA immediately (another fetch overwrites
   `FETCH_HEAD`). Verify fetched commits against PR metadata and review merge-base-to-head,
   using a stacked PR's actual base, not the default branch.
2. **Inventory, then trace.** List every in-scope changed file/hunk and group by behavior.
   Trace each behavior through direct callers and callees. Start with about 3 focused
   searches and 5 contextual files per behavior; expand only for concrete unresolved
   evidence. The budget must never hide a changed file from review.
3. **Search the reviewed revision**, not your working tree: `git grep -n -e 'symbol' "$HEAD_SHA" -- dir/`
   and `git show "$HEAD_SHA:path"`. Use `rg`/`ast-grep` only for local reviews or files
   verified identical to that revision. Never mix local and PR code as evidence.
4. **Prove each finding**: trigger, reachable path, impact, and the contract it breaks.
   Compare against the base to separate introduced/newly exposed defects from old ones. For
   snippet audits without a baseline, state that limit rather than inventing a regression.
5. **Treat existing comments as hypotheses.** Verify claimed fixes at the current head and
   honor the user's exclusions. Recheck live PR head/base before reporting, or disclose that
   the review may be stale.
6. **Report** (format below). Answer a specific user concern first. Say plainly when no
   actionable findings remain. Omit speculative issues and unrelated style nits.

## Severity

| Level | Meaning |
|---|---|
| **Critical** | Data loss/corruption, security or tenant-isolation breach, or production outage on a common path |
| **High** | Wrong results or failed operations on a realistic path; broken retry/idempotency; irreversible migration bug |
| **Medium** | Wrong behavior on an edge path, meaningful performance regression, or a contract violation a caller will hit |
| **Low** | Real but minor defect with limited impact. Style alone is never a finding unless a style review was requested |

## Report format

```
### [High] Retry re-sends the webhook after a partial failure
`workers/delivery.py:88` (introduced in this PR)
Trigger: the HTTP call times out after the receiver accepted the request.
Impact: the event is delivered twice; receivers without dedupe double-charge.
Fix direction: persist the delivery id before sending and skip if already acknowledged.
```

After the findings: the reviewed revision/scope, checks actually performed, and material
limits (files not traced, CI not inspected, stale head). Deduplicate findings that share a
root cause. Anchor PR findings on changed lines where possible.

## Read-only and evidence boundaries

Do not edit source, tests, docs or indexes; stash/reset/switch the checkout; commit or push
as part of a review. Do not post GitHub comments/reviews or approve PRs without explicit
authorization — return the review in chat. A review request alone does not authorize running
project tests, migrations or database work.

Prefer source inspection and existing CI logs/configuration. Any separately authorized
runtime validation must use the exact reviewed revision and isolated resources.
**Never label build/lint/import checks as passing tests** without evidence that tests ran.

Apply the repository's code-quality contracts (for example `avoid-and-separate`,
`complexity-check`, `design-system`) only where they produce a relevant finding; do not
turn them into a refactoring assignment. Suggest documentation/map corrections in chat;
updating review artifacts is a separate maintenance task.
