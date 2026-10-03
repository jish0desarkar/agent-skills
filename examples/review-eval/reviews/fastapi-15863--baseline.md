# fastapi-15863: stock Claude Code, run 1

The session's final review, unedited except that scratch paths were removed.

---

I reviewed PR #15863 and found one low-severity issue. I didn't run the tests.

- **`fastapi/routing.py:1843`:** Requests that aren't GET or HEAD now do filesystem lookups before they get an answer. Before, they always got a 405. Now a lookup error can replace that 405:
  - A `PermissionError` gives a 401.
  - An `OSError` other than `ENAMETOOLONG` gives a 500.

  This is an edge case and may be acceptable.

I reviewed the diff from `gh pr diff 15863`, because the local branch has no upstream diff. I also read the surrounding `get_response` code. I left out your local changes to `README.md` and `notes.local.txt`.

Findings submitted with the ReportFindings tool:
- fastapi/routing.py:1843 [PLAUSIBLE] (correctness) Non-GET/HEAD requests now do filesystem lookups before answering, so lookup errors can replace the old unconditional 405.
  Failure scenario: POST to a frontend path whose lookup raises PermissionError returns 401. A POST to a path that hits a non-ENAMETOOLONG OSError propagates as a 500. Before this change every non-GET/HEAD request got 405 without touching the filesystem. This is an edge case and may be acceptable.
