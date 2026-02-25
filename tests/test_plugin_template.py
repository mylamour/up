"""Tests for plugin template (US-009)."""

import json
from pathlib import Path

import pytest


TEMPLATE_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "templates" / "projects" / "plugin"
)


class TestPluginTemplate:
    def test_template_dir_exists(self):
        assert TEMPLATE_DIR.is_dir()

    def test_plugin_json_template(self):
        data = json.loads((TEMPLATE_DIR / "plugin.json").read_text())
        assert "{{name}}" in data["name"]
        assert "version" in data

    def test_hooks_json_exists(self):
        assert (TEMPLATE_DIR / "hooks" / "hooks.json").exists()

    def test_example_hook_exists(self):
        assert (TEMPLATE_DIR / "hooks" / "example_hook.py").exists()

    def test_example_command_exists(self):
        assert (TEMPLATE_DIR / "commands" / "example.md").exists()

    def test_example_rule_exists(self):
        assert (TEMPLATE_DIR / "rules" / "example-rule.md").exists()

    def test_rule_has_frontmatter(self):
        content = (TEMPLATE_DIR / "rules" / "example-rule.md").read_text()
        assert content.startswith("---")
        assert "pattern:" in content
