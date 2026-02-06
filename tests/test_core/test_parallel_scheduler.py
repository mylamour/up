"""Tests for up.parallel_scheduler module."""

import json
import threading
from pathlib import Path

import pytest

from up.parallel_scheduler import (
    build_dependency_graph,
    get_execution_waves,
    TaskFileMap,
    SharedKnowledge,
)


class TestBuildDependencyGraph:
    """Tests for dependency graph construction."""

    def test_no_dependencies(self):
        tasks = [
            {"id": "A"},
            {"id": "B"},
            {"id": "C"},
        ]
        graph = build_dependency_graph(tasks)
        assert graph == {"A": set(), "B": set(), "C": set()}

    def test_simple_chain(self):
        tasks = [
            {"id": "A"},
            {"id": "B", "depends_on": ["A"]},
            {"id": "C", "depends_on": ["B"]},
        ]
        graph = build_dependency_graph(tasks)
        assert graph["A"] == set()
        assert graph["B"] == {"A"}
        assert graph["C"] == {"B"}

    def test_ignores_external_deps(self):
        """Dependencies on tasks not in the current set are ignored."""
        tasks = [
            {"id": "B", "depends_on": ["A"]},  # A not in tasks
        ]
        graph = build_dependency_graph(tasks)
        assert graph["B"] == set()

    def test_diamond_deps(self):
        tasks = [
            {"id": "A"},
            {"id": "B", "depends_on": ["A"]},
            {"id": "C", "depends_on": ["A"]},
            {"id": "D", "depends_on": ["B", "C"]},
        ]
        graph = build_dependency_graph(tasks)
        assert graph["D"] == {"B", "C"}


class TestGetExecutionWaves:
    """Tests for wave-based scheduling."""

    def test_independent_tasks_single_wave(self):
        tasks = [
            {"id": "A"},
            {"id": "B"},
            {"id": "C"},
        ]
        waves = get_execution_waves(tasks)
        assert len(waves) == 1
        ids = {t["id"] for t in waves[0]}
        assert ids == {"A", "B", "C"}

    def test_chain_produces_sequential_waves(self):
        tasks = [
            {"id": "A"},
            {"id": "B", "depends_on": ["A"]},
            {"id": "C", "depends_on": ["B"]},
        ]
        waves = get_execution_waves(tasks)
        assert len(waves) == 3
        assert waves[0][0]["id"] == "A"
        assert waves[1][0]["id"] == "B"
        assert waves[2][0]["id"] == "C"

    def test_diamond_produces_three_waves(self):
        tasks = [
            {"id": "A"},
            {"id": "B", "depends_on": ["A"]},
            {"id": "C", "depends_on": ["A"]},
            {"id": "D", "depends_on": ["B", "C"]},
        ]
        waves = get_execution_waves(tasks)
        assert len(waves) == 3
        # Wave 1: A
        assert {t["id"] for t in waves[0]} == {"A"}
        # Wave 2: B and C (parallel)
        assert {t["id"] for t in waves[1]} == {"B", "C"}
        # Wave 3: D
        assert {t["id"] for t in waves[2]} == {"D"}

    def test_mixed_deps_and_independent(self):
        tasks = [
            {"id": "A"},
            {"id": "B"},
            {"id": "C", "depends_on": ["A"]},
            {"id": "D"},
        ]
        waves = get_execution_waves(tasks)
        # Wave 1: A, B, D (all independent)
        # Wave 2: C (depends on A)
        assert len(waves) == 2
        wave1_ids = {t["id"] for t in waves[0]}
        assert "A" in wave1_ids
        assert "B" in wave1_ids
        assert "D" in wave1_ids
        assert waves[1][0]["id"] == "C"

    def test_empty_tasks(self):
        assert get_execution_waves([]) == []


class TestTaskFileMap:
    """Tests for file conflict detection."""

    def test_analyze_task_extracts_paths(self):
        fm = TaskFileMap()
        task = {
            "id": "T1",
            "description": "Modify src/up/core/state.py to add locking",
            "acceptanceCriteria": ["Update tests/test_state.py"],
        }
        files = fm.analyze_task(task, Path("/fake/workspace"))
        assert "src/up/core/state.py" in files
        assert "tests/test_state.py" in files

    def test_find_conflicts(self):
        fm = TaskFileMap()
        fm.task_files = {
            "T1": {"src/main.py", "src/utils.py"},
            "T2": {"src/main.py", "src/other.py"},
            "T3": {"src/different.py"},
        }
        wave = [{"id": "T1"}, {"id": "T2"}, {"id": "T3"}]
        conflicts = fm.find_conflicts(wave)
        assert len(conflicts) == 1
        assert conflicts[0][0] == "T1"
        assert conflicts[0][1] == "T2"
        assert "src/main.py" in conflicts[0][2]

    def test_no_conflicts(self):
        fm = TaskFileMap()
        fm.task_files = {
            "T1": {"src/a.py"},
            "T2": {"src/b.py"},
        }
        wave = [{"id": "T1"}, {"id": "T2"}]
        assert fm.find_conflicts(wave) == []

    def test_split_wave_by_conflicts(self):
        fm = TaskFileMap()
        fm.task_files = {
            "T1": {"src/main.py"},
            "T2": {"src/main.py"},
            "T3": {"src/other.py"},
        }
        wave = [{"id": "T1"}, {"id": "T2"}, {"id": "T3"}]
        sub_waves = fm.split_wave_by_conflicts(wave, max_workers=3)
        # T1 and T2 conflict, so they must be in different sub-waves
        assert len(sub_waves) == 2
        sw1_ids = {t["id"] for t in sub_waves[0]}
        sw2_ids = {t["id"] for t in sub_waves[1]}
        assert not ({"T1", "T2"} <= sw1_ids)  # T1 and T2 not together


class TestSharedKnowledge:
    """Tests for cross-agent shared knowledge."""

    def test_add_and_get_entry(self, workspace):
        sk = SharedKnowledge(workspace)
        sk.add_entry("agent-1", "discovery", "Found a bug in auth.py")
        context = sk.get_context_for_agent("agent-2")
        assert "Found a bug in auth.py" in context

    def test_own_entries_excluded(self, workspace):
        sk = SharedKnowledge(workspace)
        sk.add_entry("agent-1", "discovery", "My own finding")
        context = sk.get_context_for_agent("agent-1")
        assert "My own finding" not in context

    def test_warnings(self, workspace):
        sk = SharedKnowledge(workspace)
        sk.add_warning("agent-1", "Don't modify routes.py")
        context = sk.get_context_for_agent("agent-2")
        assert "Don't modify routes.py" in context

    def test_file_claims(self, workspace):
        sk = SharedKnowledge(workspace)
        conflicts = sk.claim_files("agent-1", {"src/a.py", "src/b.py"})
        assert conflicts == set()

        conflicts = sk.claim_files("agent-2", {"src/b.py", "src/c.py"})
        assert "src/b.py" in conflicts

    def test_release_files(self, workspace):
        sk = SharedKnowledge(workspace)
        sk.claim_files("agent-1", {"src/a.py"})
        sk.release_files("agent-1")
        conflicts = sk.claim_files("agent-2", {"src/a.py"})
        assert conflicts == set()

    def test_mark_complete(self, workspace):
        sk = SharedKnowledge(workspace)
        sk.mark_complete("T1")
        sk.mark_complete("T1")  # Idempotent
        assert sk._data["completed_tasks"].count("T1") == 1

    def test_reset(self, workspace):
        sk = SharedKnowledge(workspace)
        sk.add_entry("agent-1", "test", "data")
        sk.reset()
        assert sk._data["entries"] == []

    def test_thread_safety(self, workspace):
        sk = SharedKnowledge(workspace)
        errors = []

        def add_entries(agent_id):
            try:
                for i in range(10):
                    sk.add_entry(agent_id, "test", f"entry-{i}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=add_entries, args=(f"agent-{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(sk._data["entries"]) == 50
