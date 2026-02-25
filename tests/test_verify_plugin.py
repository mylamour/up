"""Tests for builtin verify plugin (US-010)."""

import json
from pathlib import Path

import pytest

from up.plugins.hooks import HookRunner, HookSpec


@pytest.fixture
def verify_plugin_dir():
    return Path(__file__).parent.parent / "src" / "up" / "plugins" / "builtin" / "verify"


class TestVerifyPlugin:
    def test_plugin_json_valid(self, verify_plugin_dir):
        manifest = json.loads((verify_plugin_dir / "plugin.json").read_text())
        assert manifest["name"] == "verify"
        assert manifest["category"] == "quality"

    def test_hooks_json_valid(self, verify_plugin_dir):
        hooks = json.loads(
            (verify_plugin_dir / "hooks" / "hooks.json").read_text()
        )
        assert len(hooks["hooks"]) == 1
        assert hooks["hooks"][0]["matcher"] == "post_tool_use"

    def test_skips_non_modifying_tools(self, verify_plugin_dir, tmp_path):
        runner = HookRunner(workspace=tmp_path)
        script = verify_plugin_dir / "hooks" / "post_tool_use.py"
        spec = HookSpec(type="command", command=f"python3 {script}", timeout=10)
        result = runner.run_hook(spec, {
            "tool_name": "Read",
            "workspace": str(tmp_path),
        })
        assert result.allowed is True
        parsed = json.loads(result.output)
        assert parsed.get("skipped") is True
