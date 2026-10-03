# fastapi-15030: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

I found four defects in PR #15030 (Server-Sent Events support); none were exercised end to end, because this environment has no starlette. I reviewed head `2269bb4` against base `48d58ae`.

1. **Medium: field injection in `event` and `id`.** `fastapi/sse.py:172` writes `event` and `id` straight into the output. Only `id` is checked, and only for NUL. An `event` like `"x\ndata: evil"` therefore adds a forged `data:` line. This is introduced in this PR and confirmed by reading the code.
2. **Medium: `splitlines()` on data.** `fastapi/sse.py:167` splits data on characters the SSE spec doesn't treat as line breaks (U+2028, `\x0c`, `\x0b` and others). It also drops an empty string and a trailing newline. Effects:
   - A raw U+2028 or `\x0c` in a JSON string becomes invalid JSON on the client.
   - `raw_data=""` emits no `data:` line, so the client never dispatches that event.

   I confirmed the `splitlines` behavior in plain Python only.
3. **Medium (plausible, not run): handler and route disagree on SSE detection.** `get_request_handler` (`fastapi/routing.py:371`) decides SSE from the response class alone, while `APIRoute.is_sse_stream` also requires a generator. A non-generator endpoint with `response_class=EventSourceResponse` enters the SSE branch and hands a coroutine or other non-iterator value to `iterate_in_threadpool`, so it probably returns a 500.
4. **Low (plausible, not run): exceptions arrive wrapped.** The producer runs inside an anyio task group (`fastapi/routing.py:531`). Errors from the generator or from `ResponseValidationError` probably reach the consumer as an `ExceptionGroup`, so code that matches on the original exception type, such as exception handlers, stops matching. The old JSONL path raised them directly.

**Trace log:**
- The JSONL serializer was refactored into the shared `_serialize_data`. JSONL behavior is unchanged: it still appends `\n` and uses the same validation and serialization.
- The `stream_item_type` extraction in `APIRoute.__init__` is widened to include `EventSourceResponse` and exclude `ServerSentEvent` items.
- The OpenAPI branch (`itemSchema`) is guarded by `route.is_sse_stream`.

**Not checked:**
- I did not run the project tests, because starlette isn't installed here.
- CI status wasn't seen.
- I didn't read the docs and tutorial files closely.

Findings submitted with the ReportFindings tool:
- fastapi/sse.py:172 [CONFIRMED] (correctness) format_sse_event writes `event` and `id` into the wire format without rejecting CR/LF. Only `id` is checked for NUL.
  Failure scenario: yield ServerSentEvent(event="x\ndata: injected") or an `id` built from user input containing a newline. The output has an extra `data: injected` line, so a client receives a forged field or event. Unsanitized user-controlled `event` or `id` makes this an SSE injection.
- fastapi/sse.py:167 [CONFIRMED] (correctness) `data_str.splitlines()` splits on more than the line terminators SSE recognizes (\n, \r, \r\n). It splits on U+2028, \x0b, \x0c, \x1c-\x1e and \x85, and it drops an empty or trailing-empty line.
  Failure scenario: I confirmed the splitlines behavior with plain Python only; I could not run the app, because starlette is not installed here. raw_data="a b" becomes two `data:` lines, and the client rejoins them as "a\nb". A JSON payload from model_dump_json that holds a raw U+2028 or \x0c inside a string becomes invalid JSON on the client. raw_data="" yields no `data:` line, so a client does not dispatch the event at all. A payload ending in "\n" loses that newline.
- fastapi/routing.py:491 [PLAUSIBLE] (correctness) The handler picks the SSE branch from the response class alone (`is_sse_stream` at routing.py:371), not from whether the endpoint is a generator. APIRoute.is_sse_stream does check is_generator. The two flags disagree.
  Failure scenario: A non-generator endpoint with response_class=EventSourceResponse (for example `async def f(): return [..]`) enters the SSE branch. `gen` is then a coroutine, or whatever the function returned, and is passed to iterate_in_threadpool. Starlette raises TypeError, so the request returns 500. This is a path that worked before this PR for an endpoint that returned its own iterator or Response. I did not run it. I traced it by reading the code.
- fastapi/routing.py:531 [PLAUSIBLE] (correctness) The producer task runs inside an anyio task group. An exception in the generator or in `_serialize_sse_item` reaches the consumer as an ExceptionGroup, not as the original exception.
  Failure scenario: A ResponseValidationError raised while serializing an item, or any error in user code, surfaces wrapped as an ExceptionGroup in the response stream. Code that matches on the specific exception type, such as logging, middleware or exception handlers, no longer matches it. The old JSONL path raised the exception directly.
- fastapi/sse.py:172 [CONFIRMED] (correctness) format_sse_event writes `event` and `id` into the wire format without rejecting CR/LF. Only `id` is checked for NUL.
  Failure scenario: yield ServerSentEvent(event="x\ndata: injected") or an `id` built from user input containing a newline. The output has an extra `data: injected` line, so a client receives a forged field or event. Unsanitized user-controlled `event` or `id` makes this an SSE injection.
- fastapi/sse.py:167 [CONFIRMED] (correctness) `data_str.splitlines()` splits on more than the line terminators SSE recognizes (\n, \r, \r\n). It splits on U+2028, \x0b, \x0c, \x1c-\x1e and \x85, and it drops an empty or trailing-empty line.
  Failure scenario: I confirmed the splitlines behavior with plain Python only; I could not run the app, because starlette is not installed here. raw_data="a b" becomes two `data:` lines, and the client rejoins them as "a\nb". A JSON payload from model_dump_json that holds a raw U+2028 or \x0c inside a string becomes invalid JSON on the client. raw_data="" yields no `data:` line, so a client does not dispatch the event at all. A payload ending in "\n" loses that newline.
- fastapi/routing.py:491 [PLAUSIBLE] (correctness) The handler picks the SSE branch from the response class alone (`is_sse_stream` at routing.py:371), not from whether the endpoint is a generator. APIRoute.is_sse_stream does check is_generator. The two flags disagree.
  Failure scenario: A non-generator endpoint with response_class=EventSourceResponse (for example `async def f(): return [..]`) enters the SSE branch. `gen` is then a coroutine, or whatever the function returned, and is passed to iterate_in_threadpool. Starlette raises TypeError, so the request returns 500. This is a path that worked before this PR for an endpoint that returned its own iterator or Response. I did not run it. I traced it by reading the code.
- fastapi/routing.py:531 [PLAUSIBLE] (correctness) The producer task runs inside an anyio task group. An exception in the generator or in `_serialize_sse_item` reaches the consumer as an ExceptionGroup, not as the original exception.
  Failure scenario: A ResponseValidationError raised while serializing an item, or any error in user code, surfaces wrapped as an ExceptionGroup in the response stream. Code that matches on the specific exception type, such as logging, middleware or exception handlers, no longer matches it. The old JSONL path raised the exception directly.
