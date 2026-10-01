"""Checkpoint independently observed target-branch and local code after knowledge maintenance."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import TypedDict


DOCUMENTS = (
    "AGENTS.md", "CLAUDE.md", "ARCHITECTURE.md", "REUSE_INDEX.md",
    "PR_REVIEW.md", "REVIEW_INDEX.md",
)
SKILLS = ("progressive-search", "verified-code-review", "knowledge-sync")
STAMP_NAME = "KNOWLEDGE_STAMP.json"
SOURCE_PATHS = (
    ".", *(f":(exclude,literal){name}" for name in (*DOCUMENTS, STAMP_NAME)),
    ":(exclude).claude/skills/**", ":(exclude).codex/skills/**",
    ":(exclude).agents/skills/**",
)


class LocalSnapshot(TypedDict):
    """The branch, commit, index and working contents analyzed for this checkout."""

    branch: str
    head: str
    index_digest: str
    worktree_digest: str


class Checkpoint(TypedDict):
    """Analyzed target-branch/local snapshots plus hashes of their knowledge artifacts."""

    version: int
    remote: str
    branch: str
    commit: str
    completed_at_utc: str
    summary: str
    artifacts: dict[str, str | None]
    local: LocalSnapshot | None


def git_bytes(repo: Path, *arguments: str) -> bytes:
    """Run Git without a shell, preserving NUL-delimited paths and patch bytes."""
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments], capture_output=True
    )
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip() or "Git command failed")
    return result.stdout


def git(repo: Path, *arguments: str) -> str:
    """Return stripped text for Git commands that do not emit path lists or patches."""
    return git_bytes(repo, *arguments).decode().strip()


def local_snapshot(repo: Path) -> LocalSnapshot:
    """Fingerprint staged, working and untracked source without changing Git's index."""
    if git_bytes(repo, "ls-files", "--unmerged", "-z", "--", *SOURCE_PATHS):
        raise ValueError("Resolve source merge conflicts before checkpointing local knowledge")
    head = git(repo, "rev-parse", "HEAD")
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    options = ("--binary", "--no-ext-diff", "--no-textconv", "--no-renames")
    staged = git_bytes(repo, "diff", "--cached", *options, head, "--", *SOURCE_PATHS)
    working = hashlib.sha256(git_bytes(repo, "diff", *options, head, "--", *SOURCE_PATHS))
    untracked = git_bytes(
        repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *SOURCE_PATHS
    )
    for name in sorted(filter(None, untracked.split(b"\0"))):
        path = repo / os.fsdecode(name)
        # Hash symlinks themselves; never follow an untracked link outside the checkout.
        content = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
        kind = b"link" if path.is_symlink() else str(path.stat().st_mode & 0o111).encode()
        working.update(name + b"\0" + kind + b"\0" + hashlib.sha256(content).digest())
    if head != git(repo, "rev-parse", "HEAD") or branch != git(repo, "rev-parse", "--abbrev-ref", "HEAD"):
        raise ValueError("Checkout changed while capturing local state; inspect again")
    return {
        "branch": branch, "head": head,
        "index_digest": hashlib.sha256(staged).hexdigest(),
        "worktree_digest": working.hexdigest(),
    }


def local_token(snapshot: LocalSnapshot) -> str:
    """Bind completion to the exact local snapshot inspected before edits."""
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def ancestor(repo: Path, older: str, newer: str) -> bool:
    """Distinguish a non-ancestor from a Git/history error."""
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
        text=True, capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise ValueError(result.stderr.strip())
    return result.returncode == 0


def shared_base(repo: Path, first: str, second: str) -> str | None:
    """Return no base for unrelated histories without hiding other Git errors."""
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", first, second],
        text=True, capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise ValueError(result.stderr.strip())
    return result.stdout.strip() if result.returncode == 0 else None


def commit_id(repo: Path, value: str) -> str:
    """Accept only a full hexadecimal commit ID available in this repository."""
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
        raise ValueError("Expected a full commit SHA, not a branch or abbreviation")
    return git(repo, "rev-parse", "--verify", value + "^{commit}")


def read_checkpoint(path: Path, remote: str, branch: str) -> tuple[Checkpoint | None, str]:
    """Load and validate the stamp, returning a token for stale-run detection."""
    if not path.exists():
        return None, "missing"
    content = path.read_bytes()
    state = json.loads(content)
    if not isinstance(state, dict):
        raise ValueError("Checkpoint must be an object")
    if set(state) != set(Checkpoint.__annotations__) or state["version"] != 2:
        raise ValueError("Unrecognized checkpoint schema; do not reset it automatically")
    if state["remote"] != remote or state["branch"] != branch:
        raise ValueError(
            f"Checkpoint describes {state['remote']}/{state['branch']}, not {remote}/{branch}"
        )
    if not all(isinstance(state[key], str) for key in ("commit", "completed_at_utc", "summary")):
        raise ValueError("Invalid checkpoint fields")
    if not isinstance(state["artifacts"], dict) or not all(
        isinstance(key, str) and (value is None or isinstance(value, str))
        for key, value in state["artifacts"].items()
    ):
        raise ValueError("Invalid artifact fingerprints")
    snapshot = state["local"]
    if snapshot is not None and (
        not isinstance(snapshot, dict) or set(snapshot) != set(LocalSnapshot.__annotations__)
        or not all(isinstance(value, str) for value in snapshot.values())
    ):
        raise ValueError("Invalid local snapshot")
    return state, hashlib.sha256(content).hexdigest()


def artifact_hashes(repo: Path) -> dict[str, str | None]:
    """Fingerprint managed documents and skill copies without reading application code."""
    paths = {name: repo / name for name in DOCUMENTS}
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    for name in SKILLS:
        for label, directory in (
            ("codex", codex_home / "skills" / name),
            ("claude", repo / ".claude" / "skills" / name),
        ):
            paths[f"{label}/{name}/SKILL.md"] = directory / "SKILL.md"
            if label == "codex":
                paths[f"{label}/{name}/agents/openai.yaml"] = directory / "agents/openai.yaml"
            if name == "knowledge-sync":
                paths[f"{label}/{name}/scripts/checkpoint.py"] = directory / "scripts/checkpoint.py"
    return {
        name: hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        for name, path in paths.items()
    }


def default_branch(repo: Path, remote: str) -> str:
    """Resolve the remote's default branch (e.g. main or master) from its HEAD symref."""
    try:
        return git(repo, "symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD").split("/", 1)[1]
    except ValueError:
        raise ValueError(
            f"Cannot resolve {remote}'s default branch; run `git remote set-head {remote} -a` or pass --branch"
        ) from None


def fetch_target(repo: Path, remote: str, branch: str) -> str:
    """Fetch the target branch and immediately freeze FETCH_HEAD; never switch the checkout."""
    git(repo, "fetch", "--no-tags", remote, f"refs/heads/{branch}")
    target = git(repo, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    if git(repo, "rev-parse", "--is-shallow-repository") == "true":
        raise ValueError("Shallow history: obtain complete target-branch ancestry before continuing")
    return target


def relation(repo: Path, previous: str | None, target: str) -> str:
    """Classify the checkpoint relative to the fetched target-branch snapshot."""
    if previous is None:
        return "bootstrap"
    commit_id(repo, previous)
    if previous == target:
        return "unchanged"
    if ancestor(repo, previous, target):
        return "ahead"
    return "rewritten"


def save_checkpoint(path: Path, state: Checkpoint, expected_token: str) -> None:
    """Atomically replace the stamp only if this run's starting stamp is unchanged."""
    if read_checkpoint(path, state["remote"], state["branch"])[1] != expected_token:
        raise ValueError("Checkpoint changed during this run; inspect again before completing")
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
            temporary_path = Path(output.name)
            json.dump(state, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    """Inspect without stamping, or stamp an explicitly certified completed analysis."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inspect", "complete"))
    parser.add_argument("--repo", default=".")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", help="target branch; defaults to the remote's default branch")
    parser.add_argument("--target")
    parser.add_argument("--expected-token")
    parser.add_argument("--expected-local-token")
    parser.add_argument("--summary")
    parser.add_argument("--rebaseline", action="store_true")
    args = parser.parse_args()
    repo = Path(git(Path(args.repo), "rev-parse", "--show-toplevel"))
    stamp_path = repo / STAMP_NAME
    if stamp_path.is_symlink():
        raise ValueError("Checkpoint must be a regular file in the checkout")
    branch = args.branch or default_branch(repo, args.remote)
    state, token = read_checkpoint(stamp_path, args.remote, branch)
    if args.mode == "complete" and (
        not args.target or not args.summary or args.expected_token != token
        or not args.expected_local_token
    ):
        raise ValueError("complete requires target, summary and both captured inspect tokens")
    latest = fetch_target(repo, args.remote, branch)
    previous = state["commit"] if state else None
    local = local_snapshot(repo)
    if args.mode == "inspect":
        status = relation(repo, previous, latest)
        hashes = artifact_hashes(repo)
        output = {
            "remote": args.remote, "branch": branch,
            "status": status, "stamp": previous, "target": latest, "token": token,
            "local": local, "local_token": local_token(local),
            "previous_local": state["local"] if state else None,
            "local_status": "bootstrap" if state is None or state["local"] is None else
            "unchanged" if state["local"] == local else "changed",
            "local_merge_base": shared_base(repo, latest, local["head"]),
            "local_commit_count": int(git(repo, "rev-list", "--count", f"{latest}..{local['head']}")),
            "artifact_drift": [
                name for name in sorted(set(hashes) | set(state["artifacts"] if state else {}))
                if state is None or hashes.get(name) != state["artifacts"].get(name)
            ],
            "new_commit_count": int(git(repo, "rev-list", "--count", f"{previous}..{latest}"))
            if status == "ahead" else 0,
        }
    else:
        if local_token(local) != args.expected_local_token:
            raise ValueError("Local code changed during maintenance; inspect and analyze it before stamping")
        target = commit_id(repo, args.target)
        if not ancestor(repo, target, latest):
            raise ValueError(f"Target is no longer on {args.remote}/{branch}; leave the stamp unchanged")
        status = relation(repo, previous, target)
        if status == "rewritten" and not args.rebaseline:
            raise ValueError("History was rewritten; explicit full rebaseline is required")
        new_state: Checkpoint = {
            "version": 2, "remote": args.remote, "branch": branch, "commit": target,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "summary": args.summary, "artifacts": artifact_hashes(repo),
            "local": local,
        }
        if local_snapshot(repo) != local:
            raise ValueError("Local code changed before saving; leave the stamp unchanged")
        save_checkpoint(stamp_path, new_state, token)
        output = {
            "stamped": target, "remote_head": latest, "more_commits_pending": target != latest,
            "local_head": local["head"], "local_branch": local["branch"],
        }
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        sys.stderr.write(f"Knowledge sync stopped: {error}\n")
        sys.exit(1)
