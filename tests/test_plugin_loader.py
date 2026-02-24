"""Tests for PluginLoader with auto-discovery."""

import json
import pytest
from pathlib import Path

from up.plugins.loader import (
    PluginLoader,
    LoadedPlugin,
    PluginComponents,
    _discover_components,
)
from up.plugins.manifest import PluginManifest, PluginCategory


# ── Helpers ────────────────────────────────────────────────────


def _make_plugin(base: Path, name: str, category: str = "productivity") -> Path:
    """Create a minimal plugin directory with a valid plugin.json."""
    plugin_dir = base / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": name,
        "version": "0.1.0",
        "description": f"Test plugin {name}",
        "category": category,
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest))
    return plugin_dir


@pytest.fixture
def plugin_workspace(tmp_path):
    """Workspace with .up/plugins/installed/ and builtin/ dirs."""
    installed = tmp_path / ".up" / "plugins" / "installed"
    builtin = tmp_path / ".up" / "plugins" / "builtin"
    installed.mkdir(parents=True)
    builtin.mkdir(parents=True)
    return tmp_path


# ── Component discovery ────────────────────────────────────────


class TestDiscoverComponents:
    def test_empty_plugin(self, tmp_path):
        plugin = _make_plugin(tmp_path, "empty-plugin")
        c = _discover_components(plugin)
        assert c.commands == []
        assert c.hooks == []
        assert c.rules == []

    def test_discovers_commands(self, tmp_path):
        plugin = _make_plugin(tmp_path, "cmd-plugin")
        cmd_dir = plugin / "commands"
        cmd_dir.mkdir()
        (cmd_dir / "hello.md").write_text("# Hello")
        (cmd_dir / "world.md").write_text("# World")
        c = _discover_components(plugin)
        assert len(c.commands) == 2

    def test_discovers_hooks_json(self, tmp_path):
        plugin = _make_plugin(tmp_path, "hook-plugin")
        hooks_dir = plugin / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "hooks.json").write_text("[]")
        c = _discover_components(plugin)
        assert len(c.hooks) == 1
        assert c.hooks[0].name == "hooks.json"

    def test_discovers_hook_scripts(self, tmp_path):
        plugin = _make_plugin(tmp_path, "hook-plugin")
        hooks_dir = plugin / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "hooks.json").write_text("[]")
        (hooks_dir / "pre-check.py").write_text("# hook")
        c = _discover_components(plugin)
        assert len(c.hooks) == 2

    def test_discovers_rules(self, tmp_path):
        plugin = _make_plugin(tmp_path, "rule-plugin")
        rules_dir = plugin / "rules"
        rules_dir.mkdir()
        (rules_dir / "no-secrets.md").write_text("# No secrets")
        c = _discover_components(plugin)
        assert len(c.rules) == 1


# ── PluginLoader ───────────────────────────────────────────────


class TestPluginLoader:
    def test_empty_workspace(self, plugin_workspace):
        loader = PluginLoader(plugin_workspace)
        assert loader.discover_plugins() == []

    def test_discovers_installed_plugin(self, plugin_workspace):
        installed = plugin_workspace / ".up" / "plugins" / "installed"
        _make_plugin(installed, "my-plugin")
        loader = PluginLoader(plugin_workspace)
        plugins = loader.discover_plugins()
        assert len(plugins) == 1
        assert plugins[0].manifest.name == "my-plugin"

    def test_discovers_builtin_plugin(self, plugin_workspace):
        builtin = plugin_workspace / ".up" / "plugins" / "builtin"
        _make_plugin(builtin, "safety", category="safety")
        loader = PluginLoader(plugin_workspace)
        plugins = loader.discover_plugins()
        assert len(plugins) == 1
        assert plugins[0].manifest.category == PluginCategory.SAFETY

    def test_discovers_both_dirs(self, plugin_workspace):
        builtin = plugin_workspace / ".up" / "plugins" / "builtin"
        installed = plugin_workspace / ".up" / "plugins" / "installed"
        _make_plugin(builtin, "builtin-one", category="safety")
        _make_plugin(installed, "installed-one")
        loader = PluginLoader(plugin_workspace)
        plugins = loader.discover_plugins()
        assert len(plugins) == 2
        names = {p.manifest.name for p in plugins}
        assert names == {"builtin-one", "installed-one"}

    def test_skips_invalid_manifest(self, plugin_workspace):
        installed = plugin_workspace / ".up" / "plugins" / "installed"
        # Valid plugin
        _make_plugin(installed, "good-plugin")
        # Invalid plugin (bad name)
        bad_dir = installed / "BadPlugin"
        bad_dir.mkdir()
        (bad_dir / "plugin.json").write_text(
            json.dumps({"name": "BadPlugin", "version": "1.0.0"})
        )
        loader = PluginLoader(plugin_workspace)
        plugins = loader.discover_plugins()
        assert len(plugins) == 1
        assert plugins[0].manifest.name == "good-plugin"

    def test_no_plugins_dir(self, tmp_path):
        loader = PluginLoader(tmp_path)
        assert loader.discover_plugins() == []

    def test_discovers_components_with_loader(self, plugin_workspace):
        installed = plugin_workspace / ".up" / "plugins" / "installed"
        plugin = _make_plugin(installed, "full-plugin")
        (plugin / "commands").mkdir()
        (plugin / "commands" / "greet.md").write_text("# Greet")
        (plugin / "rules").mkdir()
        (plugin / "rules" / "no-secrets.md").write_text("# Rule")

        loader = PluginLoader(plugin_workspace)
        plugins = loader.discover_plugins()
        assert len(plugins) == 1
        p = plugins[0]
        assert len(p.components.commands) == 1
        assert len(p.components.rules) == 1
