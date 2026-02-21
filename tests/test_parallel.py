"""Tests for parallel execution module."""

import json
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from up.parallel import (
    ParallelExecutionManager,
    TaskResult,
    get_pending_tasks,
    mark_task_complete_in_prd,
    _build_task_prompt,
)
from up.core.state import StateManager


@pytest.fixture
def prd_file(tmp_path):
    """Create a temporary PRD file with test tasks."""
    prd = {
        "project": "Test",
        "userStories": [
            {"id": "US-001", "title": "Task 1", "passes": True},
            {"id": "US-002", "title": "Task 2", "passes": False},
            {"id": "US-003", "title": "Task 3", "passes": False},
        ],
    }
    path = tmp_path / "prd.json"
    path.write_text(json.dumps(prd))
    return path


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_successful_result(self):
        r = TaskResult(task_id="US-001", success=True, phase="verified", duration_seconds=5.0)
        assert r.success
        assert r.error is None

    def test_failed_result(self):
        r = TaskResult(
            task_id="US-001",
            success=False,
            phase="failed",
            duration_seconds=1.0,
            error="AI failed",
        )
        assert not r.success
        assert r.error == "AI failed"


class TestGetPendingTasks:
    """Tests for get_pending_tasks."""

    def test_returns_pending_tasks(self, prd_file):
        tasks = get_pending_tasks(prd_file)
        assert len(tasks) == 2
        assert tasks[0]["id"] == "US-002"
        assert tasks[1]["id"] == "US-003"

    def test_respects_limit(self, prd_file):
        tasks = get_pending_tasks(prd_file, limit=1)
        assert len(tasks) == 1
        assert tasks[0]["id"] == "US-002"

    def test_returns_empty_for_nonexistent_file(self, tmp_path):
        tasks = get_pending_tasks(tmp_path / "nonexistent.json")
        assert tasks == []

    def test_returns_empty_for_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        assert get_pending_tasks(bad) == []

    def test_cross_checks_with_state(self, tmp_path, prd_file):
        (tmp_path / ".up").mkdir()
        sm = StateManager(tmp_path)
        sm.record_task_complete("US-002")

        tasks = get_pending_tasks(prd_file, workspace=tmp_path)
        assert len(tasks) == 1
        assert tasks[0]["id"] == "US-003"

        # Verify PRD was auto-synced
        data = json.loads(prd_file.read_text())
        us002 = [s for s in data["userStories"] if s["id"] == "US-002"][0]
        assert us002["passes"] is True


class TestMarkTaskCompleteInPrd:
    """Tests for mark_task_complete_in_prd."""

    def test_marks_task_complete(self, prd_file):
        mark_task_complete_in_prd(prd_file, "US-002")
        data = json.loads(prd_file.read_text())
        us002 = [s for s in data["userStories"] if s["id"] == "US-002"][0]
        assert us002["passes"] is True
        assert "completedAt" in us002

    def test_noop_for_nonexistent_file(self, tmp_path):
        mark_task_complete_in_prd(tmp_path / "nope.json", "US-001")

    def test_noop_for_unknown_task(self, prd_file):
        mark_task_complete_in_prd(prd_file, "US-999")
        data = json.loads(prd_file.read_text())
        assert not any(s.get("id") == "US-999" for s in data["userStories"])


class TestBuildTaskPrompt:
    """Tests for _build_task_prompt."""

    def test_includes_task_id_and_title(self):
        prompt = _build_task_prompt({"id": "US-001", "title": "Add auth"})
        assert "US-001" in prompt
        assert "Add auth" in prompt

    def test_includes_acceptance_criteria(self):
        prompt = _build_task_prompt({
            "id": "US-001",
            "title": "Auth",
            "acceptanceCriteria": ["Login works", "Token refreshes"],
        })
        assert "Login works" in prompt
        assert "Token refreshes" in prompt


class TestParallelExecutionManager:
    """Tests for ParallelExecutionManager."""

    def test_initial_state(self, tmp_path):
        (tmp_path / ".up").mkdir()
        mgr = ParallelExecutionManager(tmp_path)
        assert mgr.state.active is False
        assert mgr.iteration == 0

    def test_set_active(self, tmp_path):
        (tmp_path / ".up").mkdir()
        mgr = ParallelExecutionManager(tmp_path)
        mgr.set_active(True)
        assert mgr.state.active is True

    def test_add_remove_worktree(self, tmp_path):
        (tmp_path / ".up").mkdir()
        mgr = ParallelExecutionManager(tmp_path)
        mgr.add_active_worktree("task-1")
        assert "task-1" in mgr.active_worktrees
        mgr.remove_active_worktree("task-1")
        assert "task-1" not in mgr.active_worktrees

    def test_thread_safety(self, tmp_path):
        """Multiple threads can safely modify state."""
        (tmp_path / ".up").mkdir()
        mgr = ParallelExecutionManager(tmp_path)

        def add_worktree(tid):
            mgr.add_active_worktree(tid)

        threads = [threading.Thread(target=add_worktree, args=(f"t-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(mgr.active_worktrees) == 10
