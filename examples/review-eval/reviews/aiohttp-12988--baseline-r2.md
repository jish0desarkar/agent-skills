# aiohttp-12988: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #12988 by reading the diff. I couldn't run anything: `multidict` isn't installed here, so neither the PR's test nor my own check ran. I also couldn't confirm the fix works with the Cython build.

The PR stops a control frame (ping, pong or close) from overwriting `_frame_fin` in `aiohttp/_websocket/reader_py.py:416`. That fixes the case it targets. Before the change, a ping between the fragments of a compressed message set `_frame_fin` to true. The next continuation frame then re-read `_compressed` from its own RSV1 bit, which is 0, so the message was never decompressed. The new test reproduces that case and the logic looks right for it.

**Likely regression: a ping or other control frame before the first data frame**
- **Initial state:** `_frame_fin` starts as `False` and `_compressed` as `COMPRESSED_NOT_SET`.
- **Control frame arrives first:** the header check at `reader_py.py:405` then sets `_compressed = COMPRESSED_FALSE`, because the control frame has RSV1 = 0. With the PR, `_frame_fin` stays `False`.
- **First compressed message:** the next frame (RSV1 = 1, FIN = 1) takes the `elif rsv1` branch. That branch raises `WebSocketError("Received frame with non-zero reserved bits")`.
- **Before the PR:** the first ping set `_frame_fin = True`, so this sequence worked.
- **Impact:** a peer that pings or closes before its first compressed message, which is common with keepalive pings, would hit a protocol error on a connection that worked before.
- **Fix:** don't let control frames touch `_compressed` at all. Only run the compression-state block when `opcode <= 0x7`. For control frames, either reject RSV1 or ignore it.

**Smaller points**
- **Missing test:** there's no test for the control-frame-first case above, nor for a ping between uncompressed fragments.
- **Cython:** `reader_c.py` and `reader_c.pxd` are also in the tree. Please check that `reader_c.py` picks up the same change, and run the new test with the Cython extensions built, as AGENTS.md requires for parser changes.
- **Changelog:** the changelog line "Fixed control frames breaking fragmented WebSocket messages" is vague. Naming permessage-deflate would help.
- **Other files:** the CONTRIBUTORS entry looks fine.

I left `master` checked out and created a local `pr-12988` branch. I posted nothing to the PR.

Findings submitted with the ReportFindings tool:
