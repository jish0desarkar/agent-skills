# Skills for engineers who want to stay in charge

Agent skills for Claude Code, Codex and Cursor. They let an AI agent write production code while you keep a clear picture of how your codebase works.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-d97757)
![Codex](https://img.shields.io/badge/Codex-compatible-black)

Coding agents are fast, and they cut corners. They copy the same logic into two places, add another `if` to a function that already has forty, cache values that should be computed, and report "tests pass" when no test ran. A few weeks of that and nobody on the team can explain how the code works.

I wrote these skills while shipping a production FastAPI, HTMX and Celery SaaS app with agents every day. Each one is a short set of rules aimed at a problem I kept running into. They are opinionated, they work together, and you are meant to fork them.

> [!TIP]
> The skills are written to work in any codebase, and they look up your project's details on their own. You will still get much better results if you tailor them. After installing, ask your agent something like:
>
> *"Read the skills in `.claude/skills/` and adapt them to this codebase. Replace the generic code examples with real ones from our code, point the paths and folder names at our actual layout, and add the bugs and hotspots we keep hitting."*
>
> A rule that names your own files and your own past bugs is followed far more reliably than a generic one. Do this per project, and repeat it when the codebase changes shape.

## Install

Pick one method. Installing the same skills twice gives you duplicates.

### Claude Code

As a plugin, which updates when this repo changes:

```
/plugin marketplace add jish0desarkar/agent-skills
/plugin install jishnu-skills@jish0desarkar
```

If you plan to tailor the skills (see the tip above), copy them into your project instead, so the agent can edit them:

```bash
git clone https://github.com/jish0desarkar/agent-skills
mkdir -p .claude/skills
cp -R agent-skills/skills/*/* .claude/skills/          # this project only
# or: cp -R agent-skills/skills/*/* ~/.claude/skills/  # every project
```

### Codex

```bash
mkdir -p ~/.codex/skills
cp -R agent-skills/skills/*/* ~/.codex/skills/
```

Each skill includes `agents/openai.yaml`, so Codex shows it with a display name and a default prompt.

### Cursor and other agents

```bash
npx skills@latest add jish0desarkar/agent-skills
```

The installer asks which skills you want and which agents to install them for. To copy by hand, put the skill folders in `~/.cursor/skills/` (all projects) or `.cursor/skills/` (one project).

## How to use them

Most skills start on their own. Your agent reads each skill's description and loads the skill when the task matches. For example, editing backend code brings in `avoid-and-separate`, and asking for a PR review brings in `verified-code-review`. You don't have to do anything.

You can also call a skill by name when you want it for sure:

| Agent | How to call a skill |
|---|---|
| Claude Code, copied skills | `/build-with-ownership Add rate limiting to the login endpoint` |
| Claude Code, plugin | `/jishnu-skills:build-with-ownership Add rate limiting to the login endpoint` |
| Codex | `Use $complexity-check on the functions I changed` |
| Cursor | `Use the verified-code-review skill on this branch` |

`build-with-ownership` is the one exception: it never starts on its own. It runs a long workflow with checkpoints where you approve the plan, so you decide when to start it.

Some prompts that work well:

- *"/build-with-ownership Add webhook retries with an outbox"* to plan and build a feature with you approving each step.
- *"Review PR 123"* for a review that reports only bugs it can prove.
- *"Check the complexity of what you just changed"* after a big edit.
- *"Verify this in the browser"* before you call a UI change done.
- *"Set up the repository maps"* once per repo, then *"run knowledge sync"* now and then to keep them current.

## The skills

### Workflow

| Skill | What it does |
|---|---|
| [build-with-ownership](./skills/workflow/build-with-ownership/SKILL.md) | My main skill. It runs a feature through nine phases: agree on the behavior, map the existing code, design, plan the tests, build in small slices, read the diff, attack the diff, collect evidence, then quiz you on what was built. The agent does the typing; you keep the decisions about architecture, invariants and failure handling. It rates each task as tiny, medium or high risk and adds approval steps only where the risk calls for them. It also has bug, refactor, review and quiz modes. |
| [verify-in-browser](./skills/workflow/verify-in-browser/SKILL.md) | Checks a web change in the running app. The shared dev server is often running old code or another branch, so the skill starts a separate copy of the app on your code, signs in safely, drives a real or headless browser, and reports what it saw. It also warns about two traps: background workers that still run old code, and hidden browser panes that freeze animations. |

### Code quality

| Skill | What it does |
|---|---|
| [avoid-and-separate](./skills/code-quality/avoid-and-separate/SKILL.md) | Applies *Out of the Tar Pit* (Moseley & Marks, 2006). Before the agent adds a field, column or cache, it has to say whether the data is essential (users care about it) or accidental (it can be computed from other data). Code is then split into four layers that may only depend downward. The skill blocks logic copied between twin code paths (async web and sync worker, or preview and production), stored values that could be computed, untyped dicts, and code that depends on statement order for no reason. It includes grep commands for finding this debt. |
| [complexity-check](./skills/code-quality/complexity-check/SKILL.md) | Limits cyclomatic complexity (Ruff `C901`) and cognitive complexity (`complexipy`) for the code the agent changed. Because it ignores untouched code, it works in repos that are already full of complex functions. It maps each common cause to a fix, lists equivalent tools for JS/TS and Go, and when no tool is available it scores by hand and labels the score as an estimate. It forbids splitting a function just to lower the number. |
| [design-system](./skills/code-quality/design-system/SKILL.md) | Keeps the agent inside your design system. It may only use primitive classes and tokens that already exist, and must ask you before adding a new one. It has to use as few classes as possible, and loading skeletons must match the layout of the content they replace. If you have a stylesheet but no written rules, it can draft a `DESIGN.md` from it. |

### Review

| Skill | What it does |
|---|---|
| [verified-code-review](./skills/review/verified-code-review/SKILL.md) | A review that never edits code. The agent fetches the exact commits under review, follows each changed behavior into its callers and callees, and compares against the old version to separate new bugs from old ones. It reports only bugs it can prove, each with a severity, the input that triggers it, and a file and line. Build and lint results never count as passing tests. It comes with a [review procedure](./skills/review/verified-code-review/references/review-procedure.md) and a [risk map template](./skills/review/verified-code-review/templates/REVIEW_INDEX.md) that covers auth, migrations, retries, caches, background jobs and LLM calls. |

### Codebase knowledge

| Skill | What it does |
|---|---|
| [progressive-search](./skills/codebase-knowledge/progressive-search/SKILL.md) | Makes the agent look for existing code before writing a new helper. It starts with about 3 searches and 5 files, guided by `ARCHITECTURE.md` and `REUSE_INDEX.md`, and has to explain why whenever it searches wider. This stops agents from rebuilding a helper that already exists a few files away. It includes [templates](./skills/codebase-knowledge/progressive-search/templates/) for both maps and steps for creating them in a new repo. |
| [knowledge-sync](./skills/codebase-knowledge/knowledge-sync/SKILL.md) | Keeps the agent docs (`AGENTS.md`, `CLAUDE.md`, the maps and the review guides) in line with the code. It tracks the remote default branch and your local work separately, using a [Python script with no dependencies](./skills/codebase-knowledge/knowledge-sync/scripts/checkpoint.py) that marks the docs as current only after every change has been checked. Notes about your local work move into the main sections once that work is merged, including squash merges. |

## How they fit together

```
            ┌──────────────────────────┐
            │  build-with-ownership    │  what to build, and who decides
            └────────────┬─────────────┘
                         │
   progressive-search    →  should new code exist at all?
   avoid-and-separate    →  where may state and logic live?
   complexity-check      →  how complex may a function be?
   design-system         →  what may the UI use?
                         │
     ┌───────────────────┴──────────────────────┐
     │ verify-in-browser · verified-code-review │  evidence that it works
     └───────────────────┬──────────────────────┘
                         │
                  knowledge-sync     keeps the maps true
```

Each skill covers one question and refers to the others instead of repeating them. When two of them disagree, pick the simpler code that still respects the layers.

## Getting the most out of them

1. Tailor the skills to your codebase, as described in the tip at the top. This makes the biggest difference.
2. Create the maps. Ask *"set up the repository maps with progressive-search"*. The agent fills in `ARCHITECTURE.md` and `REUSE_INDEX.md` from the templates and shows you the drafts before saving.
3. Add a review risk map if you review a lot of PRs. Copy [`REVIEW_INDEX.md`](./skills/review/verified-code-review/templates/REVIEW_INDEX.md) to your repo root and replace the example paths with real ones.
4. Run *"knowledge sync"* every so often. It only checks what changed since the last run.
5. After your first `verify-in-browser` run, let it save the steps that worked to `AGENTS.md` so later runs are quicker.

`build-with-ownership`, `complexity-check` and `avoid-and-separate` are useful without any setup.

## Principles

- You own the design. The agent can explore, write boilerplate and run commands, but architecture, transactions, security and risky tradeoffs stay with you.
- Show the evidence. "Tests pass" means the output is there to see. Code that was only read is reported as a manual review.
- Fix the design instead of the score. Splitting a function into `_part_1` and `_part_2` fixes nothing.
- Search before you write. Reusing an existing helper is cheaper than maintaining a second copy of it.
- Say when you compromise. If accidental complexity is truly needed, the agent states what it added, why, and what keeps it correct.

## Layout

```
skills/
  workflow/            build-with-ownership, verify-in-browser
  code-quality/        avoid-and-separate, complexity-check, design-system
  review/              verified-code-review
  codebase-knowledge/  progressive-search, knowledge-sync
.claude-plugin/        Claude Code plugin and marketplace manifests
```

Each skill is a folder with a `SKILL.md` and an `agents/openai.yaml` for Codex. Some also have `scripts/`, `references/` or `templates/`.

## Contributing

Issues and PRs are welcome. I'd especially like to hear how you adapted a skill to your own stack. If one of these saved you from an agent mess, a star helps other people find the repo.

## License

[MIT](./LICENSE) © Jishnu De Sarkar
