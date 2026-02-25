"""Tests for auto-record hook (US-003)."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


HOOK_SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "builtin" / "memory" / "hooks" / "auto_record.py"
)


def _run_hook(event_data: dict, workspace: str = None):
    """Run the auto_record hook as a subprocess."""
    env = os.environ.copy()
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")

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


class TestAutoRecordHook:
    """Test auto_record.py hook script."""

    def test_exits_0_when_disabled(self, tmp_path):
        """Hook exits 0 when auto_record is disabled."""
        up_dir = tmp_path / ".up"
        up_dir.mkdir()
        (up_dir / "config.json").write_text(json.dumps({
            "automation": {"memory": {"auto_record": False}}
        }))
        result = _run_hook(
            {"event_type": "task_failed", "error": "KeyError", "consecutive_failures": 3},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0

    def test_exits_0_below_threshold(self, tmp_path):
        """Hook exits 0 when consecutive_failures < threshold."""
        result = _run_hook(
            {"event_type": "task_failed", "error": "KeyError", "consecutive_failures": 1},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0

    def test_exits_0_no_error_output(self, tmp_path):
        """Hook exits 0 when no error text provided."""
        result = _run_hook(
            {"event_type": "task_failed", "consecutive_failures": 3},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0

    def test_records_error_at_threshold(self, tmp_path):
        """Hook records error when consecutive_failures >= threshold."""
        (tmp_path / ".up").mkdir(exist_ok=True)
        (tmp_path / ".up" / "memory").mkdir(exist_ok=True)
        result = _run_hook(
            {
                "event_type": "task_failed",
                "error": "KeyError: 'missing'",
                "consecutive_failures": 2,
                "task_id": "US-001",
                "files": ["src/app.py"],
            },
            workspace=str(tmp_path),
        )
        assert result.returncode == 1
        output = json.loads(result.stdout.strip())
        assert output["recorded"] == "error"
        assert "Memory record" in result.stderr

    def test_records_solution_on_task_complete(self, tmp_path):
        """Hook records solution when task completes after failures."""
        (tmp_path / ".up").mkdir(exist_ok=True)
        (tmp_path / ".up" / "memory").mkdir(exist_ok=True)
        result = _run_hook(
            {
                "event_type": "task_complete",
                "previous_error": "KeyError: 'missing'",
                "solution": "Added default value for key",
            },
            workspace=str(tmp_path),
        )
        assert result.returncode == 1
        output = json.loads(result.stdout.strip())
        assert output["recorded"] == "solution"

    def test_exits_0_task_complete_no_previous_error(self, tmp_path):
        """Hook exits 0 on task_complete with no previous error."""
        result = _run_hook(
            {"event_type": "task_complete"},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0

    def test_custom_threshold(self, tmp_path):
        """Hook respects custom threshold from config."""
        up_dir = tmp_path / ".up"
        up_dir.mkdir()
        (up_dir / "config.json").write_text(json.dumps({
            "automation": {"memory": {"auto_record_threshold": 5}}
        }))
        (up_dir / "memory").mkdir(exist_ok=True)
        # 3 failures < threshold of 5
        result = _run_hook(
            {"event_type": "task_failed", "error": "err", "consecutive_failures": 3},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0


class TestAutoRecordHelpers:
    """Test helper functions directly."""

    def test_error_signature_deterministic(self):
        """Same error text produces same signature."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from up.plugins.builtin.memory.hooks.auto_record import _error_signature
        sig1 = _error_signature("KeyError: 'x'")
        sig2 = _error_signature("KeyError: 'x'")
        assert sig1 == sig2

    def test_error_signature_differs(self):
        """Different errors produce different signatures."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from up.plugins.builtin.memory.hooks.auto_record import _error_signature
        sig1 = _error_signature("KeyError: 'x'")
        sig2 = _error_signature("ValueError: invalid")
        assert sig1 != sig2
