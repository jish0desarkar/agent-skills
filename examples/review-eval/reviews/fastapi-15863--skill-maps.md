# fastapi-15863: with verified-code-review and blind-built maps

The session's final review, unedited except that scratch paths were removed.

---

### Review of PR #15863: no actionable findings

I found no verified defects at head `279e298` (base `c2708d9`, `master`). I read the diff and traced the behaviour by reading source. I did not run the tests, lint or mypy, and I did not look at CI.

**What the PR changes**
- The change is in `_FrontendStaticFiles.get_response` (`fastapi/routing.py` around line 1841). Non-`GET`/`HEAD` requests now return `405` only when the path resolves to a real static file, either a regular file or a directory with an `index.html`. Anything else returns `404`.
- The lookup logic is now shared in two helpers, `_lookup_path` and `_lookup_static_resource`. On `GET` the extraction keeps the previous behaviour:
  - the trailing-slash redirect for directory indexes;
  - the `401` on `PermissionError`;
  - the `404` for `ENAMETOOLONG` and `ValueError`.
- The docs page `frontend.md` is updated, and tests are added in `tests/test_frontend.py`.

**Checks**
- **Priority over path operations:** `Router.app` (`routing.py` around line 2528) tries normal routes first, full and then partial matches. Frontend routes are low-priority and only reached afterwards, so an API route that matches the path with a different method still gets its `405`. The new frontend `404` can't shadow it.
- **Frontend selection:** `_FrontendRouteGroup._match` still picks the most specific prefix. The new tests cover the longest-prefix, `APIRouter` prefix and `fallback` variants (`404.html`, `auto`, `None`).
- **`GET` and `HEAD`:** the fallback and navigation logic is unchanged. A `HEAD` test for the fallback is added.

**Minor observations, not findings**
- A non-`GET` request to a path that raises `PermissionError` now returns `401`. Before, any non-`GET` request returned `405` before touching the filesystem. This is an edge case, and it is consistent with how `GET` behaves.
- The new non-`GET` branch calls `_lookup_static_resource` separately from the `GET` branch, so the lookup code runs from two places. This is only a readability point.
- The PR description is mostly the empty template. The checklist is unticked and no discussion is linked. That is a process point for the maintainers, not a code issue.
