# Eval: verified-code-review on 10 real pull requests

Claude Code reviewed 10 merged pull requests from aiohttp, FastAPI and Django in three setups, and every review was graded blind against what the maintainers later had to fix.

- **Stock:** Claude Code as installed. It picked its built-in `code-review` skill every time.
- **Skill:** the same, plus this repo installed as a plugin. It picked `verified-code-review` every time.
- **Skill + maps:** the same as Skill, plus `ARCHITECTURE.md`, `REUSE_INDEX.md` and `REVIEW_INDEX.md` written by a separate session from the repository as it was before the PR.

Eight of the PRs shipped bugs that the maintainers fixed later (12 known bugs in total). Two are controls with no known bug.

## Results

| | Stock | Skill | Skill + maps |
|---|---|---|---|
| Known bugs caught (of 12) | 5 | 5, plus 1 partial | 5, plus 1 partial |
| Other real problems reported | 12 | 12 | 11 |
| False positives | 3 | 2 | 2 |
| Noise (nits and speculation presented as problems) | 18 | 10 | 11 |
| Changed the user's checkout | 7 of 10 runs | 0 of 10 | 0 of 10 |
| Cost for all 10 reviews | $1.71 | $1.54 | $1.76 |

What this shows, and doesn't:

- **The skill did not find more bugs.** Every setup caught the same five, and all three missed the same six. The one difference is django/django#21420. There the skill traced the exact code path the maintainers later fixed, and proposed the same fix, but it named the wrong trigger, so it gets partial credit.
- **It reported less noise and slightly fewer false alarms.** It produced 10 nits against stock's 18, and 2 false positives against 3. On django/django#20718 every setup caught the bug, but stock added 2 false positives and 4 nits, while the skill added none and one.
- **It left your checkout alone.** In 7 of 10 runs, stock Claude Code checked out the PR in the working tree and left a new branch behind. The skill read the PR from git objects and changed nothing, which is what it promises.
- **The maps made no measurable difference** at this size.

## Per PR

C = caught, P = partial, M = missed, one letter per known bug. fp = false positives, n = noise.

| PR | What broke later | Stock | Skill | Skill + maps |
|---|---|---|---|---|
| [aio-libs/aiohttp#12988](https://github.com/aio-libs/aiohttp/pull/12988) | Compressed WebSocket message rejected after a leading ping/pong | C, n1 | C, n1 | C, n1 |
| [fastapi/fastapi#15030](https://github.com/fastapi/fastapi/pull/15030) | SSE ignores `status_code`; `splitlines()` corrupts data; item type lost via `include_router()` | M C M, n4 | M C M, n1 | M C M, n2 |
| [django/django#17554](https://github.com/django/django/pull/17554) | Old-signature `from_db()` overrides crash; custom `Prefetch` querysets lose router hints | M M | M M, n1 | M M |
| [django/django#20009](https://github.com/django/django/pull/20009) | Iterator passed to `__in` gets consumed | M, fp1 n2 | M, n1 | M, fp1 |
| [django/django#20718](https://github.com/django/django/pull/20718) | Changelist crash for some `list_display` relation paths | C, fp2 n4 | C, n1 | C, n1 |
| [django/django#20538](https://github.com/django/django/pull/20538) | Admin search crash on `choices` fields; boolean over-matching | M C, n2 | M C | M C, n1 |
| [django/django#19534](https://github.com/django/django/pull/19534) | False deprecation warning for template string literals | C, n1 | C | C |
| [django/django#21420](https://github.com/django/django/pull/21420) | Python default used instead of `db_default` for a primary key | M, n2 | P, fp2 n1 | P, fp1 n2 |
| [django/django#21344](https://github.com/django/django/pull/21344) (control) | none known | n2 | n2 | n2 |
| [fastapi/fastapi#15863](https://github.com/fastapi/fastapi/pull/15863) (control) | none known | — | n2 | n2 |

Every review is in [reviews/](reviews/) and every grade, with the grader's reasoning, is in [grades/](grades/).

## How it was run

- **Offline and blind.** Each review ran in a fresh clone that ends at the PR. Its `origin` is a local mirror holding only the base branch and the PR ref, and an offline stand-in for `gh` serves the PR's title and description. Shell commands ran in Claude Code's sandbox with all network access denied, so no session could see the later bug report or fix.
- **A realistic checkout.** The clone was on the base branch with some uncommitted "user work" in it, which is the normal state when you ask an agent to review a PR. Afterwards the branch, HEAD, the uncommitted work, the stash and any new branches were checked.
- **Same everything else.** All sessions used Claude Sonnet 5.5 at its default effort, no user settings and no MCP servers. The prompt was `Review PR #<n>`, plus one line saying the mirror and `gh` work offline. That line was needed because stock Claude Code assumed the sandbox meant it couldn't fetch the PR.
- **Answer keys first.** The [answer keys](answer-keys.md) were written from the maintainers' fixes before any review ran. Each bug was also confirmed to exist in the PR as submitted. One candidate was dropped because it didn't.
- **Blind grading.** One Claude Opus 5.5 session per PR graded its three reviews, labelled X, Y and Z in random order. It checked every claim against the PR's code and could run code locally. Its false-positive calls were spot-checked by hand.
- **Maps built blind.** Each map was built from the repository at a commit before every PR that used it, following this repo's own setup instructions.

The scripts are in [harness/](harness/).

## Limits

- **One run per PR and setup.** A second run could differ, and with 12 known bugs a one-bug difference is within noise.
- **The PRs were chosen to suit the skill.** They are regressions where tracing callers and contracts matters. That is a fair test of what the skill is for, not a random sample.
- **Shallow reviews.** At default effort, reviews took about 40 seconds and 5–14 tool calls. Deeper settings might change both detection and the gap between setups.
- **Grading is a model's judgement.** It follows a key written in advance and checks claims against code, but it can still be wrong.
