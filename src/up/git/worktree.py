"""Git worktree management for parallel task execution.

This module provides utilities for creating, managing, and merging
Git worktrees - enabling parallel AI task execution.
"""

import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from up.core.state import AgentState, get_state_manager
from up.git.utils import (
    make_branch_name,
)

# For backwards compatibility during the migration
WorktreeState = AgentState

def _get_workspace_for_worktree(worktree_path: Path) -> Path:
    """Get the root workspace path from a worktree path.
    
    Since worktree_path is typically something like '.worktrees/US-001',
    its parent's parent is the workspace root.
    """
    return worktree_path.absolute().parent.parent

def save_worktree_state(state: AgentState, worktree_path: Path):
    """Save state to unified state manager instead of local file."""
    workspace = _get_workspace_for_worktree(worktree_path)
    sm = get_state_manager(workspace)
    sm.add_agent(state)

def load_worktree_state(worktree_path: Path, task_id: str | None = None) -> AgentState:
    """Load state from unified state manager."""
    workspace = _get_workspace_for_worktree(worktree_path)
    sm = get_state_manager(workspace)

    # Extract task_id from path if not provided
    if not task_id:
        task_id = worktree_path.name

    if task_id in sm.state.agents:
        return sm.state.agents[task_id]

    raise FileNotFoundError(f"No state found for agent {task_id} in unified state")

def _monkeypatch_agent_state():
    """Add load/save methods to AgentState for backward compatibility."""
    if not hasattr(AgentState, 'save'):
        AgentState.save = save_worktree_state
    if not hasattr(AgentState, 'load'):
        AgentState.load = classmethod(lambda cls, path: load_worktree_state(path))

_monkeypatch_agent_state()


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
    message: str = None,
    cli_name: str = None,
    workspace: Path = None
) -> bool:
    """Merge worktree changes into target branch, with AI conflict resolution.
    
    Args:
        task_id: Task identifier
        target_branch: Branch to merge into
        squash: Whether to squash commits
        message: Custom commit message
        cli_name: AI CLI to use for conflict resolution
        workspace: Project root directory
    
    Returns:
        True if merge successful
    """
    branch = make_branch_name(task_id)
    worktree_path = Path(f".worktrees/{task_id}")
    workspace_dir = workspace or Path.cwd()

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
        cwd=workspace_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return False

    # Merge
    merge_cmd = ["git", "merge", "--squash", branch] if squash else ["git", "merge", branch, "-m", commit_message]

    result = subprocess.run(
        merge_cmd,
        cwd=workspace_dir,
        capture_output=True,
        text=True
    )

    # If merge fails, attempt AI conflict resolution
    if result.returncode != 0:
        if not cli_name:
            # Revert the failed merge
            subprocess.run(["git", "merge", "--abort"], cwd=workspace_dir, capture_output=True)
            return False

        # Get conflicted files
        diff_res = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=workspace_dir,
            capture_output=True,
            text=True
        )
        conflicted_files = [f for f in diff_res.stdout.strip().split("\n") if f]

        if not conflicted_files:
            subprocess.run(["git", "merge", "--abort"], cwd=workspace_dir, capture_output=True)
            return False

        from up.ai_cli import run_ai_prompt

        for file in conflicted_files:
            file_path = workspace_dir / file
            if not file_path.exists():
                continue

            content = file_path.read_text()
            prompt = (
                f"Please resolve the Git merge conflicts in this file. "
                f"Output ONLY the fully resolved file content, with no markdown formatting, "
                f"no explanations, and no original conflict markers.\n\nFile: {file}\n\n"
                f"```\n{content}\n```"
            )

            resolved = run_ai_prompt(workspace_dir, prompt, cli_name, timeout=300, silent=True)
            if not resolved or "<<<<<<< HEAD" in resolved:
                # Resolution failed
                subprocess.run(["git", "merge", "--abort"], cwd=workspace_dir, capture_output=True)
                return False

            # Clean up markdown block if the AI included it
            if resolved.startswith("```"):
                lines = resolved.split("\n")
                if len(lines) >= 2 and lines[-1].startswith("```"):
                    resolved = "\n".join(lines[1:-1])

            file_path.write_text(resolved)
            subprocess.run(["git", "add", file], cwd=workspace_dir)

    # Commit the changes (always needed for squash, or if we resolved conflicts)
    if squash or result.returncode != 0:
        commit_res = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=workspace_dir,
            capture_output=True,
            text=True
        )
        if commit_res.returncode != 0:
            # Commit failed (e.g. no changes)
            return False

    # Cleanup worktree
    remove_worktree(task_id)

    return True


# Standard checkpoint tag prefix (matches checkpoint.py)
CHECKPOINT_TAG_PREFIX = "up-checkpoint"


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

    # Create lightweight tag with standard prefix
    subprocess.run(
        ["git", "tag", f"{CHECKPOINT_TAG_PREFIX}/{checkpoint_name}"],
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
    target = f"{CHECKPOINT_TAG_PREFIX}/{checkpoint}" if checkpoint else "HEAD"

    subprocess.run(
        ["git", "reset", "--hard", target],
        cwd=worktree_path,
        capture_output=True
    )
