"""Tests for up init sync integration (US-007)."""

import json
from pathlib import Path

import pytest

from up.commands.init import _run_init_sync


def _setup_workspace(tmp_path):
    """Create workspace with plugin system ready."""
    up_dir = tmp_path / ".up"
    up_dir.mkdir()
    (up_dir / "config.json").write_text(json.dumps({
        "project": {"name": "init-test"},
    }))

    # Builtin safety plugin
    safety = up_dir / "plugins" / "builtin" / "safety"
    safety.mkdir(parents=True)
    (safety / "plugin.json").write_text(json.dumps({
        "name": "safety", "version": "1.0.0", "category": "safety",
    }))

    # Builtin verify plugin
    verify = up_dir / "plugins" / "builtin" / "verify"
    verify.mkdir(parents=True)
    (verify / "plugin.json").write_text(json.dumps({
        "name": "verify", "version": "1.0.0", "category": "quality",
    }))

    (up_dir / "plugins" / "installed").mkdir(parents=True, exist_ok=True)
    return tmp_path


class TestInitSync:
    def test_generates_claude_md(self, tmp_path):
        ws = _setup_workspace(tmp_path)
        result = _run_init_sync(ws)
        assert result is not None
        assert result["written"] >= 1
        assert (ws / "CLAUDE.md").exists()

    def test_generates_cursorrules(self, tmp_path):
        ws = _setup_workspace(tmp_path)
        _run_init_sync(ws)
        assert (ws / ".cursorrules").exists()

    def test_claude_md_includes_project_name(self, tmp_path):
        ws = _setup_workspace(tmp_path)
        _run_init_sync(ws)
        content = (ws / "CLAUDE.md").read_text()
        assert "init-test" in content

    def test_reports_plugin_count(self, tmp_path):
        ws = _setup_workspace(tmp_path)
        result = _run_init_sync(ws)
        assert result["plugins"] == 2

    def test_cursorrules_includes_project(self, tmp_path):
        ws = _setup_workspace(tmp_path)
        _run_init_sync(ws)
        content = (ws / ".cursorrules").read_text()
        assert "init-test" in content
