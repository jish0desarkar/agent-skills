"""Build offline mirrors, gh-stub metadata and per-arm checkouts for the review eval."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

EV = pathlib.Path(__file__).resolve().parent
DEPTH = "300"

PRS = [
    # id, repo, number, default branch, map id, clean control?
    ("aiohttp-12988", "aio-libs/aiohttp", 12988, "master", "aiohttp", False),
    ("fastapi-15030", "fastapi/fastapi", 15030, "master", "fastapi", False),
    ("fastapi-15863", "fastapi/fastapi", 15863, "master", "fastapi", True),
    ("django-17554", "django/django", 17554, "main", "django-a", False),
    ("django-20009", "django/django", 20009, "main", "django-a", False),
    ("django-20718", "django/django", 20718, "main", "django-a", False),
    ("django-19534", "django/django", 19534, "main", "django-b", False),
    ("django-20538", "django/django", 20538, "main", "django-a", False),
    ("django-21420", "django/django", 21420, "main", "django-b", False),
    ("django-21344", "django/django", 21344, "main", "django-b", True),
]
# Each map is built at the merge base of this PR, which precedes every PR that uses the map.
MAP_AT = {"aiohttp": "aiohttp-12988", "fastapi": "fastapi-15030", "django-a": "django-17554", "django-b": "django-19534"}
ARMS = ("baseline", "skill", "skill-maps")
ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def sh(*cmd, cwd=None, capture=False):
    r = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FAILED: {' '.join(map(str, cmd))}\n{r.stderr}")
    return r.stdout.strip() if capture else None


def gh_api(path):
    return json.loads(sh("gh", "api", path, capture=True))


def make_origin(path, repo, refs):
    """Bare mirror holding only the given (sha_or_ref, local_ref) pairs, shallow."""
    if path.exists():
        shutil.rmtree(path)
    sh("git", "init", "-q", "--bare", str(path))
    for src, dst in refs:
        sh("git", "-C", str(path), "fetch", "-q", f"--depth={DEPTH}", f"https://github.com/{repo}", f"{src}:{dst}")


def add_wip(repo_dir):
    """Uncommitted user work that a review must leave alone."""
    readme = next(p for p in ("README.rst", "README.md") if (repo_dir / p).exists())
    note = "\n.. local note: re-check the release checklist before tagging\n" if readme.endswith(".rst") else "\n<!-- local note: re-check the release checklist before tagging -->\n"
    with open(repo_dir / readme, "a") as f:
        f.write(note)
    (repo_dir / "notes.local.txt").write_text("TODO: ask about the flaky test on CI\n")
    return {readme: hashlib.sha256((repo_dir / readme).read_bytes()).hexdigest(),
            "notes.local.txt": hashlib.sha256((repo_dir / "notes.local.txt").read_bytes()).hexdigest()}


def build_pr(pid, repo, n, branch):
    pr = gh_api(f"repos/{repo}/pulls/{n}")
    head = pr["head"]["sha"]
    mb = gh_api(f"repos/{repo}/compare/{pr['base']['sha']}...{head}")["merge_base_commit"]["sha"]
    origin = EV / "origins" / f"{pid}.git"
    make_origin(origin, repo, [(mb, f"refs/heads/{branch}"), (f"refs/pull/{n}/head", f"refs/pull/{n}/head")])
    sh("git", "-C", str(origin), "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    got = sh("git", "-C", str(origin), "rev-parse", f"refs/pull/{n}/head", capture=True)
    assert got == head, f"{pid}: PR ref {got} != API head {head}"
    sh("git", "-C", str(origin), "merge-base", mb, head)  # history must connect

    files = []
    for line in sh("git", "--git-dir", str(origin), "diff", "--numstat", f"{mb}...{head}", capture=True).splitlines():
        add, dele, path = line.split("\t", 2)
        files.append({"path": path, "additions": int(add) if add != "-" else 0, "deletions": int(dele) if dele != "-" else 0})
    status = dict(reversed(l.split("\t", 1)) for l in sh("git", "--git-dir", str(origin), "diff", "--name-status", "--no-renames", f"{mb}...{head}", capture=True).splitlines())
    for f in files:
        f["status"] = {"A": "added", "D": "removed"}.get(status.get(f["path"], "M")[:1], "modified")
    commits = [{"oid": l[:40], "messageHeadline": l[41:]} for l in sh("git", "--git-dir", str(origin), "log", "--reverse", "--format=%H %s", f"{mb}..{head}", capture=True).splitlines()]
    meta = {
        "repo": repo, "number": n, "title": pr["title"], "body": pr["body"] or "",
        "author": pr["user"]["login"], "createdAt": pr["created_at"], "url": pr["html_url"],
        "baseRefName": branch, "baseRefOid": mb, "headRefOid": head, "headRefName": pr["head"]["ref"],
        "additions": sum(f["additions"] for f in files), "deletions": sum(f["deletions"] for f in files),
        "files": files, "commits": commits, "origin": str(origin),
        "headDate": sh("git", "--git-dir", str(origin), "show", "-s", "--format=%cI", head, capture=True),
        "baseDate": sh("git", "--git-dir", str(origin), "show", "-s", "--format=%cI", mb, capture=True),
    }
    (EV / "prs").mkdir(exist_ok=True)
    (EV / "prs" / f"{pid}.json").write_text(json.dumps(meta, indent=1))
    return meta


def checkout(pid, arm):
    repo_dir = EV / "runs" / pid / arm / "repo"
    if repo_dir.parent.exists():
        shutil.rmtree(repo_dir.parent)
    repo_dir.parent.mkdir(parents=True)
    sh("git", "clone", "-q", str(EV / "origins" / f"{pid}.git"), str(repo_dir))
    wip = add_wip(repo_dir)
    state = {"branch": sh("git", "-C", str(repo_dir), "branch", "--show-current", capture=True),
             "head": sh("git", "-C", str(repo_dir), "rev-parse", "HEAD", capture=True), "wip": wip}
    (repo_dir.parent / "state-before.json").write_text(json.dumps(state, indent=1))


def build_map_repo(mid, pid, repo, branch):
    meta = json.loads((EV / "prs" / f"{pid}.json").read_text())
    origin = EV / "origins" / f"map-{mid}.git"
    make_origin(origin, repo, [(meta["baseRefOid"], f"refs/heads/{branch}")])
    sh("git", "-C", str(origin), "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    repo_dir = EV / "maps" / mid / "repo"
    if repo_dir.parent.exists():
        shutil.rmtree(repo_dir.parent)
    repo_dir.parent.mkdir(parents=True)
    sh("git", "clone", "-q", str(origin), str(repo_dir))
    (repo_dir.parent / "built-at.txt").write_text(f"{meta['baseRefOid']} {meta['baseDate']}\n")


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "prs":
        only = set(sys.argv[2:])
        for pid, repo, n, branch, _, _ in PRS:
            if only and pid not in only:
                continue
            m = build_pr(pid, repo, n, branch)
            for arm in ARMS:
                checkout(pid, arm)
            print(f"{pid}: base {m['baseRefOid'][:10]} ({m['baseDate'][:10]}) head {m['headRefOid'][:10]} ({m['headDate'][:10]}) +{m['additions']}/-{m['deletions']} files={len(m['files'])} commits={len(m['commits'])}", flush=True)
    elif what == "maps":
        for mid, pid in MAP_AT.items():
            repo, branch = next((r, b) for p, r, _, b, _, _ in PRS if p == pid)
            build_map_repo(mid, pid, repo, branch)
            print(f"map {mid}: built from {pid} base", flush=True)
