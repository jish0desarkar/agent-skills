# fastapi-15030: stock Claude Code, run 1

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #15030 (SSE support) by reading the diff. I couldn't run it because the sandbox has no Python environment with fastapi installed and no network. Nothing below has been executed. The first built-in review run returned "no issues" only because it never fetched the PR.

**Likely bugs**

1. **`fastapi/routing.py:371`, `:491`: a non-generator endpoint with `response_class=EventSourceResponse` will crash.**
   - `is_sse_stream` is computed inside `get_request_handler` from the response class alone.
   - The `APIRoute.is_sse_stream` attribute at line 926 does include `is_generator`, but it is never passed to the handler. `is_json_stream` is passed in at line 951.
   - A plain `async def` that returns a response object, or a sync function, goes into the SSE branch and calls `gen.__aiter__()` on a coroutine or non-iterable. That raises `AttributeError`.
   - Fix: pass `is_sse_stream=self.is_sse_stream` into the handler and drop the local computation.

2. **`fastapi/sse.py`, `format_sse_event`: field injection through `event`, `id` and `retry`.**
   - `event` and `id` are written as `f"event: {event}"` and `f"id: {id}"` with no newline check. Only `id` is checked for `\0`.
   - An `event` value like `"a\ndata: x"` injects extra SSE fields if the value comes from user input.
   - Fix: reject `\r` and `\n` in `event` and `id`, in the validator or in the formatter.

3. **`fastapi/sse.py`, `format_sse_event`: `raw_data` is altered by `str.splitlines()`.**
   - `splitlines()` also splits on `\x0b`, `\x0c`, `\x1c`–`\x1e`, `\x85`, `\u2028` and `\u2029`. These aren't SSE line terminators, so the client sees a different payload.
   - It drops a trailing newline: `"a\n"` becomes one line.
   - `raw_data=""` emits no `data:` line at all, so the browser fires no event.
   - Fix: split on `\r\n|\r|\n` explicitly, for example `re.split(r"\r\n|\r|\n", s)`.

**Worth checking**

4. **`fastapi/routing.py:529-560`: errors from the generator are wrapped.**
   - The producer runs in an `anyio` task group. If the generator raises, or `ResponseValidationError` is raised while serializing an item, the error reaches the caller as an `ExceptionGroup`. It won't be the original exception type.
   - Before this PR, JSONL streaming raised the original exception.
   - Any handler or test that expects the original exception type may break.

5. **Task group across a `yield` in an async generator.**
   - `_async_stream_sse` holds a task group open across `yield`. Closing that generator from a different task, for example on client disconnect, can raise "cancel scope in a different task" errors.
   - It needs a disconnect test with both sync and async generators.

**Minor**

- A `ServerSentEvent` with `data=None` can't send a JSON `null`.
- `_serialize_sse_item` skips `stream_item_field` validation and `response_model_include`/`exclude` for `ServerSentEvent` items. The comment says this is intentional, but the docs should say so.
- `max_buffer_size=1` plus the producer task means the generator runs one item ahead of what the client has received.

Fixing #1 to #3 is small. Do you want me to write the fixes and tests on a branch?

Findings submitted with the ReportFindings tool:
