"""Tests for commands/start/ core loop.

Covers: helpers (task finding, circuit breaker, checkpoints),
verification, and PRD schema integration.
"""

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from up.core.prd_schema import PRD, UserStory, save_prd


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def prd_file(workspace):
    """Create a minimal PRD file in workspace."""
    prd = PRD(
        name="test",
        userStories=[
            UserStory(id="T-001", title="First task", priority="high"),
            UserStory(id="T-002", title="Second task", priority="medium"),
            UserStory(id="T-003", title="Done task", passes=True),
        ],
    )
    path = workspace / "prd.json"
    save_prd(prd, path)
    return path


# ── get_next_task_from_prd ────────────────────────────────────────────


class TestGetNextTask:
    def test_returns_first_incomplete(self, workspace, prd_file):
        from up.commands.start.helpers import get_next_task_from_prd

        task = get_next_task_from_prd(prd_file, workspace)
        assert task is not None
        assert task["id"] == "T-001"
        assert task["passes"] is False

    def test_skips_completed(self, workspace, prd_file):
        from up.commands.start.helpers import get_next_task_from_prd

        # Mark T-001 as complete
        prd = json.loads(prd_file.read_text())
        prd["userStories"][0]["passes"] = True
        prd_file.write_text(json.dumps(prd))

        task = get_next_task_from_prd(prd_file, workspace)
        assert task["id"] == "T-002"

    def test_returns_none_when_all_complete(self, workspace):
        from up.commands.start.helpers import get_next_task_from_prd

        prd = PRD(userStories=[
            UserStory(id="T-001", title="Done", passes=True),
        ])
        path = workspace / "prd.json"
        save_prd(prd, path)

        assert get_next_task_from_prd(path, workspace) is None

    def test_returns_none_for_missing_file(self, workspace):
        from up.commands.start.helpers import get_next_task_from_prd

        assert get_next_task_from_prd(workspace / "nope.json", workspace) is None

    def test_returns_none_for_invalid_json(self, workspace):
        from up.commands.start.helpers import get_next_task_from_prd

        bad = workspace / "prd.json"
        bad.write_text("{invalid")
        assert get_next_task_from_prd(bad, workspace) is None


# ── mark_task_complete ────────────────────────────────────────────────


class TestMarkTaskComplete:
    def test_marks_task(self, workspace, prd_file):
        from up.commands.start.helpers import mark_task_complete

        mark_task_complete(workspace, "prd.json", "T-001")

        data = json.loads(prd_file.read_text())
        story = data["userStories"][0]
        assert story["passes"] is True
        assert "completedAt" in story

    def test_noop_for_missing_id(self, workspace, prd_file):
        from up.commands.start.helpers import mark_task_complete

        mark_task_complete(workspace, "prd.json", "NOPE")
        data = json.loads(prd_file.read_text())
        assert data["userStories"][0]["passes"] is False

    def test_noop_for_non_json(self, workspace):
        from up.commands.start.helpers import mark_task_complete

        # Should not raise
        mark_task_complete(workspace, "TODO.md", "T-001")


# ── check_circuit_breaker ─────────────────────────────────────────────


class TestCircuitBreaker:
    def test_closed_circuit(self):
        from up.commands.start.helpers import check_circuit_breaker

        state = {"circuit_breaker": {"test": {"state": "CLOSED", "failures": 0}}}
        result = check_circuit_breaker(state)
        assert result["open"] is False

    def test_open_circuit(self):
        from up.commands.start.helpers import check_circuit_breaker

        state = {"circuit_breaker": {"test": {"state": "OPEN", "failures": 3}}}
        result = check_circuit_breaker(state)
        assert result["open"] is True
        assert "test" in result["circuit"]

    def test_empty_state(self):
        from up.commands.start.helpers import check_circuit_breaker

        result = check_circuit_breaker({})
        assert result["open"] is False


# ── find_task_source ──────────────────────────────────────────────────


class TestFindTaskSource:
    def test_finds_prd_json(self, workspace):
        from up.commands.start.helpers import find_task_source

        (workspace / "prd.json").write_text("{}")
        assert find_task_source(workspace) == "prd.json"

    def test_explicit_path(self, workspace):
        from up.commands.start.helpers import find_task_source

        assert find_task_source(workspace, "custom.json") == "custom.json"

    def test_returns_none(self, workspace):
        from up.commands.start.helpers import find_task_source

        assert find_task_source(workspace) is None


# ── count_tasks ───────────────────────────────────────────────────────


class TestCountTasks:
    def test_counts_pending_json(self, workspace, prd_file):
        from up.commands.start.helpers import count_tasks

        assert count_tasks(workspace, "prd.json") == 2  # T-001, T-002 pending

    def test_counts_md_checkboxes(self, workspace):
        from up.commands.start.helpers import count_tasks

        (workspace / "TODO.md").write_text("- [ ] one\n- [x] done\n- [ ] two\n")
        assert count_tasks(workspace, "TODO.md") == 2

    def test_missing_file(self, workspace):
        from up.commands.start.helpers import count_tasks

        assert count_tasks(workspace, "nope.json") == 0


# ── verification ──────────────────────────────────────────────────────


class TestVerification:
    def test_get_modified_files_empty(self, git_workspace):
        from up.commands.start.verification import get_modified_files

        assert get_modified_files(git_workspace) == []

    def test_get_modified_files_with_changes(self, git_workspace):
        from up.commands.start.verification import get_modified_files

        (git_workspace / "new.txt").write_text("hello")
        files = get_modified_files(git_workspace)
        assert "new.txt" in files

    def test_commit_changes(self, git_workspace):
        from up.commands.start.verification import commit_changes

        (git_workspace / "file.txt").write_text("content")
        assert commit_changes(git_workspace, "test commit") is True

    def test_commit_no_changes(self, git_workspace):
        from up.commands.start.verification import commit_changes

        assert commit_changes(git_workspace, "empty") is False


# ── PRD schema integration ────────────────────────────────────────────


class TestPRDSchema:
    def test_load_and_roundtrip(self, workspace):
        from up.core.prd_schema import load_prd, save_prd

        prd = PRD(
            name="test",
            userStories=[UserStory(id="X-1", title="Test")],
        )
        path = workspace / "prd.json"
        save_prd(prd, path)

        loaded = load_prd(path)
        assert loaded.name == "test"
        assert len(loaded.userStories) == 1
        assert loaded.userStories[0].id == "X-1"

    def test_next_task_skips_completed_ids(self, workspace):
        prd = PRD(userStories=[
            UserStory(id="A", title="a"),
            UserStory(id="B", title="b"),
        ])
        task = prd.next_task(completed_ids={"A"})
        assert task.id == "B"

    def test_validation_error_on_bad_json(self, workspace):
        from up.core.prd_schema import load_prd, PRDValidationError

        bad = workspace / "prd.json"
        bad.write_text("not json")
        with pytest.raises(PRDValidationError):
            load_prd(bad)

    def test_validation_error_on_missing(self, workspace):
        from up.core.prd_schema import load_prd, PRDValidationError

        with pytest.raises(PRDValidationError):
            load_prd(workspace / "nope.json")
