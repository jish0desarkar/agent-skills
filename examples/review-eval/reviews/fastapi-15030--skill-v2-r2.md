# fastapi-15030: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] A non-generator endpoint with `EventSourceResponse` crashes at request time
`fastapi/routing.py:371` (introduced in this PR)

Trigger: `@app.get("/x", response_class=EventSourceResponse)` on a plain `def` or `async def` endpoint that returns a value.

- `APIRoute` computes `is_sse_stream = is_generator and ...` (`routing.py:926`), but never passes it to `get_request_handler`.
- The handler recomputes `is_sse_stream` from the response class alone (`routing.py:371`), with no generator check.
- Every request therefore takes the SSE branch. It calls `dependant.call(...)`, which for an `async def` returns a coroutine. The code then runs `iterate_in_threadpool(coro)`, or `.__aiter__()` on a plain value.
- The route's `is_sse_stream` is false, so the OpenAPI schema describes a normal response.

Impact: the request fails with an unhandled 500 (a `TypeError` from the SSE branch), and the docs disagree with the actual behavior.

Fix direction: pass the route's `is_sse_stream` into the handler, like `is_json_stream`. Alternatively, gate the SSE branch on `dependant.is_async_gen_callable or dependant.is_gen_callable`.

### [Medium] SSE field injection through `event`, `id` and `comment`
`fastapi/sse.py:195` (introduced in this PR)

Trigger: `ServerSentEvent(event=user_input)` or `ServerSentEvent(id=user_input)` where the value contains `\n` or `\r`. A value such as `"x\ndata: injected"` is one example.

- `format_sse_event` writes `f"event: {event}"` and `f"id: {id}"` unescaped. `comment` is split with `splitlines()`, so it is safe.
- `_check_id_no_null` only rejects `\0`, so newlines in `id` pass validation.

Impact: a caller can inject extra `data:` lines, fake events or a different `id` into the stream. This matters when the value comes from user input.

Fix direction: reject `\r` and `\n` in `event` and `id` in the model validator, as is already done for `\0`.

### [Low] `splitlines()` corrupts payloads containing U+2028, U+2029, U+0085 and similar characters
`fastapi/sse.py:200` (introduced in this PR)

Trigger: the data is serialized with `model_dump_json()` or `stream_item_field.serialize_json`, and a string field contains `\u2028`, `\u2029`, `\x85`, `\x0b`, `\x0c` or `\x1c`–`\x1e`. Pydantic does not escape these. `str.splitlines()` splits on all of them.

Impact: the single JSON payload becomes several `data:` lines. The client joins them with `\n`, which puts a raw newline inside a JSON string, so `JSON.parse` fails. SSE itself only treats `\r`, `\n` and `\r\n` as line breaks.

Fix direction: split on `\r\n`, `\r` or `\n` only, for example with `re.split(r"\r\n|\r|\n", s)`. Empty-string `raw_data` also yields no `data:` line, so the event is never dispatched in browsers. This is the same root cause.

### Trace log
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| New `is_sse_stream` flag, computed in the route and again in the handler | adds a branch beside siblings; adds a parameter | the route's flag is not passed to `get_request_handler`, which only takes `is_json_stream` | finding 1 |
| SSE branch compared with the JSONL and raw-stream branches | sibling comparison | headers are extended, `background` is passed, the `anyio.sleep(0)` is present. `status_code` is ignored, as in JSONL. | OK |
| `format_sse_event` and `ServerSentEvent` | iterates, indexes, splits or parses an input | newlines in `event` and `id`, empty strings, unusual separators | findings 2 and 3 |
| `stream_item_type` condition now also covers `EventSourceResponse` and excludes `ServerSentEvent` | changes what a function accepts | the existing JSONL path (`DefaultPlaceholder`) is unchanged | OK |
| Keepalive producer task group | state across calls | cancellation, client disconnect, timeout | no defect proven. Generator exceptions may surface as an `ExceptionGroup`, but only after the response has started, so I did not report it. |
| OpenAPI `itemSchema` branch | adds a branch beside siblings | mirrors the JSONL branch | OK |

Reviewed head `2269bb446a1233118812c9a4a62beb0aaf2054b0`, merge base `48d58ae3b6ef4ded5a4794618c00345667256d98`.

I did not run the tests or look at CI. I did not execute findings 1 and 3. Both follow from reading the code and from standard `str.splitlines` and Pydantic behavior.
