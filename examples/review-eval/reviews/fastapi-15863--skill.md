# fastapi-15863: with verified-code-review

The session's final review, unedited except that scratch paths were removed.

---

### No actionable findings in PR #15863

Reviewed `c2708d9` (base) to `279e298` (head). I read the diff statically and ran no tests.

**What changed**
- `_FrontendStaticFiles.get_response` now answers a non-`GET`/`HEAD` request with `405` only if the path matches a real static file or directory `index.html`. Otherwise it returns `404`.
- To do this, the file lookup moved into two helpers, `_lookup_path` and `_lookup_static_resource`.
- The `GET`/`HEAD` path is unchanged:
  - It returns the same files.
  - It still redirects a directory to its trailing-slash URL when the directory has an `index.html`.
  - It still reaches the fallback and `404.html` handling when nothing matches.
- The docs and the new tests describe the new behaviour.

**Why I found no defect**
- **Real API routes are unaffected.** The router tries normal routes first and handles any partial match (right path, wrong method) before it reaches the low-priority frontend routes (`routing.py:2538-2548`). So `POST /items` against a `GET`-only API route still gets `405` from the API. The frontend `404` only applies to paths no API route claims.
- **Error mapping is preserved.** The `PermissionError` → `401`, `ENAMETOOLONG` → `404` and `ValueError` → `404` handling moved unchanged into `_lookup_path`. Both lookups, including the `index.html` one, go through it.
- **Directory handling matches the old code.** A directory without `index.html` returns `None`, as it fell through before, so fallback handling is the same.

**Minor, not worth blocking**
- A non-`GET` request that hits an unreadable path now gets `401` where it used to get `405`. That is a very rare edge case and consistent with `GET`.
- Non-`GET` `404` responses never use the `404.html` fallback page. The docs imply this, and it seems intended.

**Limits**
- I did not run `tests/test_frontend.py` or check CI.
- The PR checklist items are unticked and the description is empty. The Discussion link and coverage claim are unverified.
- The review is pinned to head `279e298` as fetched; I did not re-check the live head afterwards.
