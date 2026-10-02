# Review by the session with `verified-code-review`

The session's final message, unedited except that the scratch directory prefix was removed from file paths. Back to the [example](README.md).

---

**Verdict: request changes.** The patch fixes the case it targets (RSV1 data fragment, then PING, then continuation). It also adds a regression on a more ordinary path. A control frame that arrives before the first data frame leaves the compression flag stuck at "uncompressed". The next compressed message is then rejected.

### [High] A leading ping/pong/close breaks the first compressed message on a permessage-deflate connection
`aiohttp/_websocket/reader_py.py:419-420` (introduced in this PR). It interacts with the unchanged init at line 158 and the latch at lines 408-414.

**Trigger:**
- Compression is negotiated. The aiohttp server defaults to `compress=True`, and any client that offers permessage-deflate triggers it: browsers, `websockets`, or an aiohttp client with `compress=15`.
- The first frame the reader sees is PING, PONG or CLOSE, and a data frame with RSV1 set follows.
- Ordinary keep-alive traffic does this. Examples are a server `heartbeat=` PING answered by the browser's PONG before the page's first message, or a client keep-alive ping before its first send.

**Trace** (by hand, not executed):

| frame | `_frame_fin` / `_compressed` before | result |
|---|---|---|
| PING, FIN=1, RSV1=0 | False / NOT_SET | The latch runs only because `_compressed == COMPRESSED_NOT_SET`, so `_compressed` becomes FALSE. The new guard skips the `_frame_fin` update, so it stays False. |
| TEXT or BINARY, RSV1=1 | False / FALSE | `_frame_fin or NOT_SET` is false, so the `elif rsv1` branch runs and raises `WebSocketError(PROTOCOL_ERROR, "Received frame with non-zero reserved bits")`. |

On master the same input works, because the PING sets `_frame_fin = True` and the data frame re-latches.

**Impact:**
- The first compressed message is lost and the connection is torn down. `feed_data` returns `(True, b"")`, and `WebSocketResponse.receive()` closes with 1002 and returns an ERROR message.
- This needs no unusual peer behaviour, unlike the interleaving bug the PR fixes.

**Why the tests miss it:**
- The new test only covers data, then PING, then continuation.
- No parser test starts with a control frame before an RSV1 frame.
- The ping/pong functional tests use the client default `compress=0`, so no RSV1 is ever sent.
- `test_send_recv_compress*` negotiate compression but have no leading control frame.

**Fix direction:**
- Either stop control frames writing the latch: put the latch and the `_frame_fin` update under `if opcode <= 0x7:`, and optionally reject RSV1 on control frames per RFC 7692 §6.1.
- Or initialise `_frame_fin = True` ("no data message in flight") in `__init__`.
- I hand-checked both against the PR's sequence and the leading-PING sequence.

A regression test would be (untested; I expect it to fail on this branch):
```python
def test_compressed_message_after_leading_ping(out, parser):
    parser.feed_data(PACK_LEN1(0x80 | WSMsgType.PING, 0))
    parser.feed_data(build_frame(b"hello", WSMsgType.TEXT, ZLibBackend=ZLibBackend))
    assert out._buffer[1] == WSMessageText(data="hello", size=5, extra="")
```

**Same root cause, minor:** `_frame_fin` no longer describes the current frame for control frames, but lines 515-517 still pass it to `_handle_frame` as `fin`. Only the `Invalid close frame: {fin} ...` message reads it, so it can now print `False` for a CLOSE frame. This is cosmetic.

### Checked and fine
- The targeted interleaving case now keeps `_compressed` TRUE across the PING. The new test at `tests/test_websocket_parser.py:609-634` fails on master and passes on the branch, by trace.
- `reader_c.py` is a symlink to `reader_py.py`, so the Cython build shares this logic. The `.pxd` types don't change it.
- The changelog fragment and the CONTRIBUTORS entry follow the AGENTS.md conventions.

### Scope and limits
- I reviewed `keep-ws-compression-state` at `7972054f2b7ccb28b158a9c98f7213bba8c43f0f` against `master` at `b48737e74f2a18d0345d2894566be02c5da47f6b`. That master commit is also the merge-base. The range is 6 commits including a clean merge of master, touching 4 files (+35/−1).
- I read from git objects and made no edits; the checkout is still clean.
- I traced the full reader, `_handle_frame`, the Cython `.pxd`, the writer's RSV1 behaviour, client and server compression negotiation, heartbeat handling, and the existing websocket tests.
- I ran no tests (no Python here, and a review doesn't authorise it) and did not build Cython. Findings come from static tracing.
- With no network, I could not see PR comments, CI logs or the live PR head, so the review may be stale against the live PR.
