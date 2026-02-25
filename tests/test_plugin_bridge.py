"""Tests for plugin-EventBridge integration (US-007)."""

import json
from pathlib import Path

import pytest

from up.events import EventBridge, EventType, Event
from up.plugins.bridge import PluginEventBridge


@pytest.fixture(autouse=True)
def reset_bridge_singleton():
    """Reset EventBridge singleton between tests."""
    EventBridge._instance = None
    yield
    EventBridge._instance = None


@pytest.fixture
def workspace(tmp_path):
    """Create a workspace with plugin structure."""
    plugins_dir = tmp_path / ".up" / "plugins"
    (plugins_dir / "installed").mkdir(parents=True)
    (plugins_dir / "builtin").mkdir(parents=True)
    return tmp_path


def _create_plugin(workspace, name, hooks_data, builtin=False):
    """Helper to create a plugin with hooks."""
    subdir = "builtin" if builtin else "installed"
    plugin_dir = workspace / ".up" / "plugins" / subdir / name
    plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": name,
        "version": "0.1.0",
        "description": f"Test plugin {name}",
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest))

    hooks_dir = plugin_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    (hooks_dir / "hooks.json").write_text(json.dumps(hooks_data))

    return plugin_dir


class TestPluginEventBridge:
    def test_initialize_no_plugins(self, workspace):
        bridge = PluginEventBridge(workspace)
        bridge.initialize()
        assert bridge._hook_map == {}

    def test_initialize_loads_hooks(self, workspace):
        _create_plugin(workspace, "test-plugin", {
            "hooks": [
                {"type": "command", "command": "echo ok", "matcher": "pre_tool_use"}
            ]
        })
        bridge = PluginEventBridge(workspace)
        bridge.initialize()
        assert "pre_tool_use" in bridge._hook_map
        assert len(bridge._hook_map["pre_tool_use"]) == 1

    def test_hook_fires_on_event(self, workspace):
        _create_plugin(workspace, "test-plugin", {
            "hooks": [
                {"type": "command", "command": "echo hooked"}
            ]
        })
        bridge = PluginEventBridge(workspace)
        bridge.initialize()

        event = Event(type=EventType.PRE_TOOL_USE, data={"tool_name": "Edit"})
        bridge._bridge.emit(event)
        # Hook ran without error (no block)
        assert not bridge.is_event_blocked(event)

    def test_blocking_hook_marks_event(self, workspace):
        _create_plugin(workspace, "blocker", {
            "hooks": [
                {"type": "command", "command": "echo 'nope' >&2; exit 2"}
            ]
        })
        bridge = PluginEventBridge(workspace)
        bridge.initialize()

        event = Event(type=EventType.PRE_EXECUTE, data={"task_id": "US-001"})
        bridge._bridge.emit(event)
        assert bridge.is_event_blocked(event)
        reasons = bridge.get_block_reasons(event)
        assert len(reasons) == 1
        assert "nope" in reasons[0]

    def test_matcher_filters_events(self, workspace):
        _create_plugin(workspace, "filtered", {
            "hooks": [
                {"type": "command", "command": "exit 2", "matcher": "pre_tool_use"}
            ]
        })
        bridge = PluginEventBridge(workspace)
        bridge.initialize()

        # This event type doesn't match the hook's matcher
        event = Event(type=EventType.POST_EXECUTE, data={})
        bridge._bridge.emit(event)
        assert not bridge.is_event_blocked(event)

    def test_multiple_plugins_hooks(self, workspace):
        _create_plugin(workspace, "plugin-a", {
            "hooks": [{"type": "command", "command": "echo a"}]
        })
        _create_plugin(workspace, "plugin-b", {
            "hooks": [{"type": "command", "command": "echo b"}]
        })
        bridge = PluginEventBridge(workspace)
        bridge.initialize()

        # Both plugins' hooks should be in the "all" bucket
        assert len(bridge._hook_map.get("all", [])) == 2
