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


# Legacy branch prefix for migration
LEGACY_BRANCH_PREFIX = "worktree"


def migrate_legacy_branch(name: str, cwd: Optional[Path] = None) -> bool:
    """Migrate a legacy worktree/ branch to agent/ prefix.

    Args:
        name: Branch name without prefix
        cwd: Repository path

    Returns:
        True if migration successful or not needed
    """
    old_branch = f"{LEGACY_BRANCH_PREFIX}/{name}"
    new_branch = make_branch_name(name)

    # Check if old branch exists
    result = run_git("branch", "--list", old_branch, cwd=cwd)
    if not result.stdout.strip():
        return True  # No migration needed

    # Check if new branch already exists
    result = run_git("branch", "--list", new_branch, cwd=cwd)
    if result.stdout.strip():
        return True  # Already migrated

    # Rename branch
    result = run_git("branch", "-m", old_branch, new_branch, cwd=cwd)
    return result.returncode == 0


def preview_merge(
    source_branch: str,
    target_branch: str = "main",
    cwd: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """Preview merge to check for conflicts before actual merge.

    Args:
        source_branch: Branch to merge from
        target_branch: Branch to merge into
        cwd: Repository path

    Returns:
        Tuple of (can_merge, conflicting_files)
    """
    workspace = cwd or Path.cwd()

    # Save current branch
    original_branch = get_current_branch(workspace)

    # Checkout target branch
    result = run_git("checkout", target_branch, cwd=workspace)
    if result.returncode != 0:
        return False, [f"Cannot checkout {target_branch}"]

    # Try merge with --no-commit --no-ff
    result = run_git(
        "merge", "--no-commit", "--no-ff", source_branch,
        cwd=workspace
    )

    conflicts = []
    can_merge = result.returncode == 0

    if not can_merge:
        # Get list of conflicting files
        status_result = run_git("status", "--porcelain", cwd=workspace)
        for line in status_result.stdout.strip().split("\n"):
            if line.startswith("UU ") or line.startswith("AA "):
                conflicts.append(line[3:])

    # Always abort the merge attempt
    run_git("merge", "--abort", cwd=workspace)

    # Return to original branch
    run_git("checkout", original_branch, cwd=workspace)

    return can_merge, conflicts
