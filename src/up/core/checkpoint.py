"""Unified checkpoint management for up-cli.

This module provides a single implementation for Git checkpoints,
used by all commands that need to save/restore state:
- up save
- up reset
- up start (before AI operations)
- up agent (before merge)

Checkpoints are lightweight Git tags + metadata stored in .up/checkpoints/
"""

import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from up.core.state import get_state_manager, AgentState


@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint."""
    id: str
    commit_sha: str
    tag_name: str
    message: str
    created_at: str
    branch: str
    files_changed: int = 0
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointMetadata":
        return cls(**{
            k: v for k, v in data.items()
            if k in cls.__dataclass_fields__
        })


class CheckpointManager:
    """Manages Git checkpoints for up-cli.
    
    Provides:
    - Create checkpoints (commit + tag)
    - Restore to checkpoints
    - List available checkpoints
    - Cleanup old checkpoints
    """
    
    CHECKPOINT_DIR = ".up/checkpoints"
    TAG_PREFIX = "up-checkpoint"
    
    def __init__(self, workspace: Optional[Path] = None):
        """Initialize checkpoint manager.
        
        Args:
            workspace: Project root directory (defaults to cwd)
        """
        self.workspace = workspace or Path.cwd()
        self.checkpoint_dir = self.workspace / self.CHECKPOINT_DIR
        self.state_manager = get_state_manager(workspace)
    
    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command."""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.workspace,
            capture_output=True,
            text=True
        )
        if check and result.returncode != 0:
            raise GitError(f"Git command failed: {result.stderr}")
        return result
    
    def _is_git_repo(self) -> bool:
        """Check if workspace is a git repository."""
        result = self._run_git("rev-parse", "--git-dir", check=False)
        return result.returncode == 0
    
    def _get_current_branch(self) -> str:
        """Get current branch name."""
        result = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        return result.stdout.strip()
    
    def _get_head_sha(self) -> str:
        """Get current HEAD commit SHA."""
        result = self._run_git("rev-parse", "HEAD")
        return result.stdout.strip()
    
    def _has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        result = self._run_git("status", "--porcelain")
        return bool(result.stdout.strip())
    
    def _count_changed_files(self) -> int:
        """Count number of changed files."""
        result = self._run_git("status", "--porcelain")
        return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
    
    def save(
        self,
        message: str = None,
        task_id: str = None,
        agent_id: str = None,
        auto_commit: bool = True
    ) -> CheckpointMetadata:
        """Create a checkpoint.
        
        Args:
            message: Optional checkpoint message
            task_id: Associated task ID
            agent_id: Associated agent ID (for worktrees)
            auto_commit: Whether to commit dirty files
        
        Returns:
            CheckpointMetadata for the created checkpoint
        
        Raises:
            GitError: If git operations fail
            NotAGitRepoError: If not in a git repository
        """
        if not self._is_git_repo():
            raise NotAGitRepoError("Not a git repository")
        
        # Generate checkpoint ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        checkpoint_id = f"cp-{timestamp}"
        if task_id:
            checkpoint_id = f"cp-{task_id}-{timestamp}"
        
        # Commit dirty files if requested
        files_changed = 0
        if auto_commit and self._has_changes():
            files_changed = self._count_changed_files()
            self._run_git("add", "-A")
            commit_message = message or f"checkpoint: {checkpoint_id}"
            self._run_git("commit", "-m", commit_message)
        
        # Get commit info
        commit_sha = self._get_head_sha()
        branch = self._get_current_branch()
        
        # Create lightweight tag
        tag_name = f"{self.TAG_PREFIX}/{checkpoint_id}"
        self._run_git("tag", tag_name, check=False)  # May already exist
        
        # Create metadata
        metadata = CheckpointMetadata(
            id=checkpoint_id,
            commit_sha=commit_sha,
            tag_name=tag_name,
            message=message or f"Checkpoint before {task_id or 'AI operation'}",
            created_at=datetime.now().isoformat(),
            branch=branch,
            files_changed=files_changed,
            task_id=task_id,
            agent_id=agent_id,
        )
        
        # Save metadata
        self._save_metadata(metadata)
        
        # Update state
        self.state_manager.add_checkpoint(checkpoint_id)
        
        return metadata
    
    def restore(
        self,
        checkpoint_id: str = None,
        hard: bool = True
    ) -> CheckpointMetadata:
        """Restore to a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint to restore (defaults to last)
            hard: Whether to use hard reset (discard changes)
        
        Returns:
            CheckpointMetadata of restored checkpoint
        
        Raises:
            CheckpointNotFoundError: If checkpoint doesn't exist
        """
        if not self._is_git_repo():
            raise NotAGitRepoError("Not a git repository")
        
        # Get checkpoint
        if checkpoint_id:
            metadata = self._load_metadata(checkpoint_id)
        else:
            # Get last checkpoint
            last_id = self.state_manager.state.loop.last_checkpoint
            if not last_id:
                raise CheckpointNotFoundError("No checkpoints available")
            metadata = self._load_metadata(last_id)
        
        if metadata is None:
            # Try to restore from tag directly
            tag_name = f"{self.TAG_PREFIX}/{checkpoint_id}"
            result = self._run_git("rev-parse", tag_name, check=False)
            if result.returncode != 0:
                raise CheckpointNotFoundError(f"Checkpoint not found: {checkpoint_id}")
            
            commit_sha = result.stdout.strip()
            metadata = CheckpointMetadata(
                id=checkpoint_id,
                commit_sha=commit_sha,
                tag_name=tag_name,
                message="Restored from tag",
                created_at=datetime.now().isoformat(),
                branch=self._get_current_branch(),
            )
        
        # Perform reset
        reset_type = "--hard" if hard else "--soft"
        self._run_git("reset", reset_type, metadata.commit_sha)
        
        # Record rollback
        self.state_manager.record_rollback()
        
        return metadata
    
    def list_checkpoints(self, limit: int = 20) -> List[CheckpointMetadata]:
        """List available checkpoints.
        
        Args:
            limit: Maximum number to return
        
        Returns:
            List of checkpoint metadata, newest first
        """
        checkpoints = []
        
        # Get from state
        checkpoint_ids = self.state_manager.state.checkpoints[-limit:]
        checkpoint_ids.reverse()  # Newest first
        
        for cp_id in checkpoint_ids:
            metadata = self._load_metadata(cp_id)
            if metadata:
                checkpoints.append(metadata)
        
        return checkpoints
    
    def get_last_checkpoint(self) -> Optional[CheckpointMetadata]:
        """Get the last checkpoint."""
        last_id = self.state_manager.state.loop.last_checkpoint
        if last_id:
            return self._load_metadata(last_id)
        return None
    
    def cleanup(self, keep: int = 20) -> int:
        """Remove old checkpoints.
        
        Args:
            keep: Number of recent checkpoints to keep
        
        Returns:
            Number of checkpoints removed
        """
        all_checkpoints = self.state_manager.state.checkpoints
        if len(all_checkpoints) <= keep:
            return 0
        
        to_remove = all_checkpoints[:-keep]
        removed = 0
        
        for cp_id in to_remove:
            # Remove tag
            tag_name = f"{self.TAG_PREFIX}/{cp_id}"
            self._run_git("tag", "-d", tag_name, check=False)
            
            # Remove metadata file
            metadata_file = self.checkpoint_dir / f"{cp_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            removed += 1
        
        # Update state
        self.state_manager.state.checkpoints = all_checkpoints[-keep:]
        self.state_manager.save()
        
        return removed
    
    def diff_from_checkpoint(self, checkpoint_id: str = None) -> str:
        """Get diff from checkpoint to current state.
        
        Args:
            checkpoint_id: Checkpoint to diff from (defaults to last)
        
        Returns:
            Diff output as string
        """
        if not checkpoint_id:
            checkpoint_id = self.state_manager.state.loop.last_checkpoint
        
        if not checkpoint_id:
            # Diff from HEAD
            result = self._run_git("diff", "HEAD")
            return result.stdout
        
        tag_name = f"{self.TAG_PREFIX}/{checkpoint_id}"
        result = self._run_git("diff", tag_name, "HEAD", check=False)
        
        if result.returncode != 0:
            # Tag might not exist, try commit SHA from metadata
            metadata = self._load_metadata(checkpoint_id)
            if metadata:
                result = self._run_git("diff", metadata.commit_sha, "HEAD")
                return result.stdout
            return ""
        
        return result.stdout
    
    def diff_stats(self, checkpoint_id: str = None) -> dict:
        """Get diff statistics from checkpoint.
        
        Returns:
            Dict with files, insertions, deletions
        """
        if not checkpoint_id:
            checkpoint_id = self.state_manager.state.loop.last_checkpoint
        
        if not checkpoint_id:
            result = self._run_git("diff", "--stat", "HEAD")
        else:
            tag_name = f"{self.TAG_PREFIX}/{checkpoint_id}"
            result = self._run_git("diff", "--stat", tag_name, "HEAD", check=False)
            if result.returncode != 0:
                return {"files": 0, "insertions": 0, "deletions": 0}
        
        # Parse stat output
        lines = result.stdout.strip().split("\n")
        if not lines or not lines[-1]:
            return {"files": 0, "insertions": 0, "deletions": 0}
        
        # Last line has summary: "X files changed, Y insertions(+), Z deletions(-)"
        import re
        summary = lines[-1] if lines else ""
        
        files = 0
        insertions = 0
        deletions = 0
        
        files_match = re.search(r"(\d+) files? changed", summary)
        if files_match:
            files = int(files_match.group(1))
        
        ins_match = re.search(r"(\d+) insertions?\(\+\)", summary)
        if ins_match:
            insertions = int(ins_match.group(1))
        
        del_match = re.search(r"(\d+) deletions?\(-\)", summary)
        if del_match:
            deletions = int(del_match.group(1))
        
        return {
            "files": files,
            "insertions": insertions,
            "deletions": deletions,
        }
    
    def _save_metadata(self, metadata: CheckpointMetadata) -> None:
        """Save checkpoint metadata to file."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = self.checkpoint_dir / f"{metadata.id}.json"
        metadata_file.write_text(json.dumps(metadata.to_dict(), indent=2))
    
    def _load_metadata(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        """Load checkpoint metadata from file."""
        metadata_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if not metadata_file.exists():
            return None
        
        try:
            data = json.loads(metadata_file.read_text())
            return CheckpointMetadata.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None


# =============================================================================
# Exceptions
# =============================================================================

class CheckpointError(Exception):
    """Base exception for checkpoint operations."""
    pass


class GitError(CheckpointError):
    """Git operation failed."""
    pass


class NotAGitRepoError(CheckpointError):
    """Not in a git repository."""
    pass


class CheckpointNotFoundError(CheckpointError):
    """Checkpoint not found."""
    pass


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager(workspace: Optional[Path] = None) -> CheckpointManager:
    """Get or create the default checkpoint manager."""
    global _default_manager
    if _default_manager is None or (workspace and _default_manager.workspace != workspace):
        _default_manager = CheckpointManager(workspace)
    return _default_manager


def save_checkpoint(
    message: str = None,
    task_id: str = None,
    workspace: Optional[Path] = None
) -> CheckpointMetadata:
    """Create a checkpoint (convenience function)."""
    return get_checkpoint_manager(workspace).save(message=message, task_id=task_id)


def restore_checkpoint(
    checkpoint_id: str = None,
    workspace: Optional[Path] = None
) -> CheckpointMetadata:
    """Restore to a checkpoint (convenience function)."""
    return get_checkpoint_manager(workspace).restore(checkpoint_id=checkpoint_id)


def get_diff(
    checkpoint_id: str = None,
    workspace: Optional[Path] = None
) -> str:
    """Get diff from checkpoint (convenience function)."""
    return get_checkpoint_manager(workspace).diff_from_checkpoint(checkpoint_id)
