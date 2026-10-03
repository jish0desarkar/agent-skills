# aiohttp-12988: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] A control frame before the first data frame breaks the next compressed message
`aiohttp/_websocket/reader_py.py:406-420` (introduced in this PR)

Trigger: a connection with `compress=True` and a fresh reader, where a ping, pong or close frame arrives before any data frame. Browsers and proxies can send an unsolicited ping or pong early.

The head code behaves like this:
1. `_frame_fin` starts as `False` (line 158) and `_compressed` starts as `COMPRESSED_NOT_SET`.
2. The control frame passes the latch check at line 408 because `_compressed` is `NOT_SET`. That sets `_compressed = COMPRESSED_FALSE` from the control frame's RSV1 bit.
3. The new `if opcode <= 0x7` guard skips the update, so `_frame_fin` stays `False`. Before the PR, the control frame's FIN bit set it to `True`.
4. The first compressed data frame (RSV1=1, FIN=1) then reaches line 408 with `_frame_fin == False` and `_compressed == FALSE`. Both conditions fail, so it falls into `elif rsv1` and raises "Received frame with non-zero reserved bits".

Impact: a valid compressed message is rejected with a protocol error, and the connection closes. On the base commit this sequence worked, so it is a regression. It also applies to any control frame that arrives while `_frame_fin` is still `False` and `_compressed` is `NOT_SET`.

Fix direction: don't let control frames take part in the compression latch. For example, wrap lines 408-413 in the same `opcode <= 0x7` condition, so control frames neither set `_compressed` nor touch `_frame_fin`. The alternative is to initialise `_frame_fin = True` as "no message in progress". Add a test that sends a ping first and then a compressed message.

I could not run this. The checkout is at the base commit, and the sandbox has no `multidict`, so an export of the head would not import. The finding comes from tracing the code.

### Trace log

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| `_frame_fin` is only updated for data frames | changes meaning; state across calls; adds a branch beside siblings | the only readers are line 408 and the `_handle_frame` call at line 516. `reader_c.py` is a symlink to `reader_py.py`, and `reader_c.pxd` declares the same field. | finding 1 |
| `_handle_frame` now gets a stale `fin` for control frames | changes meaning | the ping, pong and close branches ignore `fin`, except in the invalid-close error text, which only prints it | no functional change |
| A control frame arrives mid-message (the PR's target case) | state across calls | `_frame_fin` is `False`, so `_compressed` is kept. A control frame with RSV1 set still raises, which is correct. | fixed as intended |
| A control frame arrives while `_frame_fin` is `True` | state across calls | `_compressed` is set from the control frame's RSV1, but the next data frame relatches it | OK (this was already the case) |
| New test | n/a | covers only the ping-mid-message case, not control-first or close or pong variants | gap behind finding 1 |

The Python reader is the only implementation of this code: `reader_c.py` is a symlink to it, so the Cython build gets the same change.

Base commit: `b48737e74f2a18d0345d2894566be02c5da47f6b`. Head commit: `7972054f2b7ccb28b158a9c98f7213bba8c43f0f`. The merge base is the same as the base.

I did not run the project tests or the Cython build. I did not run `changed_symbols.py` because I couldn't find it on this machine, so I used `git diff` and `git grep` instead. I did not see CI results.
