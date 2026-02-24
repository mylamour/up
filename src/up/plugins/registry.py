"""Plugin registry with enable/disable state.

Persists plugin state (enabled/disabled) in .up/plugins/registry.json.
Provides lookup methods for active plugins and their components.
"""

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from up.plugins.loader import PluginLoader, LoadedPlugin

logger = logging.getLogger(__name__)

REGISTRY_FILE = "registry.json"


@dataclass
class PluginEntry:
    """Persisted state for a single plugin in registry.json."""
    name: str
    version: str
    enabled: bool = True
    installed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "local"


class PluginRegistry:
    """Manages plugin state with persistence to registry.json."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.plugins_dir = workspace / ".up" / "plugins"
        self.registry_file = self.plugins_dir / REGISTRY_FILE
        self._entries: dict[str, PluginEntry] = {}
        self._plugins: dict[str, LoadedPlugin] = {}
        self._loader = PluginLoader(workspace)

    def _read_registry(self) -> dict[str, PluginEntry]:
        """Read persisted entries from registry.json."""
        entries: dict[str, PluginEntry] = {}
        if not self.registry_file.exists():
            return entries
        try:
            data = json.loads(self.registry_file.read_text())
            for raw in data.get("plugins", []):
                name = raw.get("name", "")
                if name:
                    entries[name] = PluginEntry(
                        name=name,
                        version=raw.get("version", "0.0.0"),
                        enabled=raw.get("enabled", True),
                        installed_at=raw.get("installed_at", ""),
                        source=raw.get("source", "local"),
                    )
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Could not read registry: %s", e)
        return entries

    def load(self) -> None:
        """Load registry from disk and merge with discovered plugins.

        Reads registry.json for persisted state, then runs plugin discovery.
        New plugins found on disk are auto-registered as enabled.
        """
        self._entries = self._read_registry()
        discovered = self._loader.discover_plugins()

        # Index discovered plugins
        self._plugins = {p.manifest.name: p for p in discovered}

        # Auto-register new plugins found on disk
        for name, plugin in self._plugins.items():
            if name not in self._entries:
                self._entries[name] = PluginEntry(
                    name=name,
                    version=plugin.manifest.version,
                    source="builtin" if "builtin" in str(plugin.path) else "local",
                )

    def save(self) -> None:
        """Save registry to disk atomically (temp file + os.replace)."""
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "plugins": [
                {
                    "name": e.name,
                    "version": e.version,
                    "enabled": e.enabled,
                    "installed_at": e.installed_at,
                    "source": e.source,
                }
                for e in self._entries.values()
            ]
        }
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.plugins_dir), suffix=".tmp", prefix="registry_"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(self.registry_file))
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def get_enabled(self) -> list[LoadedPlugin]:
        """Return all enabled plugins that exist on disk."""
        return [
            self._plugins[name]
            for name, entry in self._entries.items()
            if entry.enabled and name in self._plugins
        ]

    def is_enabled(self, name: str) -> bool:
        """Check if a plugin is enabled."""
        entry = self._entries.get(name)
        return entry.enabled if entry else False

    def enable(self, name: str) -> bool:
        """Enable a plugin by name. Returns True if found."""
        entry = self._entries.get(name)
        if entry is None:
            return False
        entry.enabled = True
        return True

    def disable(self, name: str) -> bool:
        """Disable a plugin by name. Returns True if found."""
        entry = self._entries.get(name)
        if entry is None:
            return False
        entry.enabled = False
        return True

    def get_all_entries(self) -> list[PluginEntry]:
        """Return all registry entries."""
        return list(self._entries.values())

    def get_plugin(self, name: str) -> Optional[LoadedPlugin]:
        """Get a loaded plugin by name."""
        return self._plugins.get(name)
