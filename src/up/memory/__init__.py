"""Long-term memory system for up-cli.

Split from the original 1097-line memory.py into:
- entry.py: Data models (MemoryEntry, SessionSummary, etc.)
- stores.py: Storage backends (ChromaMemoryStore, JSONMemoryStore)
- _manager.py: MemoryManager class (core CRUD, search, indexing)

All public symbols are re-exported here for backward compatibility.
"""

# Data models (canonical source: entry.py)
from up.memory.entry import (
    MemoryEntry,
    SessionSummary,
    CodeLearning,
    ErrorMemory,
    get_git_context,
)

# Storage backends (canonical source: stores.py)
from up.memory.stores import (
    _check_chromadb,
    _ensure_chromadb,
    MemoryStore,
    ChromaMemoryStore,
    JSONMemoryStore,
)

# Manager (canonical source: _manager.py)
from up.memory._manager import MemoryManager

# Backward-compat alias
_get_git_context = get_git_context

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
    "get_git_context",
]
