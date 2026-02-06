"""Tests for up.core.provenance module."""

import json
from pathlib import Path

import pytest

from up.core.provenance import ProvenanceEntry, ProvenanceManager


class TestProvenanceEntry:
    """Tests for ProvenanceEntry dataclass."""

    def test_content_addressed_id_excludes_timestamp(self):
        """Same content at different times should produce same ID."""
        e1 = ProvenanceEntry(
            task_id="US-001",
            prompt_hash="abc123",
            context_hash="def456",
            ai_model="claude",
        )
        e2 = ProvenanceEntry(
            task_id="US-001",
            prompt_hash="abc123",
            context_hash="def456",
            ai_model="claude",
        )
        assert e1.id == e2.id
        assert len(e1.id) == 16  # 16 hex chars

    def test_different_content_produces_different_id(self):
        e1 = ProvenanceEntry(
            task_id="US-001",
            prompt_hash="abc",
            ai_model="claude",
        )
        e2 = ProvenanceEntry(
            task_id="US-002",
            prompt_hash="abc",
            ai_model="claude",
        )
        assert e1.id != e2.id

    def test_parent_id_affects_hash(self):
        """Parent ID is part of Merkle chain and should affect ID."""
        e1 = ProvenanceEntry(
            task_id="US-001",
            prompt_hash="abc",
            ai_model="claude",
        )
        e2 = ProvenanceEntry(
            task_id="US-001",
            prompt_hash="abc",
            ai_model="claude",
            parent_id="parent123",
        )
        assert e1.id != e2.id

    def test_sorted_files_deterministic(self):
        """File order should not affect ID."""
        e1 = ProvenanceEntry(
            task_id="US-001",
            prompt_hash="abc",
            ai_model="claude",
            context_files=["b.py", "a.py"],
        )
        e2 = ProvenanceEntry(
            task_id="US-001",
            prompt_hash="abc",
            ai_model="claude",
            context_files=["a.py", "b.py"],
        )
        assert e1.id == e2.id

    def test_to_dict_roundtrip(self):
        entry = ProvenanceEntry(
            task_id="US-001",
            ai_model="claude",
            prompt_hash="abc",
            status="accepted",
            parent_id="parent123",
        )
        data = entry.to_dict()
        restored = ProvenanceEntry.from_dict(data)
        assert restored.id == entry.id
        assert restored.task_id == "US-001"
        assert restored.parent_id == "parent123"

    def test_default_status_is_pending(self):
        entry = ProvenanceEntry(task_id="US-001")
        assert entry.status == "pending"


class TestProvenanceManager:
    """Tests for ProvenanceManager."""

    def test_start_operation(self, workspace):
        mgr = ProvenanceManager(workspace)
        entry = mgr.start_operation(
            task_id="US-001",
            task_title="Test Task",
            prompt="Implement the feature",
            ai_model="claude",
        )
        assert entry.id
        assert entry.task_id == "US-001"
        assert entry.status == "pending"
        assert entry.prompt_hash  # Should be hashed
        assert entry.prompt_preview == "Implement the feature"

    def test_start_operation_truncates_long_prompts(self, workspace):
        mgr = ProvenanceManager(workspace)
        long_prompt = "x" * 300
        entry = mgr.start_operation(
            task_id="US-001",
            task_title="Test",
            prompt=long_prompt,
        )
        assert len(entry.prompt_preview) == 203  # 200 + "..."

    def test_deduplication_same_entry_not_duplicated(self, workspace):
        """Re-fetching the same entry by ID should work."""
        mgr = ProvenanceManager(workspace)
        e1 = mgr.start_operation(
            task_id="US-001",
            task_title="Test",
            prompt="Same prompt",
            ai_model="claude",
        )
        # Verify entry was saved and can be retrieved
        retrieved = mgr.get_entry(e1.id)
        assert retrieved is not None
        assert retrieved.id == e1.id
        assert retrieved.task_id == "US-001"

    def test_get_entry(self, workspace):
        mgr = ProvenanceManager(workspace)
        entry = mgr.start_operation(
            task_id="US-001",
            task_title="Test",
            prompt="Test prompt",
        )
        retrieved = mgr.get_entry(entry.id)
        assert retrieved is not None
        assert retrieved.task_id == "US-001"

    def test_get_entry_not_found(self, workspace):
        mgr = ProvenanceManager(workspace)
        assert mgr.get_entry("nonexistent") is None

    def test_list_entries(self, workspace):
        mgr = ProvenanceManager(workspace)
        mgr.start_operation("US-001", "Task 1", "prompt 1")
        mgr.start_operation("US-002", "Task 2", "prompt 2")

        entries = mgr.list_entries()
        assert len(entries) >= 2

    def test_complete_operation(self, workspace):
        mgr = ProvenanceManager(workspace)
        entry = mgr.start_operation("US-001", "Test", "prompt")

        updated = mgr.complete_operation(
            entry.id,
            files_modified=["src/main.py"],
            lines_added=50,
            commit_sha="abc123",
        )
        assert updated.status == "accepted"  # Default status
        assert updated.files_modified == ["src/main.py"]
        assert updated.lines_added == 50
        assert updated.completed_at is not None

    def test_parent_chain(self, workspace):
        """Entries should link to previous entry via parent_id."""
        mgr = ProvenanceManager(workspace)
        e1 = mgr.start_operation("US-001", "Task 1", "prompt 1")
        e2 = mgr.start_operation("US-002", "Task 2", "prompt 2")
        assert e2.parent_id == e1.id

    def test_context_file_hashing(self, workspace):
        """Context files should be hashed for integrity."""
        # Create a test file
        test_file = workspace / "src" / "main.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("print('hello')")

        mgr = ProvenanceManager(workspace)
        entry = mgr.start_operation(
            "US-001", "Test", "prompt",
            context_files=["src/main.py"],
        )
        assert entry.context_hash  # Should have a hash
