# fastapi-15863: verified-code-review v2, run 2

The session's final review, unedited except that scratch paths were removed.

---

### PR #15863 review: no actionable findings

I found no defects I could prove on this revision. I read the code only and did not run the tests.

The PR changes `_FrontendStaticFiles.get_response` in `fastapi/routing.py`. A non-`GET`/`HEAD` request now returns 405 only if it matches a real static file or a directory `index.html`. Otherwise it returns 404. The old unconditional 405 is gone. The static-file lookup moved into two new helpers, `_lookup_path` and `_lookup_static_resource`.

**Trace log**

| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| Non-`GET`/`HEAD` returns 404 instead of 405 when there's no static match | changes what is returned; adds a branch beside siblings | `get_response` has no other callers. It is reached only through `_FrontendRoute.handle`, which `_FrontendRouteGroup.handle` calls after picking the route (full match first, then partial). | Nothing else relied on the old 405. Existing 405 tests still hold because they hit real files. |
| Lookup refactored into helpers | removes or moves code; hands work to a library call | The old code handled `PermissionError`→401, `ENAMETOOLONG`→404 and `ValueError`→404 only on the first lookup. The helper applies them to both lookups, including the `index.html` lookup. The 401/404 error mapping now covers the second lookup too. Directory redirect, `file_response`, the 404.html/auto/index.html fallbacks and HEAD handling are unchanged. | Behavior is preserved, with slightly better error coverage. |
| Priority between regular routes and frontend routes | state across calls | `_FrontendRoute.matches` returns PARTIAL for non-`GET`/`HEAD`. A full-match path operation still wins. A `GET`-only API route (a partial match) registered earlier still produces its own 405. The frontend only answers when nothing else matches. | Matches the new docs text. |
| Longest-prefix selection for non-`GET` requests | adds a branch beside siblings | `_FrontendRouteGroup._match` picks the most specific partial match. The new test covers `/admin` over `/`. | Correct. |

**Pre-existing and out of scope**
- The 405 responses carry no `Allow` header.
- A `PermissionError` on a non-`GET` request now returns 401 where it used to return 405. This is correct and edge-only.

**Not checked**
- I did not run the tests or see CI.
- The PR checklist is unticked and has no linked discussion, which is a process matter.

Reviewed head `279e2983e86478589163c574d1a1a49d9e7264d0` against merge base `c2708d981729c96437dcc1d7cfa40cd15128bc60`.
