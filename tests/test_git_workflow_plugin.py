"""Tests for git-workflow plugin (US-003)."""

import json
from pathlib import Path

import pytest


PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "installed" / "git-workflow"
)


class TestGitWorkflowPlugin:
    def test_plugin_json_exists(self):
        assert (PLUGIN_DIR / "plugin.json").exists()

    def test_plugin_json_valid(self):
        data = json.loads((PLUGIN_DIR / "plugin.json").read_text())
        assert data["name"] == "git-workflow"
        assert data["category"] == "productivity"

    def test_commit_command_exists(self):
        assert (PLUGIN_DIR / "commands" / "commit.md").exists()

    def test_push_pr_command_exists(self):
        assert (PLUGIN_DIR / "commands" / "push-pr.md").exists()

    def test_commit_has_allowed_tools(self):
        content = (PLUGIN_DIR / "commands" / "commit.md").read_text()
        assert "allowed-tools" in content
        assert "git" in content.lower()

    def test_push_pr_has_allowed_tools(self):
        content = (PLUGIN_DIR / "commands" / "push-pr.md").read_text()
        assert "allowed-tools" in content
        assert "gh" in content.lower()
