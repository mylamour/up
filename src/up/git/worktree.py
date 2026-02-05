"""Git worktree management for parallel task execution.

This module provides utilities for creating, managing, and merging
Git worktrees - enabling parallel AI task execution.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from up.git.utils import (
    is_git_repo,
    get_current_branch,
    count_commits_since,
    make_branch_name,
    run_git,
    BRANCH_PREFIX,
)


@dataclass
class WorktreeState:
    """State of a task worktree."""
    task_id: str
    task_title: str
    branch: str
    path: str
    status: str = "created"  # created, executing, verifying, passed, failed, merged
    phase: str = "INIT"
    started: str = field(default_factory=lambda: datetime.now().isoformat())
    checkpoints: list = field(default_factory=list)
    ai_invocations: list = field(default_factory=list)
    verification: dict = field(default_factory=lambda: {
        "tests_passed": None,
        "lint_passed": None,
        "type_check_passed": None
    })
    error: Optional[str] = None
    
    def save(self, worktree_path: Path):
        """Save state to worktree."""
        state_file = worktree_path / ".agent_state.json"
        state_file.write_text(json.dumps(asdict(self), indent=2))
    
    @classmethod
    def load(cls, worktree_path: Path) -> "WorktreeState":
        """Load state from worktree."""
        state_file = worktree_path / ".agent_state.json"
        if state_file.exists():
            data = json.loads(state_file.read_text())
            return cls(**data)
        raise FileNotFoundError(f"No state file in {worktree_path}")


def create_worktree(
    task_id: str,
    task_title: str = "",
    base_branch: str = "main"
) -> tuple[Path, WorktreeState]:
    """Create an isolated worktree for a task.
    
    Args:
        task_id: Unique task identifier (e.g., "US-004")
        task_title: Human-readable task title
        base_branch: Branch to base the worktree on
    
    Returns:
        Tuple of (worktree_path, state)
    """
    branch = make_branch_name(task_id)
    worktree_dir = Path(".worktrees")
    worktree_path = worktree_dir / task_id
    
    # Ensure .worktrees directory exists
    worktree_dir.mkdir(exist_ok=True)
    
    # Check if worktree already exists
    if worktree_path.exists():
        try:
            state = WorktreeState.load(worktree_path)
            return worktree_path, state
        except FileNotFoundError:
            # Corrupt state, remove and recreate
            remove_worktree(task_id)
    
    # Create branch and worktree
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), base_branch],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        # Branch might already exist, try without -b
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")
    
    # Copy environment files
    env_files = [".env", ".env.local", ".env.development"]
    for env_file in env_files:
        if Path(env_file).exists():
            shutil.copy(env_file, worktree_path / env_file)
    
    # Initialize state
    state = WorktreeState(
        task_id=task_id,
        task_title=task_title or task_id,
        branch=branch,
        path=str(worktree_path),
        status="created"
    )
    state.save(worktree_path)
    
    return worktree_path, state


def remove_worktree(task_id: str, force: bool = False):
    """Remove a worktree and its branch.
    
    Args:
        task_id: Task identifier
        force: Force removal even if changes exist
    """
    worktree_path = Path(f".worktrees/{task_id}")
    branch = make_branch_name(task_id)
    
    # Remove worktree
    if worktree_path.exists():
        cmd = ["git", "worktree", "remove", str(worktree_path)]
        if force:
            cmd.append("--force")
        subprocess.run(cmd, capture_output=True)
    
    # Delete branch
    subprocess.run(
        ["git", "branch", "-D" if force else "-d", branch],
        capture_output=True
    )


def list_worktrees() -> list[dict]:
    """List all active worktrees with their state.
    
    Returns:
        List of worktree info dicts
    """
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True
    )
    
    worktrees = []
    current = {}
    
    for line in result.stdout.strip().split("\n"):
        if not line:
            if current and ".worktrees" in current.get("worktree", ""):
                # Load state if available
                wt_path = Path(current["worktree"])
                try:
                    state = WorktreeState.load(wt_path)
                    current["state"] = asdict(state)
                except FileNotFoundError:
                    current["state"] = None
                worktrees.append(current)
            current = {}
        elif line.startswith("worktree "):
            current["worktree"] = line[9:]
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:]
    
    # Don't forget last entry
    if current and ".worktrees" in current.get("worktree", ""):
        wt_path = Path(current["worktree"])
        try:
            state = WorktreeState.load(wt_path)
            current["state"] = asdict(state)
        except FileNotFoundError:
            current["state"] = None
        worktrees.append(current)
    
    return worktrees


def merge_worktree(
    task_id: str,
    target_branch: str = "main",
    squash: bool = True,
    message: str = None
) -> bool:
    """Merge worktree changes into target branch.
    
    Args:
        task_id: Task identifier
        target_branch: Branch to merge into
        squash: Whether to squash commits
        message: Custom commit message
    
    Returns:
        True if merge successful
    """
    branch = make_branch_name(task_id)
    worktree_path = Path(f".worktrees/{task_id}")
    
    # Load state for commit message
    try:
        state = WorktreeState.load(worktree_path)
        default_message = f"feat({task_id}): {state.task_title}"
    except FileNotFoundError:
        default_message = f"feat({task_id}): Implement task"
    
    commit_message = message or default_message
    
    # Checkout target branch
    result = subprocess.run(
        ["git", "checkout", target_branch],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return False
    
    # Merge
    if squash:
        # Squash merge - combines all commits into staging
        result = subprocess.run(
            ["git", "merge", "--squash", branch],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False
        
        # Commit the squashed changes
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True,
            text=True
        )
    else:
        # Regular merge
        result = subprocess.run(
            ["git", "merge", branch, "-m", commit_message],
            capture_output=True,
            text=True
        )
    
    if result.returncode != 0:
        return False
    
    # Cleanup worktree
    remove_worktree(task_id)
    
    return True


def create_checkpoint(worktree_path: Path, name: str = None) -> str:
    """Create a checkpoint (commit + tag) in a worktree.
    
    Args:
        worktree_path: Path to worktree
        name: Optional checkpoint name
    
    Returns:
        Checkpoint identifier
    """
    checkpoint_name = name or f"cp-{datetime.now().strftime('%H%M%S')}"
    
    # Stage all changes
    subprocess.run(
        ["git", "add", "-A"],
        cwd=worktree_path,
        capture_output=True
    )
    
    # Check if there are changes to commit
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    
    if result.stdout.strip():
        # Commit changes
        subprocess.run(
            ["git", "commit", "-m", f"checkpoint: {checkpoint_name}"],
            cwd=worktree_path,
            capture_output=True
        )
    
    # Create lightweight tag
    subprocess.run(
        ["git", "tag", f"vibe/{checkpoint_name}"],
        cwd=worktree_path,
        capture_output=True
    )
    
    return checkpoint_name


def reset_to_checkpoint(worktree_path: Path, checkpoint: str = None):
    """Reset worktree to a checkpoint.
    
    Args:
        worktree_path: Path to worktree
        checkpoint: Checkpoint name (defaults to HEAD)
    """
    target = f"vibe/{checkpoint}" if checkpoint else "HEAD"
    
    subprocess.run(
        ["git", "reset", "--hard", target],
        cwd=worktree_path,
        capture_output=True
    )
