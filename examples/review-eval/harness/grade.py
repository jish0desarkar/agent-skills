"""Blind grading: one Opus session per PR scores the three reviews, labelled in random order."""
import json
import pathlib
import random
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analyze import summarize  # noqa: E402

EV = pathlib.Path(__file__).resolve().parent
import os
ARMS = tuple(os.environ.get("GRADE_ARMS", "baseline,skill,skill-maps").split(","))
GDIR = os.environ.get("GRADE_DIR", "grades")
KEYS = (EV / "keys" / "ALL.md").read_text()


def key_for(pid):
    if pid in ("django-21344", "fastapi-15863"):
        return "No defect is known in this PR (no later fix references it). There are no K items; grade every finding on its merits."
    sections = re.split(r"\n(?=## )", KEYS)
    sec = next(s for s in sections if s.startswith(f"## {pid} "))
    if pid == "aiohttp-12988":
        sec += "\n\n" + (EV / "keys" / "aiohttp-12988.md").read_text()
    return sec


PROMPT = """You are grading several code reviews of the same pull request. You do not know how they were produced; judge only what they say.

There are {count} reviews: {labels}. The repository is checked out in the current directory. The PR is {repo}#{number} "{title}". Its merge base is commit {base} and its head is commit {head} (both are in this repository). Check every claim against the PR's code with `git show {head}:<path>`, `git grep -n <pattern> {head} -- <dir>` and `git diff {base}...{head}`. Do not trust a review's quotes or line numbers without looking.

Answer key, written from the maintainers' later fixes:

{key}

For each review:
1. For each known defect (K1, K2, ...): CAUGHT, PARTIAL or MISSED, using the definitions above, with the review's words that earn the verdict.
2. Every other distinct problem the review reports (ignore praise, "looks fine" notes and pure questions). For each: a one-line summary, the severity the review gave it (or "none"), and your verdict: VALID (true at this revision and reachable through real use), FALSE_POSITIVE (contradicted by the code, unreachable, or a misreading), or NOISE (style, docs, wording or test nits, or speculation presented as a defect). Say briefly what you checked.
3. Whether it states what it could not verify (for example that no tests ran), and whether it claims that something ran or passed that could not have.

Reviews:

{reviews}

End your answer with one fenced ```json block holding an object keyed by review label ({labels}), each:
{{"known": [{{"id": "K1", "verdict": "CAUGHT|PARTIAL|MISSED", "evidence": "..."}}],
  "other": [{{"summary": "...", "severity": "...", "verdict": "VALID|FALSE_POSITIVE|NOISE", "reason": "..."}}],
  "states_limits": true, "claims_unrun_execution": false}}
"""


def prepare(pid):
    meta = json.loads((EV / "prs" / f"{pid}.json").read_text())
    gdir = EV / GDIR / pid
    if gdir.exists():
        shutil.rmtree(gdir)
    gdir.mkdir(parents=True)
    subprocess.run(["git", "clone", "-q", meta["origin"], str(gdir / "repo")], check=True)
    subprocess.run(["git", "-C", str(gdir / "repo"), "fetch", "-q", "origin", f"pull/{meta['number']}/head"], check=True,
                   env={"GIT_ALLOW_PROTOCOL": "file", "PATH": "/usr/bin:/bin"})
    labels = list("ABCDEF"[: len(ARMS)])
    random.Random(f"grade-{pid}-{GDIR}").shuffle(labels)
    mapping = dict(zip(labels, ARMS))
    blocks = []
    for label in sorted(mapping):
        s_ = summarize(EV / "runs" / pid / mapping[label])
        text = s_["final"].strip() or "(The review produced no final message.)"
        blocks.append(f'<review label="{label}">\n{text}\n</review>')
    (gdir / "mapping.json").write_text(json.dumps(mapping, indent=1))
    prompt = PROMPT.format(repo=meta["repo"], number=meta["number"], title=meta["title"], base=meta["baseRefOid"],
                           head=meta["headRefOid"], key=key_for(pid), reviews="\n\n".join(blocks),
                           count=len(ARMS), labels=", ".join(sorted(mapping)))
    (gdir / "prompt.txt").write_text(prompt)
    print(f"{pid}: prompt {len(prompt)} chars", flush=True)


if __name__ == "__main__":
    for pid in sys.argv[1:]:
        prepare(pid)
