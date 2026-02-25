"""Tests for bisect plugin (US-008)."""

import json
from pathlib import Path

import pytest


PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "installed" / "bisect"
)


class TestBisectPlugin:
    def test_plugin_json_exists(self):
        assert (PLUGIN_DIR / "plugin.json").exists()

    def test_plugin_json_valid(self):
        data = json.loads((PLUGIN_DIR / "plugin.json").read_text())
        assert data["name"] == "bisect"
        assert data["category"] == "productivity"

    def test_bisect_command_exists(self):
        assert (PLUGIN_DIR / "commands" / "bisect.md").exists()

    def test_command_references_checkpoints(self):
        content = (PLUGIN_DIR / "commands" / "bisect.md").read_text()
        assert "checkpoint" in content.lower()
