---
name: knowledge-sync
description: Keep a repository's agent knowledge (AGENTS.md, CLAUDE.md, ARCHITECTURE.md, REUSE_INDEX.md, review guides) and its Codex/Claude skill copies true to the code, using independent checkpoints for the remote default branch and local work. Records unmerged local knowledge alongside merged knowledge in the same files and promotes it once merged (including squash/rebase merges). Use for requested knowledge maintenance or forced audits — not ordinary implementation, debugging or code review.
---

# Keep repository knowledge true to the code

Agent instructions rot. A map that names a moved function sends every future session to the
wrong file. This skill re-verifies the knowledge documents against what actually changed —
on the default branch and in your local work — and records exactly what it has checked so
the next run starts where this one stopped.

This is a separate documentation-maintenance task. Edit the affected artifacts, not
application code. Reading a review guide as maintenance input does not activate its review
workflow. Preserve all review-only restrictions in the resulting instructions.

Use the skill directory that was loaded; its `scripts/checkpoint.py` needs only Python 3.10+
and Git. Both Codex and Claude Code copies support this workflow.

## Scope and controls

Managed documents (in the checkout root, when present): `AGENTS.md`, `CLAUDE.md`,
`ARCHITECTURE.md`, `REUSE_INDEX.md`, `PR_REVIEW.md`, `REVIEW_INDEX.md`.
Managed skills: `progressive-search`, `verified-code-review`, `knowledge-sync`. Codex copies
live under `${CODEX_HOME:-$HOME/.codex}/skills/<name>`; Claude copies under
`.claude/skills/<name>` in the checkout. To manage other files or skills, edit `DOCUMENTS`
and `SKILLS` at the top of the script.

If the repository has no maps yet, bootstrap them first with `progressive-search` (its
templates), then run this skill to certify them.

- **Normal invocation:** inspect new default-branch commits and changed local code for knowledge impact.
- **`force <file, section, topic or skill>`:** also revalidate those targets even if both code
  states are unchanged or the delta seems insignificant. Natural-language requests suffice.
- **`force all`:** audit all managed artifacts against the default branch and the checkout.
- **`only <targets>`:** honor the limited scope, but do not advance the stamp unless both
  outstanding code states and all affected managed artifacts were also covered.
- **Explicit decisions** supplied by the user may update instructions without a code change.
  Preserve their rationale succinctly; never infer an agreed policy from a commit message alone.

Force bypasses the relevance filter, not validation, source accuracy, dirty-file protection
or ancestry checks. It does not mean rewrite everything, pull/switch branches, or reset a stamp.
Do not schedule recurring work, commit, push, modify ignore rules or run project tests.

## Knowledge layout and validity

Keep code-specific knowledge and decision notes in the existing Markdown files, under
`## Master knowledge` (merged into the default branch, whatever it is called) and
`## Local knowledge` (this checkout only). Use topic subheadings inside each section. Do not
create separate local index files. Keep general instructions outside these sections; files
with no source-specific facts need no empty provenance sections.

The distinction is provenance, not confidence or priority. Both sections contain valid,
usable knowledge. Always search both. For the current checkout, local facts and decisions
are fully applicable before merge; where local code changes default-branch behavior, use
the local behavior. For a PR/commit review, apply what exists at that target revision.
Never call local knowledge speculative or a fallback merely because it is unmerged.
Explicit user decisions remain authoritative regardless of which section records them.

Record the branch and local HEAD (and whether an entry depends on uncommitted work) in the
local section. Keep each entry independently movable; separate a merged contract from an
unmerged extension rather than labelling an entire mixed module local.

## 1. Pin the input and inspect the stamp

1. Confirm the checkout's remote is the intended repository (`git remote -v`) and identify
   the target: the remote's default branch, auto-detected from `refs/remotes/<remote>/HEAD`.
   If detection fails or the team integrates into a different branch, pass `--branch`
   (and `--remote` if not `origin`) on every call. Never substitute local HEAD or a cached ref.
2. Record checkout status and read existing target files before editing. These documents and
   `.claude/skills/` may be ignored by Git; include them explicitly. Preserve existing edits,
   user decisions and branch-specific entries. Do not run maintenance concurrently in the
   same checkout, or edit installed skill copies concurrently from another checkout.
3. Run `python3 <skill-dir>/scripts/checkpoint.py inspect --repo <checkout>`.
   It fetches the target branch without switching branches and returns its old/new SHAs and
   state token, plus an independent local snapshot/token/status, the merge base and local
   commit count. Local state captures branch, HEAD, staged patch, working patch and
   non-ignored untracked file contents. Managed documents, skills and the stamp are excluded
   to avoid a loop; their changes are reported separately as `artifact_drift`. Record both
   tokens for completion. The helper never judges significance or advances a checkpoint
   during inspection.
4. Network/fetch failure, malformed stamp, missing commit or shallow history: stop without
   changing the stamp. Recover the required history first (`git fetch --unshallow`); never
   substitute timestamps or silently reset. Rewritten target history requires an explicitly
   requested full rebaseline; normal force targets do not authorize that reset.

States:

- `bootstrap` — no stamp yet: validate existing entries against the target-branch and local
  code before stamping. This is a curated-map audit, not a dump of all repository files.
- `unchanged` — only the target branch is unchanged; still inspect `local_status`, forced
  targets and artifact drift. Report "up to date" only when BOTH states and the artifacts are unchanged.
- `ahead` — analyze the exact range below, plus forced or drifted artifacts.
- `rewritten` — keep the stamp; explain the divergence and ask for a full rebaseline.

The stamp records **analyzed-through**, not merely **last-fetched**. It stores the
target-branch SHA and the local snapshot independently. Local `changed` includes commits,
rebases, resets, branch switches, staging and dirty/untracked content changes. A local
bootstrap requires inspecting the existing local delta even when the target is unchanged.
Hashes detect change, not semantic correctness.

## 2. Analyze target-branch and local changes

Use the full captured SHAs as `STAMP` and `TARGET`, never moving branch names:

```bash
git log --reverse --topo-order --format='%H %s' "$STAMP..$TARGET"
git diff --name-status --find-renames "$STAMP" "$TARGET"
git show --format=fuller --stat <commit>
git diff "$STAMP" "$TARGET" -- <affected-paths>
git grep -n -e '<symbol>' "$TARGET" -- <likely-directory>
git show "${TARGET}:<path>"
```

Inventory every new commit, including merged branch commits; never use dates, `--no-merges`
or `--first-parent` as the sole coverage filter. Inspect per-commit patches when aggregate
diffs hide moves, merge resolutions, reversions or meaningful decisions. Start with changed
paths and imports, and read only the relevant implementation sections and callers at TARGET.
The working tree is not evidence for the target branch when it differs.

When local status changes or bootstraps, inspect the committed local delta from
`local_merge_base` to the captured local HEAD, then staged/unstaged patches and non-ignored
untracked source files:

```bash
git log "$TARGET..$LOCAL_HEAD"            # local commits
git diff "$LOCAL_BASE" "$LOCAL_HEAD"      # local branch work
git diff --cached                          # staged
git diff                                   # unstaged
git ls-files --others --exclude-standard   # new files
```

Do not mistake target-branch changes missing from an older local branch for local deletions.
Read actual working files for dirty content; staged content may differ from them. If there
is no shared merge base, report that and audit the local tree rather than inventing a diff.
The helper stores fingerprints, not old patches, so re-evaluate the current local delta and
reconcile existing notes rather than claiming an unavailable before/after diff.

**Promotion.** Reconcile local notes whenever either state changes. Verify each against the
target branch: if its behavior or decision is now present there, MOVE it into the matching
master topic, keep its rationale, and remove the local duplicate. This handles normal,
squash, rebase and cherry-pick merges — ancestry or commit IDs alone do not prove promotion.
If only part merged, promote that part and keep the rest local. A staged/unstaged extension
stays local even when the preceding committed feature has merged. Promotion happens on the
next maintenance run; no background monitor is implied.

On branch switches, resets or discarded edits, remove obsolete code-derived local entries or
update their scope; never present unavailable code as active. Preserve explicit user
decisions with their correct scope unless superseded, even if the code was reverted.

**What is significant:** owner moves/renames/deletions; new genuinely reusable APIs; changed
validation, authorization, persistence or sync/async contracts; new architectural boundaries;
changed check/build commands; recurring failure patterns that change review guidance; and
explicit workflow decisions. Routine formatting, internal-only renames and unchanged public
behavior usually need no entry. Confirm with code, not commit titles.

Update only the relevant map or skill. Keep maps curated and skills focused; never append a
changelog to every artifact. Do not convert existing implementation debt into a new policy.
Put branch-specific facts in the checkout's Markdown sections, not in globally installed skills.

### Repairing missing workflow coverage

Treat a user-reported missing topic as a forced target, even when both checkpoints are
unchanged. A path or symbol appearing in an index does not mean its workflow is covered.
During bootstrap or a forced topic audit, trace the topic's entry point, orchestration,
state, dispatch/handlers, persistence/confirmation and output boundaries where applicable,
and document the owners and relationships in the existing maps. Distinguish registered
declarations or stubs from implemented behavior. For example, for an LLM chat feature that
means prompt/history assembly, the tool loop, the tool registry/executor, per-step handlers,
drafts, and confirmation/replay.

Check repaired coverage against target-branch and local code before stamping. Describe an
existing omission as a coverage repair, not a new code change. Ordinary runs stay
incremental; this does not require a whole-repository survey every time.

## 3. Update counterparts and validate

When changing a managed Codex `SKILL.md`, inspect the matching Claude `SKILL.md` first and
update it in the same run (and vice versa). Create a missing counterpart when that skill
changes. Keep shared guidance identical; preserve necessary platform metadata (Codex-only
`agents/openai.yaml` stays in the Codex copy unless the Claude copy needs it). Mirror
changed supporting scripts too. If copies already differ, reconcile useful edits from both;
never blindly overwrite one.

Changing this skill's Git/state logic requires exercising the helper in temporary Git
repositories (bootstrap → complete → local edit → remote advance → stale token); it does not
authorize project tests or application imports.

Check target-branch claims against TARGET and local claims against the captured checkout
state. Check changed links, paths and symbols, and that review-only and implementation
guidance stay separated. Validate skill frontmatter with an available skill validator and
compare counterpart content. Record which significant groups were covered and why the
others needed no change. A partial or failed audit must keep the stamp.

## 4. Advance only after successful completion

After outstanding target/local changes, promotion, affected artifacts, forced targets and
artifact drift are analyzed and validated, run (with the same `--remote`/`--branch`, if used):

```bash
python3 <skill-dir>/scripts/checkpoint.py complete --repo <checkout> \
  --target <captured-target-sha> --expected-token <captured-token> \
  --expected-local-token <captured-local-token> \
  --summary '<brief coverage and update/no-change result>'
```

This atomically writes `KNOWLEDGE_STAMP.json` in the checkout. Use `missing` as the token
only for bootstrap. The helper rejects stale tokens, targets no longer on the target branch,
and local code that changed since inspection, so unexamined edits cannot be silently
certified. Only an explicitly requested full rebaseline may pass `--rebaseline`; a local
branch switch or rebase is ordinary local change, not a rebaseline.

The agent must certify semantic coverage; the helper only enforces Git/state checks. Advance
after a complete no-significant-change analysis too, to avoid repeating work. If the remote
advanced during the run, stamp only the analyzed TARGET and report that newer commits remain.
Never stamp a newly fetched head without analyzing it.

Report: both checkpoints, commits/dirty changes examined, notes promoted or reconciled,
affected files and mirrored skills, forced targets, validation, and anything pending.
The stamp and artifacts are local to this checkout; keep them together when sharing or
moving them. Never edit an agent's private memory files as part of this workflow.
