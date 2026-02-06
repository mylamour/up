"""Memory storage backends: ChromaDB (vector) and JSON (keyword).

ChromaDB is the default for semantic search.
JSON is the fallback for fast operations or when ChromaDB is unavailable.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict

from up.memory.entry import MemoryEntry


def _check_chromadb() -> bool:
    """Check if chromadb is available."""
    try:
        import chromadb
        return True
    except ImportError:
        return False


def _ensure_chromadb():
    """Ensure ChromaDB is installed, provide helpful message if not."""
    if not _check_chromadb():
        raise ImportError(
            "ChromaDB is required for up-cli memory system.\n"
            "Install with: pip install up-cli[all]\n"
            "Or: pip install chromadb"
        )


class MemoryStore:
    """Abstract base for memory storage."""

    def add(self, entry: MemoryEntry) -> None:
        raise NotImplementedError

    def search(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        raise NotImplementedError

    def get_by_type(self, entry_type: str, limit: int = 10) -> List[MemoryEntry]:
        raise NotImplementedError

    def delete(self, entry_id: str) -> bool:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class ChromaMemoryStore(MemoryStore):
    """Memory store using ChromaDB with local embeddings.

    Uses ChromaDB's default embedding function (all-MiniLM-L6-v2).
    First initialization downloads the model (~100MB), which takes 30-60s.
    Subsequent loads are fast (2-5s).

    Storage location: .up/memory/chroma/
    """

    def __init__(self, workspace: Path):
        import chromadb

        self.workspace = workspace
        self.db_path = workspace / ".up" / "memory" / "chroma"
        self.db_path.mkdir(parents=True, exist_ok=True)

        is_first_time = not (self.db_path / "chroma.sqlite3").exists()

        if is_first_time:
            import sys
            print(
                "Initializing ChromaDB (first time setup)...\n"
                "Downloading embedding model (~100MB). This may take 30-60 seconds.",
                file=sys.stderr,
            )

        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        self.collection = self.client.get_or_create_collection(
            name="up_memory",
            metadata={"description": "Long-term memory for up-cli"},
        )

        if is_first_time:
            import sys
            print("ChromaDB ready!", file=sys.stderr)

    def add(self, entry: MemoryEntry) -> None:
        """Add entry to memory with auto-embedding."""
        metadata = {
            "type": entry.type,
            "timestamp": entry.timestamp,
            "branch": entry.branch or "unknown",
            "commit": entry.commit or "unknown",
            **{k: v for k, v in entry.metadata.items() if v is not None},
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}

        self.collection.add(
            ids=[entry.id],
            documents=[entry.content],
            metadatas=[metadata],
        )

    def search(
        self, query: str, limit: int = 5, entry_type: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Semantic search for relevant memories."""
        where = {"type": entry_type} if entry_type else None

        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,
        )

        entries = []
        if results and results["ids"]:
            for i, id_ in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                entries.append(
                    MemoryEntry(
                        id=id_,
                        type=meta.get("type", "unknown"),
                        content=results["documents"][0][i],
                        metadata=meta,
                        timestamp=meta.get("timestamp", ""),
                        branch=meta.get("branch"),
                        commit=meta.get("commit"),
                    )
                )

        return entries

    def get_by_type(self, entry_type: str, limit: int = 10) -> List[MemoryEntry]:
        """Get entries by type."""
        results = self.collection.get(
            where={"type": entry_type},
            limit=limit,
        )

        entries = []
        if results and results["ids"]:
            for i, id_ in enumerate(results["ids"]):
                meta = results["metadatas"][i]
                entries.append(
                    MemoryEntry(
                        id=id_,
                        type=entry_type,
                        content=results["documents"][i],
                        metadata=meta,
                        timestamp=meta.get("timestamp", ""),
                        branch=meta.get("branch"),
                        commit=meta.get("commit"),
                    )
                )

        return entries

    def delete(self, entry_id: str) -> bool:
        """Delete an entry."""
        try:
            self.collection.delete(ids=[entry_id])
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all memories."""
        self.client.delete_collection("up_memory")
        self.collection = self.client.create_collection(
            name="up_memory",
            metadata={"description": "Long-term memory for up-cli"},
        )

    def persist(self) -> None:
        """Persist to disk (automatic with PersistentClient)."""
        pass


class JSONMemoryStore(MemoryStore):
    """Simple JSON-based memory store with keyword search."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.db_path = workspace / ".up" / "memory"
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.db_path / "index.json"
        self.entries: Dict[str, MemoryEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load from disk."""
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text())
                for id_, entry_data in data.items():
                    self.entries[id_] = MemoryEntry(**entry_data)
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        """Save to disk."""
        data = {id_: entry.to_dict() for id_, entry in self.entries.items()}
        self.index_file.write_text(json.dumps(data, indent=2))

    def add(self, entry: MemoryEntry) -> None:
        """Add entry to memory."""
        self.entries[entry.id] = entry
        self._save()

    def search(
        self, query: str, limit: int = 5, entry_type: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Keyword-based search."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for entry in self.entries.values():
            if entry_type and entry.type != entry_type:
                continue

            content_lower = entry.content.lower()
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def get_by_type(self, entry_type: str, limit: int = 10) -> List[MemoryEntry]:
        """Get entries by type."""
        entries = [e for e in self.entries.values() if e.type == entry_type]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def delete(self, entry_id: str) -> bool:
        """Delete an entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save()
            return True
        return False

    def clear(self) -> None:
        """Clear all memories."""
        self.entries.clear()
        self._save()
