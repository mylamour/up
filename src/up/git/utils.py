"""Shared Git utilities for up-cli.

This module provides common Git operations used across the codebase,
eliminating duplication between worktree.py and agent.py.
"""

import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

# Standard branch prefix for all agent/worktree operations
BRANCH_PREFIX = "agent"


def is_git_repo(path: Optional[Path] = None) -> bool:
    """Check if path is inside a Git repository.

    Args:
        path: Directory to check (defaults to cwd)

    Returns:
        True if path is in a Git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path or Path.cwd(),
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def get_current_branch(path: Optional[Path] = None) -> str:
    """Get current Git branch name.

    Args:
        path: Repository path (defaults to cwd)

    Returns:
        Current branch name
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=path or Path.cwd(),
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def count_commits_since(path: Path, base: str = "main") -> int:
    """Count commits since branching from base.

    Args:
        path: Repository path
        base: Base branch to compare against

    Returns:
        Number of commits since base
    """
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{base}..HEAD"],
        cwd=path,
        capture_output=True,
        text=True
    )
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def get_repo_root(path: Optional[Path] = None) -> Optional[Path]:
    """Get the root directory of the Git repository.

    Args:
        path: Starting path (defaults to cwd)

    Returns:
        Repository root path or None if not in a repo
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path or Path.cwd(),
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return None


def make_branch_name(name: str) -> str:
    """Create a standardized branch name.

    Args:
        name: Agent or task name

    Returns:
        Branch name with standard prefix
    """
    return f"{BRANCH_PREFIX}/{name}"


def run_git(*args, cwd: Optional[Path] = None, check: bool = False) -> subprocess.CompletedProcess:
    """Run a git command with standard options.

    Args:
        *args: Git command arguments
        cwd: Working directory
        check: Raise exception on failure

    Returns:
        CompletedProcess result
    """
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd or Path.cwd(),
        capture_output=True,
        text=True
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            ["git"] + list(args),
            result.stdout,
            result.stderr
        )
    return result
