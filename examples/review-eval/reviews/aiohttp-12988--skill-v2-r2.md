# aiohttp-12988: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

I found one regression in PR #12988, and I confirmed it by reading the code. I couldn't run it, because the sandbox has no `multidict` or `yarl`.

### [High] A control frame before the first data message now breaks the next compressed message
`aiohttp/_websocket/reader_py.py:408-420` (introduced in this PR)

**Trigger:** a permessage-deflate connection where a ping, pong or close frame arrives before any data frame, for example a heartbeat sent right after the handshake. Then a compressed message (RSV1 set) arrives. Both sides' state starts as `_frame_fin = False` and `_compressed = COMPRESSED_NOT_SET`.

**Trace at the head commit:**
1. The ping header reaches the compression latch at line 408. `_compressed` is `NOT_SET`, so it latches `COMPRESSED_FALSE` from the ping's RSV1 of 0.
2. The new `if opcode <= 0x7` guard skips the update, so `_frame_fin` stays `False`. Before this PR, the ping set it to `True`.
3. The compressed BINARY frame arrives. `self._frame_fin or self._compressed == NOT_SET` is now false, because `_frame_fin` is `False` and `_compressed` is `FALSE`. The latch is skipped.
4. `elif rsv1` then raises `WebSocketError(PROTOCOL_ERROR, "Received frame with non-zero reserved bits")`, and the connection closes.

**Before the PR:** step 2 set `_frame_fin = True`, so the next data frame re-latched `_compressed` correctly. This works today.

**Impact:** a ping or pong ahead of the first message on a compression-enabled connection now kills it. Hand-written clients and servers that send early keepalives are affected.

**Root cause:** the compression latch at lines 408-409 still runs for control frames, but the "new message" signal it relies on is now only updated by data frames. A control frame shouldn't touch `_compressed` at all, and it should be validated separately, since RFC 6455 requires RSV1 to be 0 on control frames.

**Fix direction:** run the latch only when `opcode <= 0x7`. For control frames, raise on RSV1 set and leave `_compressed` alone. A test should send a ping first and then a compressed message. The new test only covers a ping in the middle of a message.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `_frame_fin` is now updated only by data frames | changes meaning; state across calls | The only reader is the latch at line 408. `_handle_frame` at line 516 also gets `_frame_fin`, but control branches ignore `fin` apart from an error message in the close branch. | Finding above. Mid-message ping works; ping before the first message regresses. |
| The `.pxd` Cython twin | sync twin | `reader_c.pxd` only declares `_frame_fin`; it is compiled from `reader_py.py`, so there is no separate logic | No extra change needed |
| Mid-message ping with RSV1 = 0 | attack | `_compressed` is already set and `_frame_fin` is `False`, so it falls through correctly. A ping with RSV1 = 1 raises, which is correct. | OK |
| Ping after a completed message | attack | `_frame_fin` stays `True`, so the next data frame re-latches | OK |

**Reviewed:** head `7972054f2b7c`, base (merge base) `b48737e74f2a`.

**Not checked:**
- I did not run any tests, and I did not run the Cython build.
- I did not see CI results.
- The failing path above comes from reading the code, not from a run.

The new test, changelog and `CONTRIBUTORS.txt` entry look fine.
