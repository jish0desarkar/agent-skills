# fastapi-15030: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] `response_class=EventSourceResponse` on a non-generator endpoint now crashes at request time
`fastapi/routing.py:371` and `:491` (introduced in this PR)

Trigger: `@app.get("/x", response_class=EventSourceResponse)` on an endpoint that is a plain `def` or `async def` and returns a value rather than yielding.

- `APIRoute` correctly computes `is_sse_stream = is_generator and ...` (`:926`), and that value is what OpenAPI uses.
- The request handler recomputes `is_sse_stream` from the response class alone (`:371`). It doesn't use the route's `is_sse_stream`, and `get_request_handler` doesn't accept one. `is_json_stream` is passed in; the SSE flag is not.
- So the SSE branch runs for any endpoint using this class, and it treats `dependant.call(...)` as a generator.
- For `async def`, `dependant.call(...)` returns an un-awaited coroutine, so the request fails with an `AttributeError` or `TypeError` and a "coroutine never awaited" warning.
- For `def`, it returns a plain value, and `iterate_in_threadpool` fails when it tries to iterate it.

Impact: this is a 500 on a misconfigured route. The route is silently accepted at startup, and its OpenAPI is emitted without the SSE content type.

Fix direction: pass `is_sse_stream=self.is_sse_stream` into `get_request_handler`, as is done for `is_json_stream`. Alternatively, fail at route creation when `EventSourceResponse` is used on a non-generator.

### [Medium] `splitlines()` in `format_sse_event` splits on characters that aren't SSE line terminators
`fastapi/sse.py`, `format_sse_event` (`data_str.splitlines()`, `comment.splitlines()`), new in this PR

Trigger: an event whose JSON payload contains U+2028, U+2029, U+0085, `\x0b`, `\x0c` or `\x1c`–`\x1e`. For example, a Pydantic model or `ServerSentEvent(data=model)` with the string `"a\u2028b"`.

- The `stream_item_field.serialize_json` and `model_dump_json` paths keep these characters raw in the output.
- The `jsonable_encoder` + `json.dumps` path escapes them, so it is unaffected.
- `str.splitlines()` splits on all of these characters, but the SSE spec only treats `\n`, `\r` and `\r\n` as line terminators.
- The payload is emitted as two `data:` lines. The client rejoins them with `\n`, which puts a raw newline inside a JSON string.

Impact: `JSON.parse(event.data)` throws on the client, or `raw_data` text is silently altered. It depends on the data, so it shows up in production but not in tests. The same call also drops a trailing newline in `raw_data`. An empty `raw_data=""` emits no `data:` line at all, so the client never dispatches the event.

Fix direction: split only on `\r\n`, `\r` and `\n` (for example `re.split(r"\r\n|\r|\n", s)`), and decide explicitly how to handle empty and trailing-newline data.

### [Medium] `event`, `id` and `comment` are not checked for line breaks, so a field can inject extra SSE fields
`fastapi/sse.py`, `ServerSentEvent.id` and `event` validators, and `format_sse_event`

Trigger: `ServerSentEvent(event=user_supplied, ...)`, or `id=...` containing `\n` or `\r`. For example, `"x\ndata: injected"`.

- Only `id` is checked, and only for `\0`. `event` isn't checked at all, and neither field is checked for CR or LF.
- Both values are written as `f"event: {event}"` and `f"id: {id}"` with no escaping.
- `comment` is handled by splitting into lines, but that uses the `splitlines()` set from the finding above.

Impact: if the event name or ID derives from request data, a client can forge `data:` or `id:` fields in the stream. The PR already validates `id` for `\0`, so the intent is to protect these fields.

Fix direction: reject or strip `\r` and `\n` in `event` and `id` with a validator, as is done for `\0`.

### [Low, unverified] The keepalive generator yields inside an `anyio` task group
`fastapi/routing.py:~520`, `_async_stream_sse`

Concern: the async generator yields from inside `anyio.create_task_group()`. If Starlette's disconnect handling cancels the response task and the generator is finalized later (garbage-collected or `aclose` from another task), anyio can raise "exit cancel scope in a different task". Also, a generator or serialization error inside `_producer` surfaces as an `ExceptionGroup` rather than the original exception, which affects exception handlers and logging. I did not run this, so treat it as a risk to test (client disconnect mid-stream and a raising generator), not a confirmed defect.

---
**Scope reviewed:** PR #15030, head `2269bb4`, base `48d58ae` (master). I did not recheck the live head after fetching it. I read the full diff for `fastapi/` (`sse.py`, `routing.py`, `openapi/utils.py`, `responses.py`) and `pyproject.toml`, and used `REVIEW_INDEX.md` for the streaming and OpenAPI rows. The PR has no comments.

**Not done:** I did not run tests, lint or mypy, and did not inspect CI. I did not read the docs, the `docs_src` examples, `tests/test_sse.py`, the tutorial tests or the `.agents` SKILL.md in detail. I read them only as file names in the diffstat. I also haven't checked whether the tests cover the findings above.

**Minor observation:** the OpenAPI output uses `itemSchema` (an OpenAPI 3.2 feature) while `openapi_version` still defaults to `3.1.0`. `MediaType` allows extra fields, so it validates, but strict 3.1 consumers may ignore the field.
