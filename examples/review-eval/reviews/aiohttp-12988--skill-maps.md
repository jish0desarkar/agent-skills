# aiohttp-12988: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

### [High] A ping/pong before the first data frame breaks the first compressed message
`aiohttp/_websocket/reader_py.py:408` and `:418-420` (introduced in this PR)

**Trigger:** permessage-deflate is negotiated, and a control frame arrives before any data frame. A keepalive ping from the server right after the handshake is a common case. The first data frame then arrives with RSV1 set.

**Trace (static):**
- `_frame_fin` starts as `False` (`reader_py.py:158`), and `_compressed` starts as `COMPRESSED_NOT_SET`.
- The ping reaches the latch at line 408 and sets `_compressed = COMPRESSED_FALSE`, because the ping has RSV1 = 0.
- With this PR, line 420 is skipped for the ping, so `_frame_fin` stays `False`. Before the PR, the ping set it to `True`.
- The first compressed TEXT or BINARY frame then evaluates `_frame_fin or _compressed == NOT_SET` as false. It falls into `elif rsv1:` and raises `WebSocketError(PROTOCOL_ERROR, "Received frame with non-zero reserved bits")`.

**Impact:** the connection is closed with a protocol error on a valid stream. This is a regression, and the base commit handles that sequence correctly.

**Fix direction:** don't use "a control frame was seen" as the signal that a message boundary was crossed. Either:
- Skip the line 408 latch for control frames, so they never touch `_compressed`.
- Track "inside a fragmented message" separately, for example from `self._opcode != OP_CODE_NOT_SET`, and use that instead of `_frame_fin`.

Add a regression test that feeds a ping, then a compressed single-frame message.

### [Low] `fin` passed to `_handle_frame` is stale for interleaved control frames
`reader_py.py:515-516` (introduced in this PR)

`self._frame_fin` now holds the previous data fragment's FIN for any control frame. The only observable effect is the `{fin}` value in the "Invalid close frame" error text at line 316, which can print `False` for a close frame. Pass the real `fin` for control frames, or track the fragmentation state separately as above.

### Non-code notes
- The new test starts with a data fragment, so it never covers the ping-first sequence above.
- The PR checklist leaves the documentation box unticked. That seems fine for a bug fix.
- `CHANGES/12988.bugfix.rst` and the `CONTRIBUTORS.txt` entry are in place.
- The compiled reader shares this source, so the same logic applies there.

**Scope and limits:**
- I reviewed head `7972054f` against base `b48737e`, using the PR's 4 changed files, the diff and the surrounding reader code.
- There were no PR comments, and I did not inspect CI.
- The repro and the test suite were not run, because dependencies such as `multidict` aren't installed in the sandbox. Finding 1 rests on source tracing only.
- I did not run the Cython build.
- `REVIEW_INDEX.md` exists only in the working tree, not in the PR head, so I didn't use it.
