---
name: verified-code-review
description: Reviews pull requests, commits, branch diffs, local changes or given code, and triages reviewer or bot comments. Traces every changed behavior into its callers, siblings and inputs, and reports only defects verified on the exact revision, each with a trigger, impact and file/line anchor. Read-only; never edits, switches branches or posts to GitHub unasked. Use when the user asks for a PR or code review, an audit, or comment triage; not for implementation, debugging, refactoring, PR descriptions or checks of your own edits.
---

# Verified code review

Stock reviews read the diff and comment on what they see. Regressions usually live outside
the diff: in a caller whose assumption changed, a sibling branch the new code skipped, a side
effect a refactor dropped, or an input nobody tried. This skill makes you trace those paths
and report only what you can prove.

Use it only for a user-requested review, audit or comment triage. In a review-and-fix request,
use it for the review phase only.

## Workflow

Copy this checklist into your notes and finish every item in order. A review that skips an
item is not finished, and "no findings" is only valid after step 4.

```
- [ ] 1. Pin: head commit, base commit, merge base. Read-only from here.
- [ ] 2. Map: run <skill base directory>/scripts/changed_symbols.py; list each changed behavior.
- [ ] 3. Trace: apply every matching row of the trace table to each behavior.
- [ ] 4. Attack: two breaking inputs or call orders per changed hunk; prove or drop each.
- [ ] 5. Report: verified findings, then the trace log, then scope and limits.
```

### 1. Pin the revision

For a PR, read its metadata and fetch its head without touching the checkout:

```bash
gh pr view <n> --json title,body,baseRefName,baseRefOid,headRefOid,comments
git fetch origin "pull/<n>/head"
HEAD_SHA=$(git rev-parse FETCH_HEAD)    # save it: the next fetch overwrites FETCH_HEAD
BASE_SHA=$(git merge-base "origin/<baseRefName>" "$HEAD_SHA")
```

Read code only at the head commit: `git show "${HEAD_SHA}:path/to/file.py"` and
`git grep -n -w -e 'name' "${HEAD_SHA}" -- dir/`. Keep the braces and quotes, because zsh
treats `$HEAD_SHA:a...` as a modifier. Use the merge base, not the base branch tip, for
the diff: `git diff "${BASE_SHA}...${HEAD_SHA}"`. For local, staged or snippet reviews, see
[references/review-procedure.md](references/review-procedure.md).

You MUST NOT check out, switch, stash, reset, create branches or worktrees, edit files,
commit, push, post comments or approve. Do not run project tests unless the user asked.

### 2. Map the change

You MUST run the change map before reading code. It reads git objects only. The script is
in this skill's folder: use the "Base directory for this skill" path shown when the skill
loaded (or find it with `ls ~/.claude/skills ~/.claude/plugins 2>/dev/null`).

```bash
python3 "<skill base directory>/scripts/changed_symbols.py" "$BASE_SHA" "$HEAD_SHA"
```

It lists each changed function or class with its definitions and callers at the head
commit, calls the diff removed, and attributes it added. If Python is unavailable, collect
the same with `git diff` and `git grep`. Then read the whole diff and group the changes into
behaviors.

If the repository has a review guide (`PR_REVIEW.md`, `REVIEW.md`, or a review section in
`AGENTS.md`/`CLAUDE.md`) or a risk map (`REVIEW_INDEX.md`), read it now. Match each changed
path against the risk map's "Start tracing here" column and add every matching row to step 3.

### 3. Trace

For each behavior, apply every row whose left column matches the diff. You MUST write down
what each applied row found, even when the answer is "nothing changes".

| If the diff... | You MUST |
|---|---|
| changes what a function returns, raises, accepts or means | Go through every caller from the change map. For each, state what it now does differently. Find a concrete caller whose behavior changes, or state that none does. |
| changes a signature, or how a public or overridable method is called | Check subclasses and overrides in the repository, and the documented signature. Existing overrides and external callers written against the old form must still work. |
| removes, moves, reorders or "simplifies" code | List each side effect of the old code: calls, state set, hints, guards, ordering. Confirm each still happens on every path, including the custom or less common one. |
| adds a branch, case or mode beside existing ones | Compare it with its siblings. Every helper or step the siblings run (status, headers, validation, cleanup, hooks) must run here, or the skip must be deliberate. |
| adds a field, attribute or parameter | Find every place the object is built, copied, cloned, serialized or rebuilt. Grep a sibling field to find them. The new one must be carried through each. |
| iterates, indexes, splits or parses an input | Try a generator or iterator (consumed twice?), empty, `None`, a string where a list is expected, and unusual characters. |
| hands validation or conversion to a library or framework call | Read that callee and check what it returns for each kind of input it will receive: choices, booleans, nullable, subclasses. |
| introduces or changes state kept across calls or events | Check the initial state, the first event, and every event type, including ones the change did not target. |
| touches auth, tenancy, transactions, retries, migrations, caches or sync/async twins | Apply the matching risk-map row, or the generic one in [templates/REVIEW_INDEX.md](templates/REVIEW_INDEX.md). |

Minimum per behavior: one caller search, one base-versus-head comparison of the changed
function, and every matching row. Widen the search only to settle a concrete question; stop
when the evidence answers it.

### 4. Attack

For each changed hunk, write two concrete inputs or call sequences that could break it, then
trace each through the head commit. Keep a suspicion only if you can state the trigger, the
reachable path and the impact; otherwise drop it. Compare with the base to label each finding
"introduced in this PR" or "pre-existing".

### 5. Report

Findings first, most severe first. Leave out style, naming, docs and test nits, and anything
you could not verify.

```
### [High] Retry re-sends the webhook after a partial failure
`workers/delivery.py:88` (introduced in this PR)
Trigger: the HTTP call times out after the receiver accepted the request.
Impact: the event is delivered twice; receivers without dedupe double-charge.
Fix direction: persist the delivery id before sending and skip if already acknowledged.
```

| Severity | Meaning |
|---|---|
| Critical | Data loss or corruption, security or tenant breach, outage on a common path |
| High | Wrong results or failed operations on a realistic path; broken retry or idempotency |
| Medium | Wrong behavior on an edge path, a contract violation a caller will hit, a real performance regression |
| Low | Real but minor defect |

Then the trace log, one row per behavior:

```
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `send_webhook()` now retries on timeout | changes meaning; state across calls | 4 callers; delivery worker, admin resend read | finding 1 |
| new `region` field on `Account` | adds a field | serializer, `copy()`, CSV export | carried everywhere |
```

End with the reviewed head and base commits, what you could not check (tests not run, CI
not seen, stale head), and say plainly if no actionable findings remain. Never call a
build, lint or import check a passing test run.

## Related

Treat reviewer and bot comments as claims to verify at the head commit. Apply
`avoid-and-separate`, `complexity-check` or `design-system` only when they yield a real
finding. Suggest corrections to repository maps in the report; editing them is a separate
task.
