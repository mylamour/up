"""Claude Code settings renderer.

Generates .claude/settings.json from plugin hook configurations.
Maps UP event types to Claude Code's native hook format.
"""

import json
from pathlib import Path

from up.sync.renderer import ConfigRenderer, TemplateContext

# Map UP event types to Claude Code hook types.
# Only map events that have direct Claude Code equivalents.
# UP-internal events (pre_execute, post_execute, task_start, task_complete)
# are for the SESRC loop and should NOT fire on every Claude Code tool call.
HOOK_TYPE_MAP = {
    "pre_tool_use": "PreToolUse",
    "post_tool_use": "PostToolUse",
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

    def _resolve_command(self, action: str, plugin_dir: str) -> str:
        """Resolve relative paths in hook commands to use $CLAUDE_PROJECT_DIR."""
        if not plugin_dir:
            return action
        parts = action.split()
        if len(parts) < 2:
            return action
        # Find the first arg that looks like a relative file path
        # (contains / or ends with .py/.sh/.js), skip flags like -u
        for i, part in enumerate(parts[1:], 1):
            if part.startswith("-"):
                continue
            if "/" in part or part.endswith((".py", ".sh", ".js")):
                parts[i] = f'"$CLAUDE_PROJECT_DIR/{plugin_dir}/{part}"'
                break
        return " ".join(parts)

    def _build_hooks(self, ctx: TemplateContext) -> dict[str, list[dict]]:
        hooks: dict[str, list[dict]] = {}
        for h in ctx.hooks_summary:
            claude_type = HOOK_TYPE_MAP.get(h.event)
            if not claude_type:
                continue
            command = self._resolve_command(h.action, h.plugin_dir)
            entry = {
                "matcher": h.tool_matcher or "",
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "description": f"UP plugin: {h.plugin}",
                    }
                ],
            }
            hooks.setdefault(claude_type, []).append(entry)
        return hooks
