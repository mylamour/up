"""Tests for builtin provenance plugin manifest (US-005)."""

import json
from pathlib import Path

import pytest


PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "builtin" / "provenance"
)


class TestProvenancePluginManifest:
    def test_plugin_json_exists(self):
        assert (PLUGIN_DIR / "plugin.json").exists()

    def test_plugin_json_valid(self):
        data = json.loads((PLUGIN_DIR / "plugin.json").read_text())
        assert data["name"] == "provenance"
        assert data["category"] == "safety"
        assert "version" in data

    def test_hooks_json_exists(self):
        assert (PLUGIN_DIR / "hooks" / "hooks.json").exists()

    def test_hooks_json_has_two_hooks(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        assert len(data["hooks"]) == 2

    def test_auto_record_matches_task_events(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        hook = data["hooks"][0]
        assert "auto_record" in hook["command"]
        assert "task_complete" in hook["matcher"]
        assert "task_failed" in hook["matcher"]

    def test_context_capture_matches_execute_events(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        hook = data["hooks"][1]
        assert "context_capture" in hook["command"]
        assert "pre_execute" in hook["matcher"]
        assert "post_execute" in hook["matcher"]

    def test_hook_scripts_exist(self):
        hooks_dir = PLUGIN_DIR / "hooks"
        assert (hooks_dir / "auto_record.py").exists()
        assert (hooks_dir / "context_capture.py").exists()
