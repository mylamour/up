"""Shared test fixtures for up-cli.

Provides:
- workspace: Temporary directory with .up/ and .git/ scaffolding
- state_manager: StateManager initialized with temp workspace
- cli_runner: Click CliRunner with isolated filesystem
- mock_git: pytest-subprocess fixture pre-configured for git commands
"""

import json
import subprocess

import pytest
from click.testing import CliRunner
from pathlib import Path

from up.core.state import StateManager, UnifiedState


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace with .up/ directory.

    Returns a Path to the workspace root.
    """
    up_dir = tmp_path / ".up"
    up_dir.mkdir()
    return tmp_path


@pytest.fixture
def git_workspace(tmp_path):
    """Create a temporary workspace that is a real git repo.

    Useful for tests that need actual git operations.
    """
    # Initialize a real git repo
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        capture_output=True,
    )
    # Create initial commit
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
    )
    # Create .up/ directory
    (tmp_path / ".up").mkdir()
    return tmp_path


@pytest.fixture
def state_manager(workspace):
    """StateManager initialized with the temp workspace."""
    return StateManager(workspace)


@pytest.fixture
def state_manager_with_state(workspace):
    """StateManager with pre-populated state."""
    sm = StateManager(workspace)
    state = sm.load()
    state.loop.iteration = 5
    state.loop.phase = "EXECUTE"
    state.loop.current_task = "US-001"
    state.loop.tasks_completed = ["F-001", "F-002"]
    state.metrics.completed_tasks = 2
    state.metrics.total_tasks = 10
    sm.save()
    return sm


@pytest.fixture
def cli_runner():
    """Click CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_git_basic(fp):
    """Mock basic git commands using pytest-subprocess.

    Pre-registers common git operations. Use `fp` directly
    for custom subprocess mocking in individual tests.
    """
    fp.register(
        ["git", "rev-parse", "--git-dir"],
        stdout=".git\n",
    )
    fp.register(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        stdout="main\n",
    )
    fp.register(
        ["git", "rev-parse", "HEAD"],
        stdout="abc123def456\n",
    )
    fp.register(
        ["git", "status", "--porcelain"],
        stdout="",
    )
    return fp
