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
from up.core.state import StateManager


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
    """Tests for CheckpointManager (uses real git repo)."""

    def test_save_clean_workdir(self, git_workspace):
        """Save with no dirty files still creates a checkpoint."""
        sm = StateManager(git_workspace)
        sm.load()
        mgr = CheckpointManager(git_workspace, sm)

        meta = mgr.save(message="Test checkpoint")
        assert meta.id.startswith("cp-")
        assert meta.commit_sha
        assert meta.branch == "main"
        assert meta.files_changed == 0

    def test_save_with_dirty_files(self, git_workspace):
        """Save auto-commits dirty files."""
        # Create a dirty file
        test_file = git_workspace / "new_file.txt"
        test_file.write_text("hello world")

        sm = StateManager(git_workspace)
        sm.load()
        mgr = CheckpointManager(git_workspace, sm)

        meta = mgr.save(message="Before AI work")
        assert meta.files_changed > 0

    def test_save_records_in_state(self, git_workspace):
        sm = StateManager(git_workspace)
        sm.load()
        mgr = CheckpointManager(git_workspace, sm)

        meta = mgr.save()
        assert meta.id in sm.state.checkpoints
        assert sm.state.loop.last_checkpoint == meta.id

    def test_save_with_task_id(self, git_workspace):
        sm = StateManager(git_workspace)
        sm.load()
        mgr = CheckpointManager(git_workspace, sm)

        meta = mgr.save(task_id="US-001")
        assert "US-001" in meta.id

    def test_restore_to_last(self, git_workspace):
        sm = StateManager(git_workspace)
        sm.load()
        mgr = CheckpointManager(git_workspace, sm)

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
        sm = StateManager(git_workspace)
        sm.load()
        mgr = CheckpointManager(git_workspace, sm)

        with pytest.raises(CheckpointNotFoundError, match="No checkpoint"):
            mgr.restore(checkpoint_id=None)

    def test_restore_nonexistent_raises(self, git_workspace):
        sm = StateManager(git_workspace)
        sm.load()
        sm.state.loop.last_checkpoint = None
        mgr = CheckpointManager(git_workspace, sm)

        with pytest.raises(CheckpointNotFoundError):
            mgr.restore()

    def test_not_git_repo_raises(self, workspace):
        """Operations outside a git repo should raise."""
        sm = StateManager(workspace)
        sm.load()
        mgr = CheckpointManager(workspace, sm)

        with pytest.raises(NotAGitRepoError):
            mgr.save()

    def test_list_checkpoints(self, git_workspace):
        sm = StateManager(git_workspace)
        sm.load()
        mgr = CheckpointManager(git_workspace, sm)

        mgr.save(message="first")
        mgr.save(message="second")

        checkpoints = mgr.list()
        assert len(checkpoints) >= 2
