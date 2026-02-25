"""Tests for Claude Code settings renderer."""

import json
from pathlib import Path

from up.sync.claude_settings import ClaudeSettingsRenderer, HOOK_TYPE_MAP
from up.sync.renderer import TemplateContext, HookSummary


class TestClaudeSettingsRenderer:
    def setup_method(self):
        self.renderer = ClaudeSettingsRenderer()

    def test_filename(self):
        assert self.renderer.filename == ".claude/settings.json"

    def test_empty_hooks(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        data = json.loads(output)
        assert data == {"hooks": {}}

    def test_maps_pre_tool_use(self):
        ctx = TemplateContext(hooks_summary=[
            HookSummary(event="pre_tool_use", plugin="safety", action="python check.py"),
        ])
        output = self.renderer.render(ctx)
        data = json.loads(output)
        assert "PreToolUse" in data["hooks"]
        entries = data["hooks"]["PreToolUse"]
        assert len(entries) == 1
        assert entries[0]["matcher"] == ""
        assert entries[0]["hooks"][0]["type"] == "command"
        assert entries[0]["hooks"][0]["command"] == "python check.py"

    def test_maps_post_tool_use(self):
        ctx = TemplateContext(hooks_summary=[
            HookSummary(event="post_tool_use", plugin="verify", action="python verify.py"),
        ])
        output = self.renderer.render(ctx)
        data = json.loads(output)
        assert "PostToolUse" in data["hooks"]
        assert data["hooks"]["PostToolUse"][0]["hooks"][0]["command"] == "python verify.py"

    def test_skips_unknown_event(self):
        ctx = TemplateContext(hooks_summary=[
            HookSummary(event="unknown_event", plugin="x", action="echo"),
        ])
        output = self.renderer.render(ctx)
        data = json.loads(output)
        assert data["hooks"] == {}

    def test_description_includes_plugin(self):
        ctx = TemplateContext(hooks_summary=[
            HookSummary(event="pre_tool_use", plugin="safety", action="check"),
        ])
        output = self.renderer.render(ctx)
        data = json.loads(output)
        hook_entry = data["hooks"]["PreToolUse"][0]["hooks"][0]
        assert "safety" in hook_entry["description"]

    def test_multiple_hooks_same_type_grouped(self):
        ctx = TemplateContext(hooks_summary=[
            HookSummary(event="pre_tool_use", plugin="a", action="cmd1"),
            HookSummary(event="pre_tool_use", plugin="b", action="cmd2"),
        ])
        output = self.renderer.render(ctx)
        data = json.loads(output)
        assert len(data["hooks"]["PreToolUse"]) == 2

    def test_render_merged_preserves_existing(self, tmp_path):
        existing = tmp_path / "settings.json"
        existing.write_text(json.dumps({
            "custom_key": "keep_me",
            "hooks": {"Old": [{"matcher": {}, "hooks": []}]},
        }))
        ctx = TemplateContext(hooks_summary=[
            HookSummary(event="pre_tool_use", plugin="s", action="cmd"),
        ])
        output = self.renderer.render_merged(ctx, existing)
        data = json.loads(output)
        assert data["custom_key"] == "keep_me"
        assert "PreToolUse" in data["hooks"]

    def test_render_merged_missing_file(self, tmp_path):
        missing = tmp_path / "nope.json"
        ctx = TemplateContext()
        output = self.renderer.render_merged(ctx, missing)
        data = json.loads(output)
        assert data == {"hooks": {}}
