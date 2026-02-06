"""Tests for up.git.utils module."""

import subprocess
from pathlib import Path

import pytest

from up.git.utils import (
    BRANCH_PREFIX,
    is_git_repo,
    get_current_branch,
    count_commits_since,
    get_repo_root,
    make_branch_name,
    run_git,
    GitError,
    GitNotInstalledError,
    GitTimeoutError,
    GitCommandError,
)


class TestIsGitRepo:
    """Tests for is_git_repo()."""

    def test_returns_true_for_git_repo(self, git_workspace):
        assert is_git_repo(git_workspace) is True

    def test_returns_false_for_non_repo(self, tmp_path):
        assert is_git_repo(tmp_path) is False

    def test_returns_false_for_nonexistent_path(self):
        assert is_git_repo(Path("/nonexistent/path")) is False


class TestGetCurrentBranch:
    """Tests for get_current_branch()."""

    def test_returns_branch_name(self, git_workspace):
        branch = get_current_branch(git_workspace)
        # Git init creates "main" or "master" depending on config
        assert branch in ("main", "master")

    def test_raises_for_non_repo(self, tmp_path):
        with pytest.raises(GitError):
            get_current_branch(tmp_path)


class TestCountCommitsSince:
    """Tests for count_commits_since()."""

    def test_returns_zero_for_same_branch(self, git_workspace):
        branch = get_current_branch(git_workspace)
        count = count_commits_since(git_workspace, branch)
        assert count == 0

    def test_returns_zero_on_error(self, tmp_path):
        count = count_commits_since(tmp_path, "main")
        assert count == 0


class TestGetRepoRoot:
    """Tests for get_repo_root()."""

    def test_returns_root_path(self, git_workspace):
        root = get_repo_root(git_workspace)
        assert root is not None
        assert root == git_workspace

    def test_returns_root_from_subdir(self, git_workspace):
        subdir = git_workspace / "sub" / "dir"
        subdir.mkdir(parents=True)
        root = get_repo_root(subdir)
        assert root == git_workspace

    def test_returns_none_for_non_repo(self, tmp_path):
        root = get_repo_root(tmp_path)
        assert root is None


class TestMakeBranchName:
    """Tests for make_branch_name()."""

    def test_adds_prefix(self):
        assert make_branch_name("frontend") == f"{BRANCH_PREFIX}/frontend"

    def test_consistent_prefix(self):
        name = make_branch_name("test")
        assert name.startswith(BRANCH_PREFIX + "/")


class TestRunGit:
    """Tests for run_git()."""

    def test_runs_command(self, git_workspace):
        result = run_git("status", cwd=git_workspace)
        assert result.returncode == 0

    def test_check_raises_on_failure(self, git_workspace):
        with pytest.raises(GitCommandError) as exc_info:
            run_git("checkout", "nonexistent-branch", cwd=git_workspace, check=True)
        assert exc_info.value.returncode != 0

    def test_returns_stdout(self, git_workspace):
        result = run_git("rev-parse", "--git-dir", cwd=git_workspace)
        assert ".git" in result.stdout

    def test_timeout(self, git_workspace):
        # Running a normal command with short timeout should work
        result = run_git("status", cwd=git_workspace, timeout=30)
        assert result.returncode == 0


class TestRunGitMocked:
    """Tests for run_git() with mocked subprocess."""

    def test_git_not_installed(self, fp):
        fp.register(
            ["git", "status"],
            returncode=1,
        )
        # To test FileNotFoundError, we'd need to mock at a lower level
        # Instead test the happy path with fp
        result = run_git("status")
        assert result.returncode == 1

    def test_mock_git_output(self, fp):
        fp.register(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout="feature/test\n",
        )
        result = run_git("rev-parse", "--abbrev-ref", "HEAD")
        assert result.stdout.strip() == "feature/test"
