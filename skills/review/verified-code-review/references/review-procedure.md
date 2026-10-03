# Review procedure

Details behind the workflow in `SKILL.md`: local and staged reviews, snippets, comment
triage and validation rules. A repository can copy this file to `PR_REVIEW.md` and
specialize it.

## Establish the exact target

- Record the requested focus and exclusions. A specific concern gets a direct answer first.
- Inspect checkout status; preserve staged, unstaged and untracked work. Do not switch
  branches, stash, reset, create worktrees, edit code/docs, commit or push for a review.
- For a live PR, obtain its repository, URL, base/head SHAs, current diff and relevant
  checks/comments (`gh pr view <n> --json baseRefName,headRefOid,baseRefOid,url,comments`).
  Use its actual base branch, including for stacked PRs; do not assume the default branch.
- Fetch the PR head/base into Git objects without changing the checkout
  (`git fetch origin pull/<n>/head` then `HEAD_SHA=$(git rev-parse FETCH_HEAD)`). Save each
  resolved SHA immediately: another fetch overwrites `FETCH_HEAD`. Verify fetched SHAs
  against live metadata. Compute the merge base, then inspect merge-base-to-head changes.
- Read and search that exact revision with `git show` and `git grep`. Local `rg` results
  are not PR-head evidence unless the searched files are verified identical to that revision.
- Before finalizing a live review, recheck its head/base. If either moved, refresh the diff
  and affected evidence. If unavailable, identify the reviewed snapshot and the freshness limit.
- For local review, distinguish staged (`git diff --cached`), unstaged (`git diff`) and
  combined changes (`git diff HEAD`); inspect relevant untracked files separately
  (`git ls-files --others --exclude-standard`). Follow the requested scope.
- For supplied snippets, state which callers/context were unavailable.

## Discover progressively from the diff

1. Inventory all changed files/hunks within the requested scope; group them by behavior.
2. Read changed functions and their immediate imports/callers. Use only the relevant rows of
   the risk map; architecture and reuse maps are optional navigation aids, not proof about
   the target SHA.
3. Start each behavior with roughly 3 targeted searches and 5 contextual candidate files.
   This budget excludes the changed-file inventory and is not a cap on review coverage.
4. Broaden only to settle a concrete hypothesis: caller contract, tenant boundary,
   sync/async or web/worker counterpart, transaction, retry, migration, index lifecycle or
   UI response.
5. Stop investigating when current evidence disproves the candidate. Do not scan unrelated
   directories or demand exhaustive proof that an alternative implementation does not exist.

Use filenames and matching lines before opening large sections:

```bash
git grep -n -e 'symbol' "$HEAD_SHA" -- path/to/domain
git show "$HEAD_SHA:path/to/file.py"
git diff "$BASE_SHA...$HEAD_SHA" --stat
```

For local-change reviews, use `rg --files`, `rg -l`, then `rg -n` in likely directories.
Use read-only `ast-grep run` only when a syntax pattern meaningfully narrows the search; do
not run it against a different checkout and describe the result as PR evidence.

## Decide whether a finding is real

- Establish a concrete trigger, a reachable path at the current target, and user/system
  impact. Trace inputs, types/return shapes, authorization, state changes and error handling
  as needed.
- Compare the base before calling something a regression. For PRs, report introduced or
  newly exposed defects; mention pre-existing issues only when requested or needed for context.
- For a general code audit without a baseline, do not invent a regression claim.
- Treat reviewer/bot comments as hypotheses. Recheck resolved comments and requested fixes
  at the current head; when asked for new issues only, do not repeat covered findings.
- Report correctness, data integrity, security, meaningful performance or concrete contract
  violations. Do not inflate style preferences, hypothetical abstractions or cleanup into
  bugs. For a requested style/design review, evaluate that contract and label findings accurately.

## Validate and report

Prefer source/contract inspection and existing CI evidence. Do not add/run project tests
unless explicitly requested. Do not start the app, run migrations or touch live data merely
to review it. Authorized runtime probes must use the reviewed revision and isolated resources.

Distinguish inspection, lint, syntax checks, import checks, image builds and actual test
runs. Green checks establish only what their commands executed; read the CI configuration
and logs before relying on them.

Report findings first, ordered by severity. Each needs a short title, verified file/line,
trigger, impact and the smallest useful correction direction. Keep comments concise and
deduplicate common root causes. Then identify the reviewed SHA/scope, checks performed and
material limits. If no actionable findings remain, say so without implying exhaustive
correctness. Posting comments, submitting reviews or approving a PR requires explicit
authorization.
