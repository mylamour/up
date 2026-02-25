"""ConfigRenderer base class and template context.

Provides the abstract renderer interface and TemplateContext dataclass
that aggregates data from .up/config.json and enabled plugins.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from up.plugins.loader import LoadedPlugin
from up.plugins.hooks import load_hooks_from_json


@dataclass
class CommandInfo:
    """A command exposed by a plugin."""
    name: str
    description: str
    plugin: str


@dataclass
class HookSummary:
    """Summary of a hook from a plugin."""
    event: str
    plugin: str
    action: str
    plugin_dir: str = ""  # relative path from project root to plugin dir
    tool_matcher: str = ""  # Claude Code tool matcher (e.g. "Write|Edit")


@dataclass
class TemplateContext:
    """Aggregated context for rendering config files."""
    project_name: str = ""
    ai_rules: list[str] = field(default_factory=list)
    commands: list[CommandInfo] = field(default_factory=list)
    hooks_summary: list[HookSummary] = field(default_factory=list)
    memory_protocol: bool = False
    safety_rules: list[str] = field(default_factory=list)


class ConfigRenderer(ABC):
    """Abstract base class for config file renderers."""

    @abstractmethod
    def render(self, context: TemplateContext) -> str:
        """Render config file content from template context."""

    @property
    @abstractmethod
    def filename(self) -> str:
        """Target filename this renderer produces."""


def _parse_command_md(path: Path, plugin_name: str) -> Optional[CommandInfo]:
    """Parse a plugin command markdown file into CommandInfo."""
    try:
        text = path.read_text()
        lines = text.strip().splitlines()
        name = path.stem
        description = ""
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                description = stripped
                break
        return CommandInfo(name=name, description=description, plugin=plugin_name)
    except Exception:
        return None


def build_context(config: dict, plugins: list[LoadedPlugin]) -> TemplateContext:
    """Aggregate data from config and enabled plugins into TemplateContext.

    Args:
        config: Parsed .up/config.json dict.
        plugins: List of enabled LoadedPlugin instances.

    Returns:
        TemplateContext ready for rendering.
    """
    ctx = TemplateContext()

    # Project name from config or fallback
    ctx.project_name = config.get("project", {}).get("name", "")

    # Memory protocol
    memory_cfg = config.get("automation", {}).get("memory", {})
    ctx.memory_protocol = any(memory_cfg.values()) if memory_cfg else False

    # Collect from plugins
    for plugin in plugins:
        pname = plugin.manifest.name

        # Commands from markdown files
        for cmd_path in plugin.components.commands:
            info = _parse_command_md(cmd_path, pname)
            if info:
                ctx.commands.append(info)

        # Hooks summary
        for hook_path in plugin.components.hooks:
            if hook_path.name == "hooks.json":
                # plugin root is parent of hooks/ dir
                plugin_root = hook_path.parent.parent
                # Find .up/ ancestor to compute relative path from project root
                rel_plugin = ""
                for parent in plugin_root.parents:
                    up_dir = parent / ".up"
                    if up_dir.exists() and plugin_root.is_relative_to(parent):
                        rel_plugin = str(plugin_root.relative_to(parent))
                        break
                specs = load_hooks_from_json(hook_path)
                for spec in specs:
                    event = spec.matcher or "all"
                    ctx.hooks_summary.append(
                        HookSummary(
                            event=event, plugin=pname,
                            action=spec.command, plugin_dir=rel_plugin,
                            tool_matcher=spec.tool_matcher or "",
                        )
                    )

        # Rules → safety_rules and ai_rules
        for rule_path in plugin.components.rules:
            try:
                text = rule_path.read_text().strip()
                if plugin.manifest.category.value == "safety":
                    ctx.safety_rules.append(text)
                else:
                    ctx.ai_rules.append(text)
            except Exception:
                pass

    return ctx
