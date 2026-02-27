"""Tests for up.core.loop LoopOrchestrator."""

import json
from pathlib import Path

import pytest

from up.core.loop import (
    LoopOrchestrator,
    TaskInfo,
    BeginTaskResult,
    TaskPrompts,
    FailureResult,
    SuccessResult,
    CircuitBreakerStatus,
    VerificationCommands,
)


@pytest.fixture
def workspace(tmp_path):
    """Create a minimal workspace with .up dir and config."""
    up_dir = tmp_path / ".up"
    up_dir.mkdir()
    (up_dir / "config.json").write_text(json.dumps({
        "doom_loop_threshold": 3,
        "circuit_breaker_failure_threshold": 3,
        "circuit_breaker_cooldown_minutes": 5,
    }))
    # Init git repo for checkpoint support
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    (tmp_path / "dummy.txt").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
    return tmp_path


@pytest.fixture
def orch(workspace):
    """Create a LoopOrchestrator for the test workspace."""
    # Reset the global state manager cache
    import up.core.state as state_mod
    state_mod._default_manager = None
    return LoopOrchestrator(workspace)


class TestTaskInfo:
    """Tests for TaskInfo dataclass."""

    def test_from_dict(self):
        data = {
            "id": "US-001",
            "title": "Add login",
            "description": "Implement login page",
            "priority": "high",
            "acceptanceCriteria": ["Has form", "Validates input"],
            "files": ["src/login.py"],
        }
        task = TaskInfo.from_dict(data)
        assert task.id == "US-001"
        assert task.title == "Add login"
        assert task.priority == "high"
        assert len(task.acceptance_criteria) == 2

    def test_from_dict_minimal(self):
        task = TaskInfo.from_dict({"id": "T1"})
        assert task.id == "T1"
        assert task.title == ""
        assert task.acceptance_criteria == []


class TestCircuitBreaker:
    """Tests for circuit breaker via orchestrator."""

    def test_initial_state_allows_execution(self, orch):
        status = orch.check_circuit_breaker()
        assert status.can_execute is True
        assert status.state == "CLOSED"

    def test_opens_after_threshold(self, orch):
        task = TaskInfo(id="T1", title="test")
        for _ in range(3):
            orch.record_failure(task, error="fail", rollback=False)
        status = orch.check_circuit_breaker()
        assert status.can_execute is False
        assert status.state == "OPEN"

    def test_reset_circuit_breaker(self, orch):
        task = TaskInfo(id="T1", title="test")
        for _ in range(3):
            orch.record_failure(task, error="fail", rollback=False)
        orch.reset_circuit_breaker()
        status = orch.check_circuit_breaker()
        assert status.can_execute is True
        assert status.state == "CLOSED"


class TestTaskLifecycle:
    """Tests for begin_task / record_success / record_failure."""

    def test_begin_task_creates_checkpoint(self, orch):
        task = TaskInfo(id="US-001", title="Add feature")
        result = orch.begin_task(task)
        assert result.success is True
        assert result.checkpoint_id is not None
        assert "US-001" in result.checkpoint_id

    def test_begin_task_updates_state(self, orch):
        task = TaskInfo(id="US-001", title="Add feature")
        orch.begin_task(task)
        status = orch.get_status()
        assert status["current_task"] == "US-001"
        assert status["phase"] == "EXECUTE"
        assert status["iteration"] == 1

    def test_record_success_marks_complete(self, orch):
        task = TaskInfo(id="US-001", title="Add feature")
        orch.begin_task(task)
        result = orch.record_success(task)
        assert result.task_id == "US-001"
        assert "feat(US-001)" in result.commit_message
        status = orch.get_status()
        assert "US-001" in status["tasks_completed"]

    def test_record_failure_returns_result(self, orch):
        task = TaskInfo(id="US-001", title="Add feature")
        orch.begin_task(task)
        result = orch.record_failure(task, error="tests failed", rollback=False)
        assert result.consecutive_failures == 1
        assert result.circuit_open is False
        status = orch.get_status()
        assert "US-001" in status["tasks_failed"]


class TestTaskSource:
    """Tests for task source discovery."""

    def test_find_prd_json(self, orch, workspace):
        (workspace / "prd.json").write_text(json.dumps({
            "projectName": "test",
            "userStories": [],
        }))
        assert orch.find_task_source() == "prd.json"

    def test_find_todo_md(self, orch, workspace):
        (workspace / "TODO.md").write_text("- [ ] Do something")
        assert orch.find_task_source() == "TODO.md"

    def test_no_source_returns_none(self, orch):
        assert orch.find_task_source() is None

    def test_explicit_path_takes_priority(self, orch):
        assert orch.find_task_source("custom.json") == "custom.json"


class TestVerificationCommands:
    """Tests for verification command generation."""

    def test_returns_all_commands(self, orch):
        cmds = orch.get_verification_commands()
        assert "pytest" in cmds.test_cmd
        assert "ruff" in cmds.lint_cmd
        assert "mypy" in cmds.type_check_cmd


class TestStatus:
    """Tests for get_status and set_idle."""

    def test_initial_status(self, orch):
        status = orch.get_status()
        assert status["iteration"] == 0
        assert status["phase"] == "IDLE"
        assert status["current_task"] is None
        assert status["tasks_completed"] == []

    def test_status_after_begin(self, orch):
        task = TaskInfo(id="US-001", title="Test")
        orch.begin_task(task)
        status = orch.get_status()
        assert status["iteration"] == 1
        assert status["current_task"] == "US-001"

    def test_set_idle(self, orch):
        task = TaskInfo(id="US-001", title="Test")
        orch.begin_task(task)
        orch.set_idle()
        status = orch.get_status()
        assert status["phase"] == "IDLE"
        assert status["current_task"] is None

    def test_mark_interrupted(self, orch):
        task = TaskInfo(id="US-001", title="Test")
        orch.begin_task(task)
        orch.mark_interrupted()
        status = orch.get_status()
        assert status["phase"] == "INTERRUPTED"
