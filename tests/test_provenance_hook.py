"""Tests for provenance auto-record hook (US-001)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


HOOK_SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "builtin" / "provenance" / "hooks" / "auto_record.py"
)


def _run_hook(event_data: dict, workspace: str = None):
    """Run the provenance auto_record hook as a subprocess."""
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


class TestProvenanceAutoRecordHook:
    """Test provenance auto_record.py hook."""

    def test_exits_0_unknown_event(self, tmp_path):
        result = _run_hook({"event_type": "unknown"}, workspace=str(tmp_path))
        assert result.returncode == 0

    def test_exits_0_no_task_id(self, tmp_path):
        result = _run_hook({"event_type": "task_complete"}, workspace=str(tmp_path))
        assert result.returncode == 0

    def test_records_on_task_complete(self, tmp_path):
        (tmp_path / ".up" / "provenance").mkdir(parents=True)
        result = _run_hook(
            {
                "event_type": "task_complete",
                "task_id": "US-001",
                "task_title": "Test task",
                "ai_model": "claude",
                "files_modified": ["src/app.py"],
            },
            workspace=str(tmp_path),
        )
        assert result.returncode == 1
        output = json.loads(result.stdout.strip())
        assert "provenance_id" in output
        assert output["status"] == "accepted"

    def test_records_on_task_failed(self, tmp_path):
        (tmp_path / ".up" / "provenance").mkdir(parents=True)
        result = _run_hook(
            {
                "event_type": "task_failed",
                "task_id": "US-002",
                "task_title": "Failed task",
                "error": "KeyError: missing",
            },
            workspace=str(tmp_path),
        )
        assert result.returncode == 1
        output = json.loads(result.stdout.strip())
        assert output["status"] == "rejected"
