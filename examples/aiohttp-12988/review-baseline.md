# Review by the session without the skill

The session's final message, unedited except that the scratch directory prefix was removed from file paths and a contributor's name, email and handle were redacted. Back to the [example](README.md).

---

**Verdict: request changes.** The patch fixes the case in the description, but it breaks a more common one. A compressed message that arrives after a leading ping, pong or close is now rejected as a protocol error, and the new test doesn't cover that order.

I couldn't run pytest here (no Python), so this comes from tracing the code and from an awk model of the header logic. I didn't modify any files.

## Blocking: control frames still consume the "first fragment" sentinel

In `aiohttp/_websocket/reader_py.py`, `_frame_fin` starts `False` (line 158) and `_compressed` starts `COMPRESSED_NOT_SET` (line 168). The latch block at 408-414 still runs for control frames. On master, every frame left `_frame_fin = True` afterwards, so the next data frame could latch. Now a control frame doesn't, so on a fresh connection with permessage-deflate negotiated:

1. PING (FIN=1, RSV1=0): `_compressed` is NOT_SET, so it latches to FALSE and `_frame_fin` stays False.
2. Compressed TEXT or BINARY (RSV1=1): `_frame_fin` is False and `_compressed` is already set, so it hits `elif rsv1` and raises `WebSocketError(PROTOCOL_ERROR, "Received frame with non-zero reserved bits")`, close code 1002.

| Frames (fin/rsv1) | master | this branch |
|---|---|---|
| BINARY 0/1, PING, CONT 1/0 | continuation left compressed (the bug) | ok |
| PING, TEXT 1/1 | ok | protocol error |
| PONG, BINARY 0/1, CONT 1/0 | ok | protocol error |

This is ordinary traffic. aiohttp's writer sends control frames uncompressed and data frames with RSV1 (`writer.py:80-82, 215, 249`), and `WebSocketResponse` defaults to `compress=True` (`web_ws.py:108`). A heartbeat-enabled server whose browser answers the first PING with a PONG before sending anything would drop that client on its first message. The error text is misleading because the frame is legitimately compressed.

**Model results.** Over all 59,699 valid frame sequences of up to 5 frames:
- Master mis-decodes 3,192 (the original bug).
- This branch mis-decodes none but rejects 10,944. Every one of them is control frame(s) followed by a compressed first data frame.

**Smallest fix:** set `self._frame_fin = True` in `__init__` (line 158), so connection start counts as a message boundary. The model shows 0 failures with it, and the PR's own test still passes. The alternative is to keep control frames out of the latch block entirely while keeping the mid-message RSV1 rejection, which also gave 0 failures.

**Test gap:** add the missing order. By my trace it fails on this branch (`feed_data` returns `(True, b"")`) and passes with the fix, but I couldn't run it.
```python
@pytest.mark.usefixtures("parametrize_zlib_backend")
def test_compressed_message_after_leading_ping(
    out: WebSocketDataQueue, parser: PatchableWebSocketReader
) -> None:
    assert parser.feed_data(build_frame(b"", WSMsgType.PING)) == (False, b"")
    data = build_frame(b"binary", WSMsgType.BINARY, ZLibBackend=ZLibBackend)
    assert parser.feed_data(data) == (False, b"")
    assert out._buffer[0] == WSMessagePing(data=b"", size=0, extra="")
    assert out._buffer[1] == WSMessageBinary(data=b"binary", size=6, extra="")
```

## Minor

- **Stale FIN for control frames:** `_handle_frame(self._frame_fin, ...)` (line 515-517) now passes the last data frame's FIN for control frames. It only feeds the `Invalid close frame: {fin} ...` message (line 316), so it's harmless, but control frames aren't fully transparent.
- **New test:** it lacks `parametrize_zlib_backend`, which `test_compressed_msg_too_large` uses. It also ignores the return of `feed_data`, so a protocol error shows up as an `IndexError` on `out._buffer[...]`.
- **`CONTRIBUTORS.txt`:** this PR adds "[name]", but the same author ([email], `[handle]`) was already added as "[another name]" by #13042 (b48737e7), on the next line. It looks like a duplicate.
- **Changelog:** "control frames breaking fragmented WebSocket messages" overstates it. Uncompressed fragments with interleaved controls already worked (`test_continuation_with_ping`), so only permessage-deflate messages were affected. I can't tell offline whether 12988 is this PR's number; if it's the issue number, AGENTS.md wants a PR-numbered symlink.
- **Cython testing:** AGENTS.md wants websocket changes tested with the Cython extensions. `reader_c.py` is a symlink to `reader_py.py`, so it's the same source, but a run is still worth doing after the fix.

## What checks out

- **Guard:** `opcode <= 0x7` is exactly the data frames, because invalid opcodes are rejected earlier (lines 375-386).
- **Added test:** it fails on master and passes here by my trace, and every name it uses is imported.
- **`CONTRIBUTORS.txt` ordering:** the new line is alphabetical.
