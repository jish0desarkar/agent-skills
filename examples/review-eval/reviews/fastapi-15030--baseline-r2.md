# fastapi-15030: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #15030 ("✨ Add support for Server Sent Events") by reading the diff. I couldn't run any of it because the sandbox has no network and no installed dependencies. The built-in `/code-review` run reviewed only your local `README.md` edit, not the PR, so I fetched `pull/15030/head` from the local mirror and read the diff myself. I did not read the tests or docs. My checkout is back on `master`.

**Findings, most important first**

1. **Header injection through `event` and `id`** (`fastapi/sse.py`, `format_sse_event`)
   - `event` and `id` are written straight into `f"event: {event}"` and `f"id: {id}"`.
   - `id` is validated only for `\0`, and `event` isn't validated at all.
   - A value containing `\n` or `\r`, such as `event="x\ndata: injected"`, adds extra fields to the stream.
   - This matters whenever either value comes from user input.
   - Fix: reject or strip `\r` and `\n` in both fields, the same way the `\0` check works. Also check `retry`/`comment` handling.

2. **Producer errors may arrive wrapped in an `ExceptionGroup`** (`fastapi/routing.py`, `_async_stream_sse`)
   - The generator runs in a `_producer` task inside `anyio.create_task_group()`.
   - If it raises, for example `ResponseValidationError` from `_serialize_data` or a user exception, anyio can re-raise it from the task group as an `ExceptionGroup`. Exception handlers matching the original type would then miss it.
   - The JSONL path raises the original exception directly, so the two paths would behave differently.
   - I'd like to see a test where an SSE item fails validation and an exception handler catches it.
   - I couldn't run this, so it's unconfirmed.

3. **Empty or newline-only payloads can be dropped** (`format_sse_event`)
   - `data_str.splitlines()` yields no lines for `""`, so `raw_data=""` sends an event with no `data:` field. Browsers don't dispatch such an event.
   - A trailing newline in `raw_data` is lost too: `"a\n"` becomes one line.
   - The fix is to emit `data:` when `data_str` is empty, and to use `split("\n")` after normalizing line endings.
   - `splitlines()` also splits on characters like `\x0b`, `\x0c`, `\x1c` and `\u2028`, which the SSE spec doesn't treat as line breaks.

4. **`ServerSentEvent.data` ignores the `response_model_*` options** (`routing.py`, `_serialize_sse_item`)
   - It uses `model_dump_json()` or `json.dumps(jsonable_encoder(...))`, so `by_alias`, `exclude_none` and the other options aren't applied.
   - The code comments say skipping `stream_item_field` validation for these items is intentional. The serialization options are skipped too, which may surprise people.
   - You can't send JSON `null` as data, because `data=None` means "no data".

5. **Minor points**
   - `-> AsyncIterable[Model | ServerSentEvent]` (a union) is not excluded from `stream_item_type`. The OpenAPI schema would then describe `ServerSentEvent` as a data model.
   - A buffer of 1 means the generator runs one item ahead of the client.
   - Yielding inside a task group within an async generator can raise anyio's "cancel scope in a different task" error if the stream is finalized from another task. I didn't confirm it here, but a client-disconnect test would show it.

The rest looked sound: the keepalive timer is decoupled from generator iteration, the `Cache-Control` and `X-Accel-Buffering` headers are set, and the OpenAPI `itemSchema` follows the 3.2 spec.

Separately, your uncommitted `README.md` change is a personal note ("local note: re-check the release checklist before tagging"). You probably don't want that committed.

Findings submitted with the ReportFindings tool:
