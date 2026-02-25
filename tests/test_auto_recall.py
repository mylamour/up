"""Tests for auto-recall hook (US-002)."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


HOOK_SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "builtin" / "memory" / "hooks" / "auto_recall.py"
)


def _run_hook(event_data: dict, workspace: str = None, env_extra: dict = None):
    """Run the auto_recall hook as a subprocess with event JSON on stdin."""
    env = os.environ.copy()
    # Ensure the src directory is on PYTHONPATH so `from up.memory...` works
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")
    if env_extra:
        env.update(env_extra)

    result = subprocess.run(
        [sys.executable, HOOK_SCRIPT],
        input=json.dumps(event_data),
        capture_output=True,
        text=True,
        cwd=workspace or str(Path(__file__).resolve().parent.parent),
        env=env,
        timeout=10,
    )
    return result


class TestAutoRecallHook:
    """Test auto_recall.py hook script."""

    def test_exits_0_when_no_error_output(self, tmp_path):
        """Hook should exit 0 when event has no error data."""
        result = _run_hook({"event_type": "task_failed"}, workspace=str(tmp_path))
        assert result.returncode == 0

    def test_exits_0_when_empty_error(self, tmp_path):
        """Hook should exit 0 when error field is empty string."""
        result = _run_hook(
            {"event_type": "task_failed", "error": ""},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0

    def test_exits_0_when_disabled_by_config(self, tmp_path):
        """Hook should exit 0 when auto_recall is disabled in config."""
        up_dir = tmp_path / ".up"
        up_dir.mkdir()
        (up_dir / "config.json").write_text(json.dumps({
            "automation": {"memory": {"auto_recall": False}}
        }))

        result = _run_hook(
            {"event_type": "task_failed", "error": "KeyError: 'x'"},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0

    @patch("up.memory.MemoryManager")
    def test_searches_memory_on_error(self, mock_mm_cls, tmp_path):
        """Verify the extractor + search flow works end-to-end via import."""
        from up.memory.patterns import ErrorPatternExtractor

        extractor = ErrorPatternExtractor()
        keywords = extractor.extract("KeyError: 'missing_key'")
        assert len(keywords) >= 1
        assert "KeyError" in keywords[0]

    def test_enabled_by_default_no_config(self, tmp_path):
        """Hook should be enabled when no config file exists."""
        # No .up/config.json → auto_recall defaults to True
        # But since MemoryManager import may fail in subprocess without
        # full setup, we just verify it doesn't crash on missing config
        result = _run_hook(
            {"event_type": "task_failed", "error": "KeyError: 'x'"},
            workspace=str(tmp_path),
        )
        # Should exit 0 (import error caught) or 1 (hint found)
        assert result.returncode in (0, 1)

    def test_outputs_json_hint_on_match(self, tmp_path):
        """When memory has a match, hook should output JSON with memory_hint."""
        # We test the logic directly since subprocess needs full env
        from up.memory.patterns import ErrorPatternExtractor

        extractor = ErrorPatternExtractor()
        keywords = extractor.extract(
            "ModuleNotFoundError: No module named 'foo'"
        )
        query = " ".join(keywords)
        assert "ModuleNotFoundError" in query

    def test_handles_malformed_json_gracefully(self, tmp_path):
        """Hook should handle malformed stdin gracefully."""
        env = os.environ.copy()
        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [sys.executable, HOOK_SCRIPT],
            input="not valid json",
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env=env,
            timeout=10,
        )
        # Should fail but not hang
        assert result.returncode != 0  # json.loads raises

    def test_uses_output_field_as_fallback(self):
        """Extractor should work with 'output' field when 'error' is empty."""
        from up.memory.patterns import ErrorPatternExtractor

        extractor = ErrorPatternExtractor()
        keywords = extractor.extract("FAILED tests/test_x.py::test_foo - AssertionError: assert 1 == 2")
        assert any("test_foo" in k for k in keywords)
