# aiohttp-12988: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

### [High] A control frame before the first data frame breaks compression latching
`aiohttp/_websocket/reader_py.py:417-420` (introduced in this PR)

**Trigger:**
- The connection has `compress=True`.
- The peer sends a ping, pong or close with RSV1=0 before any data frame. A ping right after the handshake (a keepalive) is the common case.
- The peer then sends a compressed message (RSV1=1) as its first data frame.

**Trace at the PR head:**
- `_frame_fin` is initialised to `False` (`reader_py.py:158`) and `_compressed` to `COMPRESSED_NOT_SET` (`:168`).
- On the ping header, the check at `:408` is true because `_compressed` is `NOT_SET`. So `_compressed` becomes `COMPRESSED_FALSE`.
- The new `if opcode <= 0x7` guard skips the ping, so `_frame_fin` stays `False`. On base it was set to `True` here.
- On the compressed data frame, `_frame_fin` is `False` and `_compressed` is no longer `NOT_SET`. The condition at `:408` is false, and the `elif rsv1` branch raises `PROTOCOL_ERROR` ("Received frame with non-zero reserved bits").

**Impact:**
- The connection is closed on a valid sequence that works on base.
- This is a regression on a path more common than the bug being fixed.

**Fix direction:**
- Don't let control frames latch `_compressed`. Run the latch only for `opcode <= 0x7`, or start `_frame_fin` as `True`.
- Add a test with a ping first, then a compressed message.
- `reader_c.pxd` only declares the fields, so the same logic applies to the Cython build.

I found no other defects:
- Control frames don't read `fin` in `_handle_frame`. The stale `_frame_fin` is harmless there.
- An interleaved ping with RSV1=1 still hits the `elif rsv1` error, which is correct.

### [Low] Test and docs gaps
`tests/test_websocket_parser.py` covers only a ping mid-message. It has no case for a control frame as the first frame, which would have caught the High finding. The PR checklist also leaves docs unticked, which is fine for an internal fix. The changelog and `CONTRIBUTORS.txt` entries look fine.

**Scope:**
- I reviewed `b48737e...7972054` (head SHA verified against PR metadata) by reading source. There were no PR comments.
- I did not run the tests or the Cython build. The sandbox has no `multidict`, so my reproduction script failed to import. The High finding comes from source tracing only.
- I did not check CI results.
- I did not recheck that the PR head is still current.
