"""Tests for security-guidance plugin (US-002)."""

import json
from pathlib import Path

import pytest


PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent
    / "src" / "up" / "plugins" / "installed" / "security-guidance"
)


class TestSecurityGuidancePlugin:
    def test_plugin_json_exists(self):
        assert (PLUGIN_DIR / "plugin.json").exists()

    def test_plugin_json_valid(self):
        data = json.loads((PLUGIN_DIR / "plugin.json").read_text())
        assert data["name"] == "security-guidance"
        assert data["category"] == "safety"

    def test_rules_directory_exists(self):
        assert (PLUGIN_DIR / "rules").is_dir()

    def test_has_six_rules(self):
        rules = list((PLUGIN_DIR / "rules").glob("*.md"))
        assert len(rules) == 6

    def test_each_rule_has_frontmatter(self):
        for rule_file in (PLUGIN_DIR / "rules").glob("*.md"):
            content = rule_file.read_text()
            assert content.startswith("---"), f"{rule_file.name} missing frontmatter"
            assert "pattern:" in content, f"{rule_file.name} missing pattern"
            assert "action:" in content, f"{rule_file.name} missing action"

    def test_rules_parseable(self):
        from up.plugins.rules import parse_rule
        for rule_file in (PLUGIN_DIR / "rules").glob("*.md"):
            rule = parse_rule(rule_file)
            assert rule is not None, f"Failed to parse {rule_file.name}"
            assert rule.name
            assert rule.pattern
