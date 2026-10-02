# fastapi-15030: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

### [Medium] A non-generator endpoint with `response_class=EventSourceResponse` crashes with a 500 instead of failing clearly
`fastapi/routing.py:371` and `:491` (introduced in this PR)

Trigger: a plain `def` or `async def` endpoint that has no `yield` declares `response_class=EventSourceResponse`. It might return a dict, or return a ready-made `EventSourceResponse(...)`.

Why it breaks:
- The route-level flag is correctly gated on the endpoint being a generator (`routing.py:926`).
- The handler ignores that flag. It recomputes `is_sse_stream` from the response class alone (line 371), and `get_request_handler` receives no `is_sse_stream` argument. The JSONL path, by contrast, gets `is_json_stream=self.is_json_stream` (line 951).
- So the handler still takes the SSE branch. There `dependant.is_async_gen_callable` is false, so it calls `iterate_in_threadpool(gen)` on the endpoint's return value.
- That value is a dict or a `Response`, not an iterator, so the call fails inside the streaming task or raises `TypeError`.

Impact: the client gets a 500 or a broken stream at request time. OpenAPI, which uses the route flag, documents the route differently from how it behaves.

Fix direction: pass `self.is_sse_stream` into `get_request_handler`, as is done for `is_json_stream`. Alternatively, fall through to normal response handling when the endpoint is not a generator.

### [Low] SSE framing uses `str.splitlines()`, which splits on characters the SSE spec does not treat as line breaks
`fastapi/sse.py`, in `format_sse_event`, where `data_str` and `comment` are split (introduced in this PR)

Trigger: the data string contains U+2028, U+2029, U+0085, `\x0b`, `\x0c` or `\x1c`–`\x1e`. Pydantic's `serialize_json` and `model_dump_json` leave U+2028, U+2029 and U+0085 unescaped. One example is a model field holding `"a\u2028b"`.

Impact: the string is split into two `data:` lines. The client joins them with `\n`, which puts a raw newline inside a JSON string literal, so `JSON.parse(event.data)` throws. The SSE spec only recognises `\r\n`, `\n` and `\r` as line terminators.

Related edge case: `raw_data=""` or `raw_data="a\n"` loses its empty or trailing line, so an empty `data` field is never emitted.

Fix direction: split with `re.split(r"\r\n|\r|\n", s)`.

### [Low] `event`, `id` and `comment` are not checked for line breaks
`fastapi/sse.py`, in `format_sse_event`, the `event:` and `id:` lines (introduced in this PR)

Trigger: `ServerSentEvent(event=user_value)` or `id=user_value` where the value contains `\n` or `\r`. Only `\0` is rejected for `id`.

Impact: the value is written unsanitised into an `f"event: {event}"` line. Anything after the newline becomes extra SSE fields, so the injected text can forge `data:` lines or other events. This matters when the value is derived from user input.

Fix direction: reject `\r` and `\n` in `event` and `id` with a validator. `comment` is already handled by `splitlines`.

### [Low] Errors raised while streaming are wrapped in an exception group, and the generator is not explicitly closed
`fastapi/routing.py`, in `_async_stream_sse` (introduced in this PR)

The producer runs in an anyio task group. If the user's generator raises, or `_serialize_sse_item` raises `ResponseValidationError`, anyio raises the error as an `ExceptionGroup`. The JSONL path propagates the bare exception. Any code or middleware matching on `ResponseValidationError` or the user's exception type will miss it.

Also, `sse_aiter` is never `aclose()`d. If the client disconnects while the producer is blocked in `send_stream.send`, the generator is left suspended at its `yield`. Its `finally` blocks then wait for garbage collection. I have not confirmed this one at runtime.

### Scope and checks
- Reviewed `2269bb4` against base `48d58ae` by reading the diff of `fastapi/routing.py`, `fastapi/sse.py`, `fastapi/openapi/utils.py` and `fastapi/responses.py`, and grepping the head revision for `is_sse_stream` and `is_json_stream`.
- I did not review the docs, the `docs_src` tutorial files, the `SKILL.md` file or the tests in any depth.
- I ran no tests and did not check CI. Nothing was posted to GitHub.
- The findings come from static tracing only. I did not run any reproduction.
