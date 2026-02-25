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

    def test_hooks_json_has_three_hooks(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        assert len(data["hooks"]) == 3

    def test_auto_recall_hook_matches_task_failed(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        recall_hook = data["hooks"][0]
        assert "auto_recall" in recall_hook["command"]
        assert "task_failed" in recall_hook["matcher"]

    def test_auto_record_hook_matches_task_events(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        record_hook = data["hooks"][1]
        assert "auto_record" in record_hook["command"]
        assert "task_failed" in record_hook["matcher"]
        assert "task_complete" in record_hook["matcher"]

    def test_auto_index_hook_matches_git_commit(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        index_hook = data["hooks"][2]
        assert "auto_index" in index_hook["command"]
        assert "git_commit" in index_hook["matcher"]

    def test_hook_scripts_exist(self):
        hooks_dir = PLUGIN_DIR / "hooks"
        assert (hooks_dir / "auto_recall.py").exists()
        assert (hooks_dir / "auto_record.py").exists()
        assert (hooks_dir / "auto_index.py").exists()

    def test_all_hooks_are_command_type(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        for hook in data["hooks"]:
            assert hook["type"] == "command"
            assert hook["timeout"] >= 10
