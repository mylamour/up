"""Tests for auto-index hook (US-004)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


HOOK_SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "builtin" / "memory" / "hooks" / "auto_index.py"
)


def _run_hook(event_data: dict, workspace: str = None):
    """Run the auto_index hook as a subprocess."""
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


class TestAutoIndexHelpers:
    """Test helper functions directly."""

    def test_skip_merge_commit(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from up.plugins.builtin.memory.hooks.auto_index import _should_skip_commit
        assert _should_skip_commit("Merge branch 'feature' into main") is True

    def test_skip_chore_commit(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from up.plugins.builtin.memory.hooks.auto_index import _should_skip_commit
        assert _should_skip_commit("chore: bump version") is True

    def test_skip_empty_message(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from up.plugins.builtin.memory.hooks.auto_index import _should_skip_commit
        assert _should_skip_commit("") is True
        assert _should_skip_commit(None) is True

    def test_allow_normal_commit(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from up.plugins.builtin.memory.hooks.auto_index import _should_skip_commit
        assert _should_skip_commit("feat: add login page") is False

    def test_allow_fix_commit(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from up.plugins.builtin.memory.hooks.auto_index import _should_skip_commit
        assert _should_skip_commit("fix: resolve auth bug") is False


class TestAutoIndexHook:
    """Test auto_index.py hook script."""

    def test_exits_0_when_disabled(self, tmp_path):
        """Hook exits 0 when auto_index_commits is disabled."""
        up_dir = tmp_path / ".up"
        up_dir.mkdir()
        (up_dir / "config.json").write_text(json.dumps({
            "automation": {"memory": {"auto_index_commits": False}}
        }))
        result = _run_hook(
            {"hash": "abc123", "message": "feat: something"},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0

    def test_exits_0_no_commits(self, tmp_path):
        """Hook exits 0 when no commit data provided."""
        result = _run_hook({}, workspace=str(tmp_path))
        assert result.returncode == 0

    def test_exits_0_merge_commit_skipped(self, tmp_path):
        """Hook exits 0 when commit is a merge commit."""
        result = _run_hook(
            {"hash": "abc123", "message": "Merge branch 'feature'"},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0

    def test_exits_0_chore_commit_skipped(self, tmp_path):
        """Hook exits 0 when commit has chore: prefix."""
        result = _run_hook(
            {"hash": "abc123", "message": "chore: update deps"},
            workspace=str(tmp_path),
        )
        assert result.returncode == 0
