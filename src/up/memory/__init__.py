"""Long-term memory system for up-cli.

Split from the original 1097-line memory.py into:
- entry.py: Data models (MemoryEntry, SessionSummary, etc.)
- stores.py: Storage backends (ChromaMemoryStore, JSONMemoryStore)
- _manager.py: MemoryManager class (core CRUD, search, indexing)

All public symbols are re-exported here for backward compatibility.
"""

# Re-export everything from the manager module (backward compat)
from up.memory._manager import (
    MemoryManager,
    MemoryEntry,
    SessionSummary,
    CodeLearning,
    ErrorMemory,
    MemoryStore,
    ChromaMemoryStore,
    JSONMemoryStore,
    _check_chromadb,
    _ensure_chromadb,
    _get_git_context,
)

__all__ = [
    "MemoryManager",
    "MemoryEntry",
    "SessionSummary",
    "CodeLearning",
    "ErrorMemory",
    "MemoryStore",
    "ChromaMemoryStore",
    "JSONMemoryStore",
    "_check_chromadb",
    "_ensure_chromadb",
    "_get_git_context",
]
