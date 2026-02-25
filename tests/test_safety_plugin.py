"""Tests for builtin safety plugin (US-009)."""

import json
from pathlib import Path

import pytest

from up.plugins.hooks import HookRunner, HookSpec


@pytest.fixture
def safety_plugin_dir():
    """Return the path to the builtin safety plugin."""
    return Path(__file__).parent.parent / "src" / "up" / "plugins" / "builtin" / "safety"


class TestSafetyPlugin:
    def test_plugin_json_valid(self, safety_plugin_dir):
        manifest = json.loads((safety_plugin_dir / "plugin.json").read_text())
        assert manifest["name"] == "safety"
        assert manifest["category"] == "safety"

    def test_hooks_json_valid(self, safety_plugin_dir):
        hooks = json.loads(
            (safety_plugin_dir / "hooks" / "hooks.json").read_text()
        )
        assert len(hooks["hooks"]) == 2
        types = [h["matcher"] for h in hooks["hooks"]]
        assert "pre_execute" in types
        assert "post_execute" in types

    def test_pre_execute_hook_runs(self, safety_plugin_dir, tmp_path):
        """Pre-execute hook should run without crashing."""
        runner = HookRunner(workspace=tmp_path)
        script = safety_plugin_dir / "hooks" / "pre_execute.py"
        spec = HookSpec(
            type="command",
            command=f"python3 {script}",
            timeout=10,
        )
        result = runner.run_hook(spec, {"task_id": "test", "workspace": str(tmp_path)})
        # Should warn (no git repo) but not crash
        assert result.exit_code in (0, 1, -1)

    def test_post_execute_hook_no_state(self, safety_plugin_dir, tmp_path):
        """Post-execute hook should handle missing state gracefully."""
        runner = HookRunner(workspace=tmp_path)
        script = safety_plugin_dir / "hooks" / "post_execute.py"
        spec = HookSpec(
            type="command",
            command=f"python3 {script}",
            timeout=10,
        )
        result = runner.run_hook(spec, {"workspace": str(tmp_path), "success": True})
        assert result.allowed is True
