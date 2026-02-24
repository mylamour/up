"""Tests for PluginRegistry with enable/disable state."""

import json
import pytest
from pathlib import Path

from up.plugins.registry import PluginRegistry, PluginEntry
from up.plugins.manifest import PluginCategory


# ── Helpers ────────────────────────────────────────────────────


def _make_plugin(base: Path, name: str, category: str = "productivity") -> Path:
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
    """Workspace with plugin directories."""
    installed = tmp_path / ".up" / "plugins" / "installed"
    builtin = tmp_path / ".up" / "plugins" / "builtin"
    installed.mkdir(parents=True)
    builtin.mkdir(parents=True)
    return tmp_path


# ── Registry tests ─────────────────────────────────────────────


class TestPluginRegistry:
    def test_load_empty(self, plugin_workspace):
        reg = PluginRegistry(plugin_workspace)
        reg.load()
        assert reg.get_enabled() == []
        assert reg.get_all_entries() == []

    def test_auto_registers_new_plugins(self, plugin_workspace):
        installed = plugin_workspace / ".up" / "plugins" / "installed"
        _make_plugin(installed, "my-plugin")
        reg = PluginRegistry(plugin_workspace)
        reg.load()
        assert reg.is_enabled("my-plugin")
        assert len(reg.get_enabled()) == 1

    def test_enable_disable(self, plugin_workspace):
        installed = plugin_workspace / ".up" / "plugins" / "installed"
        _make_plugin(installed, "my-plugin")
        reg = PluginRegistry(plugin_workspace)
        reg.load()

        assert reg.disable("my-plugin")
        assert not reg.is_enabled("my-plugin")
        assert reg.get_enabled() == []

        assert reg.enable("my-plugin")
        assert reg.is_enabled("my-plugin")
        assert len(reg.get_enabled()) == 1

    def test_unknown_plugin_returns_false(self, plugin_workspace):
        reg = PluginRegistry(plugin_workspace)
        reg.load()
        assert not reg.enable("nonexistent")
        assert not reg.disable("nonexistent")
        assert not reg.is_enabled("nonexistent")

    def test_save_and_reload(self, plugin_workspace):
        installed = plugin_workspace / ".up" / "plugins" / "installed"
        _make_plugin(installed, "alpha")
        _make_plugin(installed, "beta")

        # First load: auto-registers both as enabled
        reg = PluginRegistry(plugin_workspace)
        reg.load()
        reg.disable("beta")
        reg.save()

        # Second load: should remember beta is disabled
        reg2 = PluginRegistry(plugin_workspace)
        reg2.load()
        assert reg2.is_enabled("alpha")
        assert not reg2.is_enabled("beta")
