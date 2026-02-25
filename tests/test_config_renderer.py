"""Tests for ConfigRenderer base class and template system."""

import json
from pathlib import Path

import pytest

from up.sync.renderer import (
    ConfigRenderer,
    TemplateContext,
    CommandInfo,
    HookSummary,
    build_context,
    _parse_command_md,
)


class DummyRenderer(ConfigRenderer):
    """Concrete renderer for testing the ABC."""

    @property
    def filename(self) -> str:
        return "dummy.txt"

    def render(self, context: TemplateContext) -> str:
        return f"project={context.project_name}"


class TestTemplateContext:
    def test_defaults(self):
        ctx = TemplateContext()
        assert ctx.project_name == ""
        assert ctx.ai_rules == []
        assert ctx.commands == []
        assert ctx.hooks_summary == []
        assert ctx.memory_protocol is False
        assert ctx.safety_rules == []

    def test_with_values(self):
        ctx = TemplateContext(
            project_name="my-app",
            ai_rules=["rule1"],
            memory_protocol=True,
            safety_rules=["no secrets"],
        )
        assert ctx.project_name == "my-app"
        assert len(ctx.ai_rules) == 1
        assert ctx.memory_protocol is True


class TestConfigRenderer:
    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ConfigRenderer()

    def test_concrete_renderer(self):
        r = DummyRenderer()
        ctx = TemplateContext(project_name="test")
        assert r.render(ctx) == "project=test"
        assert r.filename == "dummy.txt"


def _make_plugin(tmp_path, name, category="productivity", hooks=None, commands=None, rules=None):
    """Helper to create a mock plugin on disk."""
    from up.plugins.loader import LoadedPlugin, _discover_components
    from up.plugins.manifest import PluginManifest, PluginCategory

    plugin_dir = tmp_path / name
    plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "name": name,
        "version": "1.0.0",
        "description": f"Test {name}",
        "category": category,
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest_data))

    if hooks:
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "hooks.json").write_text(json.dumps({"hooks": hooks}))

    if commands:
        cmd_dir = plugin_dir / "commands"
        cmd_dir.mkdir()
        for cmd_name, cmd_text in commands.items():
            (cmd_dir / f"{cmd_name}.md").write_text(cmd_text)

    if rules:
        rules_dir = plugin_dir / "rules"
        rules_dir.mkdir()
        for rule_name, rule_text in rules.items():
            (rules_dir / f"{rule_name}.md").write_text(rule_text)

    manifest = PluginManifest(
        name=name,
        version="1.0.0",
        description=f"Test {name}",
        category=PluginCategory(category),
    )
    components = _discover_components(plugin_dir)
    return LoadedPlugin(manifest=manifest, path=plugin_dir, components=components)


class TestParseCommandMd:
    def test_parses_description(self, tmp_path):
        md = tmp_path / "greet.md"
        md.write_text("# greet\nSay hello to the user\n")
        info = _parse_command_md(md, "my-plugin")
        assert info is not None
        assert info.name == "greet"
        assert info.description == "Say hello to the user"
        assert info.plugin == "my-plugin"

    def test_missing_file(self, tmp_path):
        info = _parse_command_md(tmp_path / "nope.md", "x")
        assert info is None


class TestBuildContext:
    def test_empty(self):
        ctx = build_context({}, [])
        assert ctx.project_name == ""
        assert ctx.commands == []
        assert ctx.memory_protocol is False

    def test_project_name_from_config(self):
        cfg = {"project": {"name": "my-app"}}
        ctx = build_context(cfg, [])
        assert ctx.project_name == "my-app"

    def test_memory_protocol(self):
        cfg = {"automation": {"memory": {"auto_index_commits": True}}}
        ctx = build_context(cfg, [])
        assert ctx.memory_protocol is True

    def test_collects_commands(self, tmp_path):
        plugin = _make_plugin(
            tmp_path, "helper",
            commands={"deploy": "# deploy\nDeploy the app"},
        )
        ctx = build_context({}, [plugin])
        assert len(ctx.commands) == 1
        assert ctx.commands[0].name == "deploy"
        assert ctx.commands[0].plugin == "helper"

    def test_collects_hooks(self, tmp_path):
        plugin = _make_plugin(
            tmp_path, "guard",
            hooks=[{"type": "command", "command": "echo ok", "matcher": "pre_execute"}],
        )
        ctx = build_context({}, [plugin])
        assert len(ctx.hooks_summary) == 1
        assert ctx.hooks_summary[0].plugin == "guard"

    def test_safety_rules(self, tmp_path):
        plugin = _make_plugin(
            tmp_path, "safe",
            category="safety",
            rules={"no-secrets": "Never commit secrets"},
        )
        ctx = build_context({}, [plugin])
        assert len(ctx.safety_rules) == 1
        assert "secrets" in ctx.safety_rules[0]

    def test_ai_rules_from_non_safety(self, tmp_path):
        plugin = _make_plugin(
            tmp_path, "style",
            category="quality",
            rules={"lint": "Always lint before commit"},
        )
        ctx = build_context({}, [plugin])
        assert len(ctx.ai_rules) == 1
        assert "lint" in ctx.ai_rules[0]
