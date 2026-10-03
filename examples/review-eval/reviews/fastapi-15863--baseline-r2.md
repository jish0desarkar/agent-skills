# fastapi-15863: stock Claude Code, run 2

The session's final review, unedited except that scratch paths were removed.

---

I couldn't run the tests, so this review is from reading the diff only. The sandbox blocked `uv` from its cache, and the system `python3` doesn't have pytest.

## PR #15863: `app.frontend()` returns 404 for non-GET/HEAD requests with no static match

I found no blocking issues. The change touches `fastapi/routing.py`, `docs/en/docs/tutorial/frontend.md` and `tests/test_frontend.py`.

**What it does**
- For methods other than `GET` and `HEAD`, `get_response` now answers `405` only if the path matches a real static resource, meaning a regular file or a directory that contains `index.html`. Otherwise it answers `404`. Before, every non-GET/HEAD request got `405`.
- The path-lookup error handling moves into two helpers, `_lookup_path` and `_lookup_static_resource`. The GET and non-GET branches now share them, so the file-or-directory-index logic exists once.
- The docs now say the fallback applies only to `GET` and `HEAD`, and that other methods get `404`.

**Observations (nits, not blockers)**
1. **Directory index lookup now handles errors.** The old code called `lookup_path(index_path)` directly, so its errors weren't mapped. It now goes through `_lookup_path`, so `PermissionError` gives `401` and an over-long name gives `404`. That's more consistent, but it's a small behaviour change the PR description doesn't mention.
2. **Redundant `stat` calls.** A directory request now does two `stat` calls through the threadpool, and a `POST` to an existing file does one. That's the same as before, so it's fine.
3. **Redirect only on `GET`/`HEAD`.** A `POST` to a directory without a trailing slash returns `405`, not a redirect, which is reasonable. A test for it would be a good addition if one isn't already in the 135 added test lines.
4. **Possible docs wording issue.** "Regular path operations still have higher priority" is true only if the frontend is mounted after the routes. This is worth confirming against how `app.frontend()` registers itself.

Overall it's a clean refactor, and the new behaviour matches the docs. I'd approve it once CI is green.

Findings submitted with the ReportFindings tool:
