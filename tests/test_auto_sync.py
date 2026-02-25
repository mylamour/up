"""Tests for auto-sync on plugin state changes (US-006)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from up.commands.plugin import plugin_group


def _setup_workspace(tmp_path):
    """Create workspace with config and a plugin."""
    up_dir = tmp_path / ".up"
    config = {"project": {"name": "test"}}
    (up_dir).mkdir()
    (up_dir / "config.json").write_text(json.dumps(config))

    # Builtin plugin
    p = up_dir / "plugins" / "builtin" / "safety"
    p.mkdir(parents=True)
    (p / "plugin.json").write_text(json.dumps({
        "name": "safety", "version": "1.0.0", "category": "safety",
    }))
    (up_dir / "plugins" / "installed").mkdir(parents=True, exist_ok=True)
    return tmp_path


class TestAutoSync:
    def test_enable_triggers_sync(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)

        runner = CliRunner()
        # First disable, then enable to trigger sync
        runner.invoke(plugin_group, ["disable", "safety", "--no-sync"])
        result = runner.invoke(plugin_group, ["enable", "safety"])

        assert result.exit_code == 0
        assert (ws / "CLAUDE.md").exists()

    def test_disable_triggers_sync(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)

        runner = CliRunner()
        result = runner.invoke(plugin_group, ["disable", "safety"])

        assert result.exit_code == 0
        # Config files should still be generated (just without the disabled plugin)
        assert (ws / "CLAUDE.md").exists()

    def test_no_sync_flag_skips(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path)
        monkeypatch.chdir(ws)

        runner = CliRunner()
        result = runner.invoke(plugin_group, ["disable", "safety", "--no-sync"])

        assert result.exit_code == 0
        assert not (ws / "CLAUDE.md").exists()
