"""Claude Code settings renderer.

Generates .claude/settings.json from plugin hook configurations.
Maps UP event types to Claude Code's native hook format.
"""

import json
from pathlib import Path

from up.sync.renderer import ConfigRenderer, TemplateContext, HookSummary

# Map UP event types to Claude Code hook types
HOOK_TYPE_MAP = {
    "pre_tool_use": "PreToolUse",
    "post_tool_use": "PostToolUse",
    "pre_execute": "PreToolUse",
    "post_execute": "PostToolUse",
    "task_start": "PreToolUse",
    "task_complete": "PostToolUse",
}


class ClaudeSettingsRenderer(ConfigRenderer):
    """Renders .claude/settings.json from plugin hooks."""

    @property
    def filename(self) -> str:
        return ".claude/settings.json"

    def render(self, context: TemplateContext) -> str:
        hooks = self._build_hooks(context)
        settings = {"hooks": hooks}
        return json.dumps(settings, indent=2) + "\n"

    def render_merged(self, context: TemplateContext, existing_path: Path) -> str:
        """Render settings merged with existing manual settings."""
        existing = {}
        if existing_path.exists():
            try:
                existing = json.loads(existing_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        hooks = self._build_hooks(context)
        existing["hooks"] = hooks
        return json.dumps(existing, indent=2) + "\n"

    def _build_hooks(self, ctx: TemplateContext) -> dict[str, list[dict]]:
        hooks: dict[str, list[dict]] = {}
        for h in ctx.hooks_summary:
            claude_type = HOOK_TYPE_MAP.get(h.event)
            if not claude_type:
                continue
            entry = {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": h.action,
                        "description": f"UP plugin: {h.plugin}",
                    }
                ],
            }
            hooks.setdefault(claude_type, []).append(entry)
        return hooks
