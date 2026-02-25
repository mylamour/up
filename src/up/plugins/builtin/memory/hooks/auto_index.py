#!/usr/bin/env python3
"""Auto-index hook: index git commits into memory.

Triggers on GIT_COMMIT event. Indexes commit message, files changed,
and diff summary into memory for semantic search.

Exit codes:
  0 = allow (indexed or skipped)
  1 = warn (indexed to memory)
"""

import json
import sys
import os
import subprocess
from pathlib import Path


def _load_config(workspace):
    """Load auto_index config from .up/config.json."""
    config_path = os.path.join(workspace, ".up", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            return cfg.get("automation", {}).get("memory", {}).get(
                "auto_index_commits", True
            )
        except (json.JSONDecodeError, OSError):
            pass
    return True


def _should_skip_commit(message):
    """Skip merge commits and chore: prefix commits."""
    if not message:
        return True
    msg_lower = message.strip().lower()
    if msg_lower.startswith("merge "):
        return True
    if msg_lower.startswith("chore:"):
        return True
    return False


def _get_commit_details(workspace, commit_sha):
    """Get commit details: message, files changed, diff summary."""
    details = {"message": "", "files": [], "diff_summary": ""}
    try:
        # Commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%s%n%n%b", commit_sha],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            details["message"] = result.stdout.strip()

        # Files changed
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            details["files"] = [
                f for f in result.stdout.strip().splitlines() if f.strip()
            ]

        # Diff summary (first 500 chars)
        result = subprocess.run(
            ["git", "diff", f"{commit_sha}~1..{commit_sha}", "--stat"],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            details["diff_summary"] = result.stdout.strip()[:500]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return details


def main():
    event_data = json.loads(sys.stdin.read())
    workspace = Path(os.getcwd())

    if not _load_config(workspace):
        sys.exit(0)

    # Support single commit or batch
    commits = event_data.get("commits", [])
    if not commits:
        sha = event_data.get("hash") or event_data.get("commit_sha", "")
        msg = event_data.get("message", "")
        if sha:
            commits = [{"sha": sha, "message": msg}]

    if not commits:
        sys.exit(0)

    try:
        from up.memory import MemoryManager

        manager = MemoryManager(workspace, use_vectors=False)
        indexed = 0

        for commit in commits:
            sha = commit.get("sha", "")
            message = commit.get("message", "")

            if _should_skip_commit(message):
                continue

            details = _get_commit_details(workspace, sha)
            if not details["message"] and not message:
                continue

            content = (
                f"Commit {sha[:8]}: {details['message'] or message}\n"
                f"Files: {', '.join(details['files'][:10])}\n"
                f"Diff: {details['diff_summary'][:300]}"
            )

            manager.record_learning(content)
            indexed += 1

        if indexed > 0:
            hint = {"indexed_commits": indexed}
            print(json.dumps(hint))
            print(
                f"Memory index: indexed {indexed} commit(s)",
                file=sys.stderr,
            )
            sys.exit(1)  # warn: indexed

    except Exception as e:
        print(f"auto_index error: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
