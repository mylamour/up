"""Plugin marketplace registry.

Catalogs available plugins (local and remote) with metadata,
categories, and version tracking.
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MarketplaceEntry:
    """A plugin entry in the marketplace catalog."""

    name: str
    description: str = ""
    version: str = "0.0.0"
    author: str = ""
    source: str = "local"
    category: str = "productivity"
    downloads: int = 0
    rating: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MarketplaceEntry":
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in fields})


class Marketplace:
    """Plugin marketplace registry — local-first with optional remote."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._entries: dict[str, MarketplaceEntry] = {}
        self._registry_path = workspace / ".up" / "plugins" / "marketplace.json"

    def load(self) -> None:
        """Load from disk and auto-discover local plugins."""
        self._load_from_disk()
        self._scan_local()

    def _load_from_disk(self) -> None:
        if self._registry_path.exists():
            try:
                data = json.loads(self._registry_path.read_text())
                for entry_data in data.get("entries", []):
                    e = MarketplaceEntry.from_dict(entry_data)
                    self._entries[e.name] = e
            except Exception:
                logger.warning("Failed to load marketplace.json")

    def _scan_local(self) -> None:
        """Scan installed/ and builtin/ for plugins not yet in registry."""
        for base_name in ("installed", "builtin"):
            base = self.workspace / ".up" / "plugins" / base_name
            if not base.is_dir():
                # Also check src layout
                base = self.workspace / "src" / "up" / "plugins" / base_name
            if not base.is_dir():
                continue
            for plugin_dir in sorted(base.iterdir()):
                manifest = plugin_dir / "plugin.json"
                if not manifest.exists():
                    continue
                try:
                    data = json.loads(manifest.read_text())
                    name = data.get("name", plugin_dir.name)
                    if name not in self._entries:
                        self._entries[name] = MarketplaceEntry(
                            name=name,
                            description=data.get("description", ""),
                            version=data.get("version", "0.0.0"),
                            author=data.get("author", ""),
                            source=base_name,
                            category=data.get("category", "productivity"),
                        )
                except Exception:
                    continue

    def save(self) -> None:
        """Persist registry to disk."""
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"entries": [e.to_dict() for e in self._entries.values()]}
        self._registry_path.write_text(json.dumps(data, indent=2))

    def search(self, query: str) -> list[MarketplaceEntry]:
        """Search by name and description."""
        q = query.lower()
        return [
            e for e in self._entries.values()
            if q in e.name.lower() or q in e.description.lower()
        ]

    def search_by_category(self, category: str) -> list[MarketplaceEntry]:
        """Filter by category."""
        return [
            e for e in self._entries.values()
            if e.category.lower() == category.lower()
        ]

    def get(self, name: str) -> MarketplaceEntry | None:
        """Get a specific entry by name."""
        return self._entries.get(name)

    def add(self, entry: MarketplaceEntry) -> None:
        """Add or update an entry."""
        self._entries[entry.name] = entry

    def remove(self, name: str) -> bool:
        """Remove an entry. Returns True if found."""
        if name in self._entries:
            del self._entries[name]
            return True
        return False

    def list_all(self) -> list[MarketplaceEntry]:
        """Return all entries."""
        return list(self._entries.values())
