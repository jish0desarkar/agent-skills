# Prompt and setup

How the two sessions in this [example](README.md) were run, so you can repeat it.

## Snapshot

Each session got its own copy of a repository that ends at the PR's head commit and has no
git remote, so nothing after the PR (the bug report, the fix, later commits) was reachable:

```bash
git init snap && cd snap
git fetch --depth=400 https://github.com/aio-libs/aiohttp b48737e74f2a18d0345d2894566be02c5da47f6b
git update-ref refs/heads/master b48737e74f2a18d0345d2894566be02c5da47f6b
git fetch --depth=400 https://github.com/aio-libs/aiohttp refs/pull/12988/head
git checkout -b keep-ws-compression-state 7972054f2b7ccb28b158a9c98f7213bba8c43f0f
```

`master` is the PR's base (and the merge base). The newest commit in the snapshot is the
PR head, dated 13 July 2026. For the session with the skill, `skills/review/verified-code-review`
was copied to `.claude/skills/verified-code-review/` and `.claude/` was added to
`.git/info/exclude`, so the skill did not show up as a local change.

## Sessions

- Claude Code subagents, model Claude Sonnet 5.5, one run each, started at the same time.
- The prompts were identical except for one line: the session with the skill had
  `verified-code-review` in its list of installed skills. aiohttp's own `backport-failed`
  skill was listed in both.
- Afterwards, both transcripts were checked for web, `gh` or git network calls and for reads
  outside the snapshot. There were none, apart from one `ls` of the two `~/.claude` files
  that aiohttp's `CLAUDE.md` imports (they don't exist on the machine).

## Prompt (session with the skill)

`<repo>` stands for the snapshot's path. The PR description is not copied here; the
sessions received it verbatim from the PR page.

```text
You are working in a local clone of the aiohttp repository at:
<repo>
Treat that directory as your working directory: cd into it for every shell command and keep all reads inside it.

Project instructions (Claude Code loads these automatically from the repo's CLAUDE.md): read <repo>/AGENTS.md before you start.

Skills installed in this project (name: description). If one applies to the task, read its SKILL.md and the files it points to, then follow it:
- backport-failed: Create a manual backport to recover from a Patchback auto-backport failure. (<repo>/.claude/skills/backport-failed/SKILL.md)
- verified-code-review: <the description from SKILL.md's frontmatter> (<repo>/.claude/skills/verified-code-review/SKILL.md)

Environment limits: there is no network access. Do not use WebFetch, WebSearch, gh, curl, or any git command that contacts a remote; work only from the local repository. Shell commands available: git, ls, rg (no python, pytest or pip). Do not modify any files.

The user's request:

Review the changes on this branch (`keep-ws-compression-state`) against `master`. They come from a pull request titled "keep websocket compression state across interleaved control frames". The author's description:

> <the description of aio-libs/aiohttp#12988>

There is no network access here, so work from the local repository.

Your final message is your answer to the user.
```

The session without the skill got the same text without the `verified-code-review` line.
