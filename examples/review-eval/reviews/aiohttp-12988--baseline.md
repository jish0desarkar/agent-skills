# aiohttp-12988: stock Claude Code (built-in code-review)

The session's final review, unedited except that scratch paths were removed.

---

I couldn't run anything: the sandbox has no Python dependencies (`multidict` is missing) and no network. What follows comes from reading the code.

**Review of PR #12988** (keep websocket compression state across interleaved control frames)

**Bug: a ping before the first compressed message now closes the connection (`aiohttp/_websocket/reader_py.py`, around lines 405–420).**

The PR stops control frames from updating `_frame_fin`. The compression-state block just above it still runs for every frame, including control frames:

```python
if self._frame_fin or self._compressed == COMPRESSED_NOT_SET:
    self._compressed = COMPRESSED_TRUE if rsv1 else COMPRESSED_FALSE
elif rsv1:
    raise WebSocketError(... "non-zero reserved bits")
```

Trace with permessage-deflate negotiated:
1. At the start, `_frame_fin` is `False` and `_compressed` is `NOT_SET`.
2. The peer sends a ping (`fin=1`, `rsv1=0`) before any data. This is common, for example a server keepalive.
3. The condition is true because `_compressed` is `NOT_SET`, so `_compressed` becomes `COMPRESSED_FALSE`.
4. Before the PR, `_frame_fin` then became `True`. After the PR it stays `False`.
5. The first compressed text or binary frame (`rsv1=1`) arrives. Now `_frame_fin` is `False` and `_compressed` is `FALSE`, so it hits `elif rsv1` and raises `PROTOCOL_ERROR`.

On master this sequence works. The PR's test doesn't catch it, because it only covers a ping in the middle of a message.

**Suggested fix:** don't let control frames touch `_compressed` at all. Wrap that block in `if opcode <= 0x7:` and set `_frame_fin` inside the same guard. Add a regression test that sends a ping as the very first frame and then a compressed message.

**Minor:**
- `_handle_frame` is still passed `self._frame_fin` for control frames. That is harmless for ping and pong. For close, the error text `Invalid close frame: {fin}...` will now show a stale `fin` value.
- The changelog entry is vague. Something like "Fixed compressed fragmented WebSocket messages failing to decompress when a control frame is interleaved" would say more.
- `reader_c.py` is a symlink to `reader_py.py`, so the Cython build gets the same change. Per AGENTS.md, test with the extensions built before merging.

The review skill initially reported the PR as unavailable. It hadn't tried the local mirror, and `git fetch origin pull/12988/head` worked. I left no changes in the repo apart from a local `pr-12988` branch, and I'm back on `master`.

Findings submitted with the ReportFindings tool:
