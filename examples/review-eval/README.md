# Eval: verified-code-review against stock Claude Code

**On real pull requests that later shipped bugs, Claude Code with `verified-code-review` found 50% more of the bugs than stock Claude Code, with a tenth of the noise, at the same cost.**

- **More real bugs:** 7.5 of 16 known bugs per run on average, against 5 for stock.
- **It wins on PRs it was never tuned on:** 3 holdout catches across two runs, against 1 for stock.
- **It finds bugs stock never finds:** the lost database-router hint in django/django#17554 (both runs) and the `bulk_create` ordering bug in django/django#19277. Stock missed both in every run.
- **It never loses ground:** every known bug that stock caught, the skill caught too.
- **About 10× less noise:** 7 nits and speculative items across two runs, against 74 for stock.
- **Fewer false alarms:** 3 false positives across two runs against stock's 8, and none at all in one run.
- **No extra cost:** about $2.45 for 14 reviews either way, and under a minute per review.

Claude Code (Sonnet 5.5) reviewed 14 real merged pull requests from aiohttp, FastAPI, Django and pandas. Twelve of them shipped bugs that the maintainers fixed later, 16 known bugs in total, and two are controls with no known bug. Each PR was reviewed four times: twice by stock Claude Code, which picked its built-in `code-review` skill, and twice with this repo installed as a plugin, which picked `verified-code-review`. Every review was graded blind against the maintainers' later fixes.

Four of the PRs are holdouts (pandas#63473, pandas#64529, django#19277, django#19925). They were chosen after the skill's trace rules were written and played no part in designing them.

## Results

| | Stock, run 1 | Stock, run 2 | Skill, run 1 | Skill, run 2 |
|---|---|---|---|---|
| Known bugs caught (of 16) | 6 | 4 | **8**, plus 1 partial | **7**, plus 1 partial |
| … on the 4 holdout bugs | 1 | 0 | **2** | **1** |
| False positives | 5 | 3 | **0** | 3 |
| Noise (nits and speculation presented as problems) | 32 | 42 | **3** | **4** |
| Other real problems reported | 15 | 16 | 15 | 10 |
| Cost for 14 reviews | $2.45 | $2.31 | $2.48 | $2.42 |

Why it does better:

- **It traces where regressions hide.** For each kind of change, the skill's trace table says what must be checked: a changed helper means every caller, a refactor means every side effect the old code had, a new branch means everything its siblings do. That is how it found the custom `Prefetch` querysets in django/django#17554 losing their router hint after a "simplification" that stock reviews read as harmless.
- **It treats a changed meaning as a finding to prove.** On holdout django/django#19925, one stock run noticed that the foreign key now gets rebuilt when only `on_delete` changes, then called it fine. Both skill runs reported it as the regression it was.
- **It proves before it reports.** Every suspicion goes through an attack step and is kept only with a trigger, a path and an impact. That is why the reviews are short and almost free of noise.
- **It does what it says.** The change-map script ran, and a trace log was written, in 26 of 28 reviews.

## Per PR

C = caught, P = partial, M = missed, one letter per known bug. fp = false positives, n = noise.

| PR | What broke later | Stock 1 | Stock 2 | Skill 1 | Skill 2 |
|---|---|---|---|---|---|
| [aio-libs/aiohttp#12988](https://github.com/aio-libs/aiohttp/pull/12988) | Compressed WebSocket message rejected after a leading ping/pong | C, n2 | C, n3 | C | C |
| [fastapi/fastapi#15030](https://github.com/fastapi/fastapi/pull/15030) | SSE ignores `status_code`; `splitlines()` corrupts data; item type lost via `include_router()` | M C M, n4 | M C M, n4 | M C M | M C M |
| [django/django#17554](https://github.com/django/django/pull/17554) | Old-signature `from_db()` overrides crash; custom `Prefetch` querysets lose router hints | M M | M M, n6 | M **C** | M **C**, n1 |
| [django/django#20009](https://github.com/django/django/pull/20009) | Iterator passed to `__in` gets consumed | M, fp1 n2 | M, n2 | M | M |
| [django/django#20718](https://github.com/django/django/pull/20718) | Changelist crash for some `list_display` relation paths | C, fp3 n5 | C, fp1 n4 | C, n1 | C, fp1 n1 |
| [django/django#20538](https://github.com/django/django/pull/20538) | Admin search crash on `choices` fields; boolean over-matching | M C, n2 | M M, n3 | M C | M C |
| [django/django#19534](https://github.com/django/django/pull/19534) | False deprecation warning for template string literals | C, n1 | C, n1 | C | C |
| [django/django#21420](https://github.com/django/django/pull/21420) | Python default used instead of `db_default` for a primary key | M, n2 | M, n4 | P | P, fp2 |
| [django/django#21344](https://github.com/django/django/pull/21344) (control) | none known | n2 | n3 | n1 | n1 |
| [fastapi/fastapi#15863](https://github.com/fastapi/fastapi/pull/15863) (control) | none known | — | fp1 n2 | — | — |
| [pandas-dev/pandas#63473](https://github.com/pandas-dev/pandas/pull/63473) (holdout) | `read_json` turns non-date strings into year-1 timestamps | M, fp1 n2 | M, fp1 n3 | M | M |
| [pandas-dev/pandas#64529](https://github.com/pandas-dev/pandas/pull/64529) (holdout) | Full-slice setitem shares memory with the caller's array | M, n3 | M, n3 | M, n1 | M |
| [django/django#19277](https://github.com/django/django/pull/19277) (holdout) | `bulk_create` sorts objects before related primary keys are set | M, n3 | M, n3 | **C** | M, n1 |
| [django/django#19925](https://github.com/django/django/pull/19925) (holdout) | Python-level `on_delete` change now alters the schema | C, n4 | M, n1 | C | C |

Every review is in [reviews/](reviews/), and every grade, with the grader's reasoning, is in [grades/](grades/).

## How it was run

- **Offline and blind.** Each review ran in a fresh clone that ends at the PR. Its `origin` is a local mirror holding only the base branch and the PR ref, and an offline stand-in for `gh` serves the PR's title and description. Shell commands ran in Claude Code's sandbox with all network access denied, so no session could see the later bug report or fix.
- **A realistic checkout.** The clone was on the base branch with some uncommitted "user work" in it, which is the normal state when you ask an agent to review a PR.
- **Same everything else.** All sessions used Claude Sonnet 5.5 at its default effort, with no user settings and no MCP servers. The prompt was `Review PR #<n>`, plus one line saying the mirror and `gh` work offline. That line was needed because stock Claude Code assumed the sandbox meant it couldn't fetch the PR.
- **Answer keys first.** The [answer keys](answer-keys.md) were written from the maintainers' fixes before any review ran, and each bug was confirmed to exist in the PR as submitted. A candidate whose bug was not in the submitted PR was dropped.
- **Blind grading.** One Claude Opus 5.5 session per PR graded all four of its reviews, labelled in random order. It checked every claim against the PR's code and could run code locally. Its verdicts on the skill's extra catches were spot-checked by hand.

The scripts are in [harness/](harness/).

## Limits

- **Small sample.** There were two runs per setup and 16 known bugs. The gain is consistent across both runs and both PR sets, but this is evidence, not a benchmark.
- **Fewer side findings in one run.** Because the skill reports only what it has traced and proven, one run listed fewer additional real problems beyond the known bugs (10 against stock's 15–16).
- **The PRs were chosen to suit the skill.** They are regressions where tracing callers and contracts matters. That is a fair test of what the skill is for, not a random sample of PRs. The four holdouts guard against the rules having been tuned to the others.
- **Shallow reviews.** At default effort, reviews took under a minute. Deeper settings might change both detection and the gap.
- **Grading is a model's judgement.** It follows keys written in advance and checks claims against code, but it can still be wrong.
