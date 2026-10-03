# fastapi-15863: verified-code-review v2, run 1

The session's final review, unedited except that scratch paths were removed.

---

### Findings
No actionable findings. I found no regression introduced by this PR.

The PR changes `_FrontendStaticFiles.get_response` in `fastapi/routing.py:1842`. For non-`GET`/`HEAD` methods it now returns 405 only when the path resolves to a real static file or directory index. Otherwise it returns 404. Before, it returned 405 for every such request.

### Trace log
| Behavior | Rows applied | Checked | Result |
|---|---|---|---|
| Non-`GET`/`HEAD` returns 405 only if a static resource exists, else 404 | changes what is returned or raised; adds a branch beside existing ones | The only caller is `_FrontendRoute.handle`. `_FrontendRoute.matches` (`routing.py:1958`) returns `Match.PARTIAL` for these methods, so API routes still take priority. Only the status of an already-unmatched request changes. | Fine |
| Lookup and error mapping moved into `_lookup_path` and `_lookup_static_resource` | removes or moves code | Old side effects: 401 on `PermissionError`, 404 on `ENAMETOOLONG` and `ValueError`, regular-file serving, and the directory-index redirect when the path has no trailing slash. All still happen on the `GET`/`HEAD` path. Fallthrough to `404.html` or `index.html` is unchanged when a directory has no index. | Equivalent |
| Directory-index lookup now goes through the mapped-error helper | iterates or parses an input | Before, a long or invalid `index.html` path raised a raw `OSError` or `ValueError`. Now it maps to 404. That only fixes an edge case, and `path` has already passed the first lookup. | Improvement |
| Docs update in `frontend.md` | none | The text matches the new behavior. | Fine |

### Observations (not findings)
- **Permission errors:** non-`GET` requests on an unreadable path now return 401 (from the shared helper). Before, they returned 405. The change is consistent with how `GET` behaves.
- **Allow header:** the 405 response has no `Allow` header. That was already true before this PR.
- **Extra lookup:** non-`GET` requests that match a static file now do a second `stat`. This is negligible.

### Scope and limits
- **Commits:** I reviewed head `279e298` against base and merge-base `c2708d9`.
- **Not run:** I did not run the tests, and I did not see CI results.
- **Not read in full:** I did not read the router's partial-match ordering code in full. My conclusion that API routes win rests on the existing `matches` logic and the PR's tests, such as `test_api_route_404_is_not_replaced_by_frontend_fallback`.
