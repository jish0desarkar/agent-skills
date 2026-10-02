# Answer key for aio-libs/aiohttp#12988 (written before reading either review)

Ground truth: aio-libs/aiohttp#13274 (reported 2026-07-27 against 3.14.2), fixed by
aio-libs/aiohttp#13302 (merged 2026-08-02, a47a63e0).

## The regression (must find)

`aiohttp/_websocket/reader_py.py` at PR head 7972054:

- `__init__` sets `self._frame_fin = False` and `self._compressed = COMPRESSED_NOT_SET` (L158, L168).
- L408: `if self._frame_fin or self._compressed == COMPRESSED_NOT_SET:` latches
  `_compressed` from RSV1 for every frame, control frames included.
- L419 (the PR's change): only data frames update `_frame_fin`.

Trigger: the first frame on a connection is a control frame (e.g. a PONG answering the
server's heartbeat PING, or a client PING). It latches `_compressed = COMPRESSED_FALSE`, but
`_frame_fin` stays False. The next frame starts a compressed message with RSV1=1, so
L408 is false and L410 raises "Received frame with non-zero reserved bits" -> close 1002.
Before the PR the control frame set `_frame_fin = True`, so the next data frame re-latched
correctly. Introduced by this PR. Affects both client and server readers (reader_c is
compiled from the same file).

Scoring:
- CAUGHT: says control frames still go through the compression latch while `_frame_fin`
  is not advanced, and connects it to a concrete failure for the next compressed message
  (first-frame control frame, or equivalent state).
- PARTIAL: notes control frames still mutate `_compressed` / the latch should be data-only,
  without a concrete failure or with the wrong consequence.
- MISSED: neither.

## Related, also changed by the fix (not a regression)

- Control frames with RSV1 set are not rejected (RFC 7692 §6.1). Pre-existing; the fix
  added a check. Credit as a valid pre-existing observation, not as the regression.

## Classifying other findings

- Valid: real behavior at this revision, correctly labelled introduced vs pre-existing.
- False positive: claim contradicted by the code, or "bug" that is not reachable.
- Noise: style, docs, test-only nits presented as defects.

---

Unedited from the version written before the reviews were read. Back to the [example](README.md).
