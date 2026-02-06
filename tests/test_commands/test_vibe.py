"""Tests for up.commands.vibe (save/reset/diff) commands."""

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from up.commands.vibe import save_cmd, reset_cmd, diff_cmd


@pytest.fixture
def vibe_workspace(git_workspace):
    """Git workspace suitable for vibe command testing."""
    return git_workspace


class TestSaveCommand:
    """Tests for `up save` command."""

    def test_save_clean_workdir(self, vibe_workspace):
        runner = CliRunner()
        result = runner.invoke(save_cmd, [], catch_exceptions=False, obj={
        })
        # Should succeed (checkpoints even clean states)
        # Note: Click commands use cwd, so we need to chdir
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(vibe_workspace)
            result = runner.invoke(save_cmd, [])
            assert result.exit_code == 0
            assert "Checkpoint created" in result.output or "No changes" in result.output
        finally:
            os.chdir(old_cwd)

    def test_save_with_dirty_files(self, vibe_workspace):
        # Create dirty file
        (vibe_workspace / "test.txt").write_text("hello")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(vibe_workspace)
            runner = CliRunner()
            result = runner.invoke(save_cmd, ["before AI work"])
            assert result.exit_code == 0
            assert "Checkpoint created" in result.output
        finally:
            os.chdir(old_cwd)

    def test_save_with_task_id(self, vibe_workspace):
        (vibe_workspace / "test.txt").write_text("hello")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(vibe_workspace)
            runner = CliRunner()
            result = runner.invoke(save_cmd, ["-t", "US-001"])
            assert result.exit_code == 0
        finally:
            os.chdir(old_cwd)

    def test_save_quiet_mode(self, vibe_workspace):
        (vibe_workspace / "test.txt").write_text("hello")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(vibe_workspace)
            runner = CliRunner()
            result = runner.invoke(save_cmd, ["-q"])
            assert result.exit_code == 0
            # Quiet mode outputs only the checkpoint ID
            assert "cp-" in result.output
        finally:
            os.chdir(old_cwd)

    def test_save_not_git_repo(self, tmp_path):
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(save_cmd, [])
            assert result.exit_code != 0
            assert "Not a git repository" in result.output
        finally:
            os.chdir(old_cwd)


class TestResetCommand:
    """Tests for `up reset` command."""

    def test_reset_list(self, vibe_workspace):
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(vibe_workspace)
            runner = CliRunner()
            # Create a checkpoint first
            runner.invoke(save_cmd, ["test checkpoint"])
            # Then list
            result = runner.invoke(reset_cmd, ["--list"])
            assert result.exit_code == 0
        finally:
            os.chdir(old_cwd)

    def test_reset_no_checkpoints(self, vibe_workspace):
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(vibe_workspace)
            runner = CliRunner()
            result = runner.invoke(reset_cmd, ["-y"])
            # Should fail gracefully - no checkpoints available
            assert result.exit_code != 0 or "No checkpoint" in result.output
        finally:
            os.chdir(old_cwd)

    def test_reset_not_git_repo(self, tmp_path):
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()
            result = runner.invoke(reset_cmd, ["-y"])
            assert result.exit_code != 0
        finally:
            os.chdir(old_cwd)


class TestDiffCommand:
    """Tests for `up diff` command."""

    def test_diff_no_changes(self, vibe_workspace):
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(vibe_workspace)
            runner = CliRunner()
            result = runner.invoke(diff_cmd, [])
            assert result.exit_code == 0
        finally:
            os.chdir(old_cwd)

    def test_diff_with_changes(self, vibe_workspace):
        # Make uncommitted changes
        (vibe_workspace / "README.md").write_text("# Modified\n")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(vibe_workspace)
            runner = CliRunner()
            result = runner.invoke(diff_cmd, [])
            assert result.exit_code == 0
        finally:
            os.chdir(old_cwd)
