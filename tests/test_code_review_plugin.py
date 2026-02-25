"""Tests for code-review plugin (US-001)."""

import json
from pathlib import Path

import pytest


PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "installed" / "code-review"
)


class TestCodeReviewPlugin:
    def test_plugin_json_exists(self):
        assert (PLUGIN_DIR / "plugin.json").exists()

    def test_plugin_json_valid(self):
        data = json.loads((PLUGIN_DIR / "plugin.json").read_text())
        assert data["name"] == "code-review"
        assert data["category"] == "quality"
        assert "version" in data

    def test_review_command_exists(self):
        assert (PLUGIN_DIR / "commands" / "review.md").exists()

    def test_hooks_json_exists(self):
        assert (PLUGIN_DIR / "hooks" / "hooks.json").exists()

    def test_hooks_json_has_post_verify(self):
        data = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text())
        assert len(data["hooks"]) >= 1
        hook = data["hooks"][0]
        assert "post_verify" in hook["command"]

    def test_post_verify_script_exists(self):
        assert (PLUGIN_DIR / "hooks" / "post_verify.py").exists()
