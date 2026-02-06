"""Tests for up.core.checkpoint module."""

import subprocess
from pathlib import Path

import pytest

from up.core.checkpoint import (
    CheckpointManager,
    CheckpointMetadata,
    CheckpointNotFoundError,
    NotAGitRepoError,
)


class TestCheckpointMetadata:
    """Tests for CheckpointMetadata dataclass."""

    def test_to_dict_roundtrip(self):
        meta = CheckpointMetadata(
            id="cp-001",
            commit_sha="abc123",
            tag_name="up-checkpoint/cp-001",
            message="Test checkpoint",
            created_at="2026-02-06T12:00:00",
            branch="main",
            files_changed=3,
            task_id="US-001",
        )
        data = meta.to_dict()
        restored = CheckpointMetadata.from_dict(data)
        assert restored.id == "cp-001"
        assert restored.task_id == "US-001"
        assert restored.files_changed == 3


class TestCheckpointManager:
    """Tests for CheckpointManager (uses real git repo).

    Note: CheckpointManager.__init__ takes only workspace (Optional[Path]).
    It creates its own StateManager internally via get_state_manager().
    """

    def test_save_clean_workdir(self, git_workspace):
        """Save with no dirty files still creates a checkpoint."""
        mgr = CheckpointManager(git_workspace)

        meta = mgr.save(message="Test checkpoint")
        assert meta.id.startswith("cp-")
        assert meta.commit_sha
        assert meta.files_changed == 0

    def test_save_with_dirty_files(self, git_workspace):
        """Save auto-commits dirty files."""
        test_file = git_workspace / "new_file.txt"
        test_file.write_text("hello world")

        mgr = CheckpointManager(git_workspace)
        meta = mgr.save(message="Before AI work")
        assert meta.files_changed > 0

    def test_save_records_in_state(self, git_workspace):
        mgr = CheckpointManager(git_workspace)
        meta = mgr.save()
        assert meta.id in mgr.state_manager.state.checkpoints
        assert mgr.state_manager.state.loop.last_checkpoint == meta.id

    def test_save_with_task_id(self, git_workspace):
        mgr = CheckpointManager(git_workspace)
        meta = mgr.save(task_id="US-001")
        assert "US-001" in meta.id

    def test_restore_to_last(self, git_workspace):
        mgr = CheckpointManager(git_workspace)

        # Save checkpoint
        meta = mgr.save(message="checkpoint 1")

        # Make more changes
        test_file = git_workspace / "extra.txt"
        test_file.write_text("this should be gone after restore")
        subprocess.run(["git", "add", "-A"], cwd=git_workspace, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "extra commit"],
            cwd=git_workspace,
            capture_output=True,
        )

        # Restore
        restored = mgr.restore()
        assert restored.id == meta.id

    def test_restore_none_checkpoint_id_raises(self, git_workspace):
        mgr = CheckpointManager(git_workspace)

        with pytest.raises(CheckpointNotFoundError, match="No checkpoint"):
            mgr.restore(checkpoint_id=None)

    def test_restore_nonexistent_raises(self, git_workspace):
        mgr = CheckpointManager(git_workspace)
        mgr.state_manager.state.loop.last_checkpoint = None

        with pytest.raises(CheckpointNotFoundError):
            mgr.restore()

    def test_not_git_repo_raises(self, workspace):
        """Operations outside a git repo should raise."""
        mgr = CheckpointManager(workspace)

        with pytest.raises(NotAGitRepoError):
            mgr.save()

    def test_list_checkpoints(self, git_workspace):
        mgr = CheckpointManager(git_workspace)

        mgr.save(message="first")
        mgr.save(message="second")

        checkpoints = mgr.list_checkpoints()
        assert len(checkpoints) >= 2
