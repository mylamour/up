"""Plugin loader with auto-discovery.

Scans .up/plugins/installed/ and .up/plugins/builtin/ directories,
reads plugin.json from each, and builds a registry of available plugins
with their components.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from up.plugins.manifest import PluginManifest, ManifestValidationError

logger = logging.getLogger(__name__)

# Standard plugin directories
PLUGINS_DIR = ".up/plugins"
INSTALLED_DIR = "installed"
BUILTIN_DIR = "builtin"


@dataclass
class PluginComponents:
    """Discovered components within a plugin."""
    commands: list[Path] = field(default_factory=list)
    hooks: list[Path] = field(default_factory=list)
    rules: list[Path] = field(default_factory=list)
    agents: list[Path] = field(default_factory=list)
    skills: list[Path] = field(default_factory=list)


@dataclass
class LoadedPlugin:
    """A discovered plugin with its manifest and components."""
    manifest: PluginManifest
    path: Path
    components: PluginComponents = field(default_factory=PluginComponents)


def _discover_components(plugin_path: Path) -> PluginComponents:
    """Scan a plugin directory for components.

    Discovers:
    - commands/*.md
    - hooks/hooks.json
    - rules/*.md
    - agents/ (any files)
    - skills/ (any files)
    """
    components = PluginComponents()

    commands_dir = plugin_path / "commands"
    if commands_dir.is_dir():
        components.commands = sorted(commands_dir.glob("*.md"))

    hooks_dir = plugin_path / "hooks"
    if hooks_dir.is_dir():
        hooks_json = hooks_dir / "hooks.json"
        if hooks_json.exists():
            components.hooks = [hooks_json]
        # Also pick up executable hook scripts
        for f in sorted(hooks_dir.iterdir()):
            if f.is_file() and f.name != "hooks.json":
                components.hooks.append(f)

    rules_dir = plugin_path / "rules"
    if rules_dir.is_dir():
        components.rules = sorted(rules_dir.glob("*.md"))

    agents_dir = plugin_path / "agents"
    if agents_dir.is_dir():
        components.agents = sorted(
            f for f in agents_dir.iterdir() if f.is_file()
        )

    skills_dir = plugin_path / "skills"
    if skills_dir.is_dir():
        components.skills = sorted(
            f for f in skills_dir.iterdir() if f.is_file()
        )

    return components


class PluginLoader:
    """Discovers and loads plugins from the workspace."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.plugins_dir = workspace / PLUGINS_DIR

    def _scan_directory(self, base: Path) -> list[LoadedPlugin]:
        """Scan a directory for plugin subdirectories."""
        plugins: list[LoadedPlugin] = []
        if not base.is_dir():
            return plugins

        for entry in sorted(base.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "plugin.json"
            try:
                manifest = PluginManifest.from_json(manifest_path)
            except ManifestValidationError as e:
                logger.warning("Skipping plugin %s: %s", entry.name, e)
                continue

            components = _discover_components(entry)
            plugins.append(LoadedPlugin(
                manifest=manifest,
                path=entry,
                components=components,
            ))
        return plugins

    def discover_plugins(self) -> list[LoadedPlugin]:
        """Discover all plugins from installed/ and builtin/ directories."""
        installed = self.plugins_dir / INSTALLED_DIR
        builtin = self.plugins_dir / BUILTIN_DIR

        plugins: list[LoadedPlugin] = []
        plugins.extend(self._scan_directory(builtin))
        plugins.extend(self._scan_directory(installed))
        return plugins
