"""Tests for Markdown rules engine (US-008)."""

from pathlib import Path

import pytest

from up.plugins.rules import (
    RuleSpec, parse_rule, evaluate, RulesEngine,
    _split_frontmatter, _parse_yaml_simple,
)
from up.plugins.hooks import HookResult


class TestSplitFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nname: test\n---\nBody text here."
        fm, body = _split_frontmatter(content)
        assert fm == "name: test"
        assert body == "Body text here."

    def test_no_frontmatter(self):
        content = "Just plain text."
        fm, body = _split_frontmatter(content)
        assert fm is None
        assert body == "Just plain text."

    def test_incomplete_frontmatter(self):
        content = "---\nname: test\nno closing"
        fm, body = _split_frontmatter(content)
        assert fm is None


class TestParseYamlSimple:
    def test_basic_pairs(self):
        text = "name: my-rule\nevent: pre_tool_use\nconfidence: 90"
        result = _parse_yaml_simple(text)
        assert result["name"] == "my-rule"
        assert result["event"] == "pre_tool_use"
        assert result["confidence"] == "90"

    def test_quoted_values(self):
        text = 'pattern: "git push.*--force"'
        result = _parse_yaml_simple(text)
        assert result["pattern"] == "git push.*--force"

    def test_skips_comments(self):
        text = "# comment\nname: test"
        result = _parse_yaml_simple(text)
        assert "name" in result
        assert len(result) == 1


class TestParseRule:
    def test_valid_rule(self, tmp_path):
        rule_file = tmp_path / "no-force-push.md"
        rule_file.write_text(
            '---\n'
            'name: no-force-push\n'
            'event: pre_tool_use\n'
            'pattern: "git push.*--force"\n'
            'action: block\n'
            'confidence: 95\n'
            '---\n'
            'Do not force push to protected branches.\n'
        )
        rule = parse_rule(rule_file)
        assert rule is not None
        assert rule.name == "no-force-push"
        assert rule.event == "pre_tool_use"
        assert rule.action == "block"
        assert rule.confidence == 95
        assert "force push" in rule.message

    def test_missing_name(self, tmp_path):
        rule_file = tmp_path / "bad.md"
        rule_file.write_text("---\nevent: pre_tool_use\n---\nBody.")
        rule = parse_rule(rule_file)
        assert rule is None

    def test_no_frontmatter(self, tmp_path):
        rule_file = tmp_path / "plain.md"
        rule_file.write_text("Just plain markdown.")
        rule = parse_rule(rule_file)
        assert rule is None

    def test_defaults(self, tmp_path):
        rule_file = tmp_path / "minimal.md"
        rule_file.write_text("---\nname: minimal\n---\nMinimal rule.")
        rule = parse_rule(rule_file)
        assert rule is not None
        assert rule.event == "all"
        assert rule.action == "warn"
        assert rule.confidence == 50


class TestEvaluate:
    def test_block_on_match(self):
        rule = RuleSpec(
            name="no-force-push", event="pre_tool_use",
            pattern="git push.*--force", action="block",
            confidence=95, message="No force push allowed.",
        )
        result = evaluate(rule, {
            "event_type": "pre_tool_use",
            "command": "git push --force origin main",
        })
        assert result.allowed is False
        assert result.exit_code == 2

    def test_warn_on_match(self):
        rule = RuleSpec(
            name="large-file", event="post_tool_use",
            pattern="large_file", action="warn",
            confidence=70, message="Large file detected.",
        )
        result = evaluate(rule, {
            "event_type": "post_tool_use",
            "file": "large_file.bin",
        })
        assert result.allowed is True
        assert result.exit_code == 1

    def test_no_match(self):
        rule = RuleSpec(
            name="test", event="all",
            pattern="dangerous", action="block",
            confidence=90, message="Blocked.",
        )
        result = evaluate(rule, {"event_type": "pre_tool_use", "cmd": "echo hi"})
        assert result.allowed is True
        assert "no match" in result.message

    def test_event_mismatch_skips(self):
        rule = RuleSpec(
            name="test", event="pre_tool_use",
            pattern=".*", action="block",
            confidence=90, message="Blocked.",
        )
        result = evaluate(rule, {"event_type": "post_execute"})
        assert result.allowed is True
        assert "skipped" in result.message


class TestRulesEngine:
    def _make_rule_file(self, rules_dir, name, event="all", pattern=".*",
                        action="warn", confidence=50, message="Test rule."):
        rule_file = rules_dir / f"{name}.md"
        rule_file.write_text(
            f'---\nname: {name}\nevent: {event}\n'
            f'pattern: "{pattern}"\naction: {action}\n'
            f'confidence: {confidence}\n---\n{message}\n'
        )
        return rule_file

    def test_load_rules(self, tmp_path):
        plugin_dir = tmp_path / "my-plugin"
        rules_dir = plugin_dir / "rules"
        rules_dir.mkdir(parents=True)
        self._make_rule_file(rules_dir, "rule-a")
        self._make_rule_file(rules_dir, "rule-b")

        engine = RulesEngine()
        loaded = engine.load_rules(plugin_dir)
        assert len(loaded) == 2
        assert len(engine.rules) == 2

    def test_load_rules_no_dir(self, tmp_path):
        engine = RulesEngine()
        loaded = engine.load_rules(tmp_path / "nonexistent")
        assert loaded == []

    def test_evaluate_all(self, tmp_path):
        plugin_dir = tmp_path / "plugin"
        rules_dir = plugin_dir / "rules"
        rules_dir.mkdir(parents=True)
        self._make_rule_file(rules_dir, "block-rm", event="pre_tool_use",
                             pattern="rm -rf", action="block",
                             message="No recursive delete.")

        engine = RulesEngine()
        engine.load_rules(plugin_dir)

        results = engine.evaluate_all({
            "event_type": "pre_tool_use",
            "command": "rm -rf /important",
        })
        assert len(results) == 1
        assert results[0].allowed is False

    def test_get_blocking_results(self, tmp_path):
        plugin_dir = tmp_path / "plugin"
        rules_dir = plugin_dir / "rules"
        rules_dir.mkdir(parents=True)
        self._make_rule_file(rules_dir, "warn-rule", action="warn",
                             pattern="test", message="Just a warning.")
        self._make_rule_file(rules_dir, "block-rule", action="block",
                             pattern="test", message="Blocked!")

        engine = RulesEngine()
        engine.load_rules(plugin_dir)

        blocking = engine.get_blocking_results({
            "event_type": "all", "data": "test value",
        })
        assert len(blocking) == 1
        assert "Blocked!" in blocking[0].message

    def test_clear(self, tmp_path):
        plugin_dir = tmp_path / "plugin"
        rules_dir = plugin_dir / "rules"
        rules_dir.mkdir(parents=True)
        self._make_rule_file(rules_dir, "rule-x")

        engine = RulesEngine()
        engine.load_rules(plugin_dir)
        assert len(engine.rules) == 1
        engine.clear()
        assert len(engine.rules) == 0
