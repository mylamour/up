"""Tests for memory hint injection into SESRC loop (US-005)."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from up.commands.start.loop import _get_memory_hint


class TestGetMemoryHint:
    """Test _get_memory_hint helper."""

    def test_returns_none_no_state_file(self, tmp_path):
        """Returns None when no state.json exists."""
        result = _get_memory_hint(tmp_path, {"id": "US-001"})
        assert result is None

    def test_returns_none_no_last_error(self, tmp_path):
        """Returns None when state has no last_error."""
        up_dir = tmp_path / ".up"
        up_dir.mkdir()
        (up_dir / "state.json").write_text(json.dumps({
            "loop": {"phase": "EXECUTE"}
        }))
        result = _get_memory_hint(tmp_path, {"id": "US-001"})
        assert result is None

    def test_returns_none_empty_last_error(self, tmp_path):
        """Returns None when last_error is empty string."""
        up_dir = tmp_path / ".up"
        up_dir.mkdir()
        (up_dir / "state.json").write_text(json.dumps({
            "loop": {"last_error": ""}
        }))
        result = _get_memory_hint(tmp_path, {"id": "US-001"})
        assert result is None

    @patch("up.memory.MemoryManager")
    def test_returns_hint_when_memory_match(self, mock_mm_cls, tmp_path):
        """Returns formatted hint when memory has a matching entry."""
        up_dir = tmp_path / ".up"
        up_dir.mkdir()
        (up_dir / "state.json").write_text(json.dumps({
            "loop": {"last_error": "KeyError: 'missing_key'"}
        }))
        (up_dir / "memory").mkdir(exist_ok=True)

        # Mock the MemoryManager to return a result
        mock_entry = MagicMock()
        mock_entry.content = "Added default value for missing key"
        mock_entry.timestamp = "2026-02-24T10:00:00"
        mock_manager = MagicMock()
        mock_manager.search.return_value = [mock_entry]
        mock_mm_cls.return_value = mock_manager

        result = _get_memory_hint(tmp_path, {"id": "US-001"})

        assert result is not None
        assert "Past solution found" in result
        assert "Added default value" in result
        assert "Consider this approach" in result

    @patch("up.memory.MemoryManager")
    def test_returns_none_no_memory_match(self, mock_mm_cls, tmp_path):
        """Returns None when memory search finds nothing."""
        up_dir = tmp_path / ".up"
        up_dir.mkdir()
        (up_dir / "state.json").write_text(json.dumps({
            "loop": {"last_error": "SomeObscureError: never seen"}
        }))

        mock_manager = MagicMock()
        mock_manager.search.return_value = []
        mock_mm_cls.return_value = mock_manager

        result = _get_memory_hint(tmp_path, {"id": "US-001"})

        assert result is None

    def test_hint_is_optional_loop_works_without(self, tmp_path):
        """Memory hint is optional — no crash when unavailable."""
        # No .up directory at all
        result = _get_memory_hint(tmp_path, {"id": "US-001"})
        assert result is None
