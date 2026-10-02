# Example: reviewing a PR that shipped a regression

[aio-libs/aiohttp#12988](https://github.com/aio-libs/aiohttp/pull/12988) changed one line in aiohttp's WebSocket reader to fix a real compression bug. A maintainer reviewed it, it was merged on 13 July 2026, and it shipped in aiohttp 3.14.2. On 27 July a user reported that valid compressed messages were now being rejected ([aio-libs/aiohttp#13274](https://github.com/aio-libs/aiohttp/issues/13274)), and the maintainers fixed it in [aio-libs/aiohttp#13302](https://github.com/aio-libs/aiohttp/pull/13302).

I gave the PR to two blind Claude Code sessions, one with `verified-code-review` installed and one without, and scored both against the maintainers' fix.

**Both sessions found the regression.** On this PR the skill did not decide whether the bug was found. It changed how the review was done and what it reported, and its fix and regression test match what the maintainers later merged.

| | With `verified-code-review` | Without the skill |
|---|---|---|
| Found the regression | Yes: rated High, "introduced in this PR" | Yes: rated blocking |
| False positives | 0 | 0 |
| Other findings | 1 cosmetic, same root cause | 5 minor: a test fixture, changelog wording, a duplicate `CONTRIBUTORS` entry, a stale value in an error message, a Cython test reminder |
| Fix vs. the maintainers' fix | The same two changes: run the compression latch for data frames only, and (marked optional) reject RSV1 on control frames | Main suggestion: start `_frame_fin` as `True` (also correct, but a different fix). Alternative: keep control frames out of the latch |
| Regression test vs. the maintainers' test | Same shape: a control frame, then a compressed TEXT `hello`. PING where the maintainers used PONG | Similar: PING, then a compressed BINARY message |
| Read the code from | Git objects at the pinned head commit | Mostly the working tree |
| Stated scope and limits | Head, base and merge-base commits, what was traced, that no tests ran, that it may be stale against the live PR | That no tests ran |
| Tool calls, time, tokens | 42, 10.8 min, 203k | 38, 10.1 min, 175k |

The full reviews: [with the skill](review-with-skill.md), [without the skill](review-baseline.md).

## The bug

Control frames (ping, pong, close) can arrive between the fragments of a data message. The PR stopped them from updating `_frame_fin`, so a ping in the middle of a compressed message no longer made the next fragment reset the compression flag (comments left out):

```diff
-                self._frame_fin = bool(fin)
+                if opcode <= 0x7:
+                    self._frame_fin = bool(fin)
```

The compression latch just above that line still ran for control frames, and `_frame_fin` starts as `False`. So when the first frame on a connection is a control frame:

1. A PONG arrives with RSV1=0. The compression flag is still unset, so the latch sets it to "uncompressed". `_frame_fin` stays `False`.
2. The first compressed message arrives with RSV1=1. `_frame_fin` is `False` and the flag is already set, so the reader raises "Received frame with non-zero reserved bits" and the connection closes with 1002.

That order is ordinary: a server with a heartbeat sends a PING, the browser answers with a PONG, then the page sends its first message. Before the PR, the PONG set `_frame_fin = True` and the next message set the flag correctly.

## How it was run

- **Blind.** Each session worked in an offline copy of aiohttp that ends at the PR's head commit and has no git remote, so the bug report and the fix were out of reach. Both transcripts were checked afterwards: neither made a web, `gh` or git network call.
- **One difference.** Same model (Claude Sonnet 5.5), same prompt: review this branch against `master`, with the PR's title and description. The only difference was one line listing the installed skill, in the form Claude Code uses (name, description, path). The session with the skill chose to load it and read its review procedure and risk-map template.
- **Key first.** The [answer key](answer-key.md) was written before either review was read.
- **Checked.** The findings in both reviews were checked against the code, and all of them held up. The other session's frame-sequence model and both proposed tests were not re-run.

The [prompt and setup](prompt.md) has the exact prompt and the commands to rebuild the snapshot.

## What the skill changed

Without the skill, Claude Code still found this bug. The skill changed how the review was done and what it reported:

- It pinned the review to exact commits and read code from them (`git show <sha>:path`), not from whatever was checked out.
- Each finding came in the skill's format: severity, whether this PR introduced it, the trigger, the impact and a fix direction. A closing section lists what it reviewed and what it couldn't check.
- It left out nits. The other session's extra findings were real but minor, and the skill's rules say to omit them.
- Its fix matched the maintainers' fix, including rejecting RSV1 on control frames, which RFC 7692 §6.1 requires.

The session without the skill did one thing better: it wrote a small model of the frame-header logic and checked every valid sequence of up to five frames. That is stronger evidence than a hand trace.

## Limits

- One run each. This is an example, not a benchmark, and a second run of either session could come out differently. Measuring how often the skill catches bugs, and how often it raises false alarms, needs many PRs and repeated runs.
- The sessions ran as Claude Code subagents, not through `/plugin install`. The skill was listed the way Claude Code lists an installed skill, but that listing was written for this test.
- Both sessions were told not to run Python, so both findings come from reading and tracing the code. Both reviews say so.
- Both sessions were told to use only `git`, `ls` and `rg`. Both also used `cat`, and the session without the skill also used `sed` and `awk`. Everything they ran was read-only.
