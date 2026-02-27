"""Tests for builtin memory plugin manifest and registration (US-006)."""

import json
from pathlib import Path

import pytest


PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "builtin" / "memory"
)


class TestMemoryPluginManifest:
    """Test plugin.json structure."""

    def test_plugin_json_exists(self):
        assert (PLUGIN_DIR / "plugin.json").exists()

    def test_plugin_json_valid(self):
        data = json.loads((PLUGIN_DIR / "plugin.json").read_text())
        assert data["name"] == "memory"
        assert data["category"] == "safety"
        assert "version" in data

    def test_hooks_json_exists(self):
        assert (PLUGIN_DIR / "hooks" / "hooks.json").exists()

    def test_hooks_json_has_five_hooks(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        assert len(data["hooks"]) == 5

    def test_hooks_by_command_name(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        hooks_by_name = {h["command"].split("/")[-1].replace(".py", ""): h for h in data["hooks"]}

        assert "task_start" in hooks_by_name["session_prime"]["matcher"]
        assert "task_failed" in hooks_by_name["auto_recall"]["matcher"]
        assert "task_failed" in hooks_by_name["auto_record"]["matcher"]
        assert "task_complete" in hooks_by_name["auto_record"]["matcher"]
        assert "task_failed" in hooks_by_name["auto_learn"]["matcher"]
        assert "git_commit" in hooks_by_name["auto_index"]["matcher"]

    def test_hook_scripts_exist(self):
        hooks_dir = PLUGIN_DIR / "hooks"
        assert (hooks_dir / "session_prime.py").exists()
        assert (hooks_dir / "auto_recall.py").exists()
        assert (hooks_dir / "auto_record.py").exists()
        assert (hooks_dir / "auto_learn.py").exists()
        assert (hooks_dir / "auto_index.py").exists()

    def test_all_hooks_are_command_type(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        for hook in data["hooks"]:
            assert hook["type"] == "command"
            assert hook["timeout"] >= 10
