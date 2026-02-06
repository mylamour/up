"""Long-term memory system for up-cli.

Provides persistent memory across sessions using ChromaDB with local embeddings.
No external API required - uses sentence-transformers for embeddings.

Features:
- Session summaries
- Code learnings  
- Decision log
- Error memory
- Semantic search (vector-based)
- Auto-update on changes
- Branch/commit-aware knowledge tracking
- Version-specific memory retrieval

Storage:
- ChromaDB (default): Semantic/vector search with local embeddings
- JSON (fallback): Simple keyword search for fast operations

ChromaDB is installed automatically with up-cli.
First run may take 30-60s to download embedding model (~100MB).
"""

import json
import hashlib
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# ChromaDB is now a required dependency
def _check_chromadb():
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


def _get_git_context(workspace: Path) -> Dict[str, str]:
    """Get current git context (branch, commit, etc.).
    
    Returns dict with:
    - branch: Current branch name
    - commit: Current commit hash (short)
    - commit_full: Full commit hash
    - tag: Current tag if HEAD is tagged
    """
    context = {
        "branch": "unknown",
        "commit": "unknown",
        "commit_full": "unknown",
        "tag": None,
    }
    
    try:
        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            context["branch"] = result.stdout.strip()
        
        # Get current commit (short)
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            context["commit"] = result.stdout.strip()
        
        # Get full commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            context["commit_full"] = result.stdout.strip()
        
        # Get tag if exists
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            context["tag"] = result.stdout.strip()
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return context


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class MemoryEntry:
    """A single memory entry with git context."""
    id: str
    type: str  # 'session', 'learning', 'decision', 'error', 'code', 'commit'
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # Git context - automatically populated
    branch: Optional[str] = None
    commit: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionSummary:
    """Summary of an AI session."""
    session_id: str
    started_at: str
    ended_at: str
    summary: str
    tasks_completed: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)


@dataclass  
class CodeLearning:
    """A learning extracted from code changes."""
    pattern: str
    description: str
    example: str
    file_path: str
    commit_hash: Optional[str] = None


@dataclass
class ErrorMemory:
    """Memory of an error and its solution."""
    error_type: str
    error_message: str
    context: str
    solution: str
    prevention: str


# =============================================================================
# Memory Store (Abstract)
# =============================================================================

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


# =============================================================================
# ChromaDB Implementation (Vector Search)
# =============================================================================

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
        
        # Check if this is first-time initialization
        is_first_time = not (self.db_path / "chroma.sqlite3").exists()
        
        if is_first_time:
            import sys
            print(
                "Initializing ChromaDB (first time setup)...\n"
                "Downloading embedding model (~100MB). This may take 30-60 seconds.",
                file=sys.stderr
            )
        
        # Initialize ChromaDB with persistent storage (new API)
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        
        # Get or create collection (uses default embedding function)
        self.collection = self.client.get_or_create_collection(
            name="up_memory",
            metadata={"description": "Long-term memory for up-cli"}
        )
        
        if is_first_time:
            import sys
            print("ChromaDB ready!", file=sys.stderr)
    
    def add(self, entry: MemoryEntry) -> None:
        """Add entry to memory with auto-embedding."""
        # Build metadata including branch/commit context
        metadata = {
            "type": entry.type,
            "timestamp": entry.timestamp,
            "branch": entry.branch or "unknown",
            "commit": entry.commit or "unknown",
            **{k: v for k, v in entry.metadata.items() if v is not None}
        }
        
        # ChromaDB doesn't allow None values in metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        self.collection.add(
            ids=[entry.id],
            documents=[entry.content],
            metadatas=[metadata]
        )
    
    def search(self, query: str, limit: int = 5, 
               entry_type: Optional[str] = None) -> List[MemoryEntry]:
        """Semantic search for relevant memories."""
        where = {"type": entry_type} if entry_type else None
        
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where
        )
        
        entries = []
        if results and results['ids']:
            for i, id_ in enumerate(results['ids'][0]):
                meta = results['metadatas'][0][i]
                entries.append(MemoryEntry(
                    id=id_,
                    type=meta.get('type', 'unknown'),
                    content=results['documents'][0][i],
                    metadata=meta,
                    timestamp=meta.get('timestamp', ''),
                    branch=meta.get('branch'),
                    commit=meta.get('commit'),
                ))
        
        return entries
    
    def get_by_type(self, entry_type: str, limit: int = 10) -> List[MemoryEntry]:
        """Get entries by type."""
        results = self.collection.get(
            where={"type": entry_type},
            limit=limit
        )
        
        entries = []
        if results and results['ids']:
            for i, id_ in enumerate(results['ids']):
                meta = results['metadatas'][i]
                entries.append(MemoryEntry(
                    id=id_,
                    type=entry_type,
                    content=results['documents'][i],
                    metadata=meta,
                    timestamp=meta.get('timestamp', ''),
                    branch=meta.get('branch'),
                    commit=meta.get('commit'),
                ))
        
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
            metadata={"description": "Long-term memory for up-cli"}
        )
    
    def persist(self) -> None:
        """Persist to disk (automatic with PersistentClient)."""
        # PersistentClient auto-persists, but we keep method for API compatibility
        pass


# =============================================================================
# JSON Implementation (Fallback - No Dependencies)
# =============================================================================

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
    
    def search(self, query: str, limit: int = 5,
               entry_type: Optional[str] = None) -> List[MemoryEntry]:
        """Keyword-based search."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored = []
        for entry in self.entries.values():
            if entry_type and entry.type != entry_type:
                continue
            
            content_lower = entry.content.lower()
            # Simple scoring: count matching words
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                scored.append((score, entry))
        
        # Sort by score descending
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


# =============================================================================
# Memory Manager (Main Interface)
# =============================================================================

class MemoryManager:
    """Main interface for the memory system.
    
    Uses ChromaDB for semantic search with local embeddings.
    Falls back to JSON only if explicitly requested (use_vectors=False).
    
    Knowledge Tracking:
    - Every memory entry is tagged with the current branch and commit
    - Search can be filtered by branch to get branch-specific knowledge
    - Compare knowledge across branches (what was learned on feature-x?)
    - Track when knowledge was created relative to commits
    
    First-time initialization:
    - ChromaDB will download embedding model (~100MB) on first use
    - This takes 30-60 seconds, subsequent loads are fast (2-5s)
    """
    
    def __init__(self, workspace: Optional[Path] = None, use_vectors: bool = True):
        self.workspace = workspace or Path.cwd()
        
        # ChromaDB is the default (required dependency)
        # JSON is only used when explicitly requested for fast operations
        if use_vectors:
            if _check_chromadb():
                try:
                    self.store = ChromaMemoryStore(self.workspace)
                    self._backend = "chromadb"
                except Exception as e:
                    # Fall back to JSON if ChromaDB fails (e.g., corrupted DB)
                    import sys
                    print(f"Warning: ChromaDB failed ({e}), using JSON fallback", file=sys.stderr)
                    self.store = JSONMemoryStore(self.workspace)
                    self._backend = "json"
            else:
                # ChromaDB not installed - show helpful message
                import sys
                print(
                    "Note: ChromaDB not found. Using JSON (keyword search).\n"
                    "For semantic search, install: pip install chromadb",
                    file=sys.stderr
                )
                self.store = JSONMemoryStore(self.workspace)
                self._backend = "json"
        else:
            # Explicitly requested JSON (fast mode)
            self.store = JSONMemoryStore(self.workspace)
            self._backend = "json"
        
        self.config_file = self.workspace / ".up" / "memory_config.json"
        self.config = self._load_config()
        
        # Cache git context (refreshed on demand)
        self._git_context_cache: Optional[Dict[str, str]] = None
        self._git_context_time: Optional[datetime] = None
    
    def _load_config(self) -> dict:
        """Load configuration."""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "auto_index_commits": True,
            "auto_summarize_sessions": True,
            "max_entries_per_type": 100,
            "track_branches": True,  # Track branch context
        }
    
    def _save_config(self) -> None:
        """Save configuration."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(self.config, indent=2))
    
    def _generate_id(self, prefix: str, content: str) -> str:
        """Generate unique ID for entry."""
        hash_input = f"{prefix}:{content}:{datetime.now().isoformat()}"
        return f"{prefix}_{hashlib.md5(hash_input.encode()).hexdigest()[:12]}"
    
    def _get_git_context(self, force_refresh: bool = False) -> Dict[str, str]:
        """Get current git context with caching.
        
        Caches for 60 seconds to avoid repeated git calls.
        """
        now = datetime.now()
        
        # Use cache if fresh (within 60 seconds)
        if (not force_refresh 
            and self._git_context_cache 
            and self._git_context_time
            and (now - self._git_context_time).seconds < 60):
            return self._git_context_cache
        
        # Refresh cache
        self._git_context_cache = _get_git_context(self.workspace)
        self._git_context_time = now
        
        return self._git_context_cache
    
    def _create_entry_with_context(
        self, 
        prefix: str, 
        entry_type: str, 
        content: str,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Create a memory entry with automatic git context."""
        git_ctx = self._get_git_context()
        
        metadata = extra_metadata or {}
        metadata["session"] = self._get_current_session_id()
        
        return MemoryEntry(
            id=self._generate_id(prefix, content),
            type=entry_type,
            content=content,
            metadata=metadata,
            branch=git_ctx["branch"],
            commit=git_ctx["commit"],
        )
    
    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------
    
    def start_session(self) -> str:
        """Start a new session and return session ID."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session_file = self.workspace / ".up" / "current_session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "tasks": [],
            "files_modified": [],
            "decisions": [],
            "learnings": [],
            "errors": [],
        }, indent=2))
        
        return session_id
    
    def end_session(self, summary: str = None) -> None:
        """End current session and save summary to memory."""
        session_file = self.workspace / ".up" / "current_session.json"
        
        if not session_file.exists():
            return
        
        session_data = json.loads(session_file.read_text())
        session_id = session_data.get("session_id", "unknown")
        
        # Auto-generate summary if not provided
        if not summary:
            summary = self._auto_summarize_session(session_data)
        
        # Create memory entry
        entry = MemoryEntry(
            id=session_id,
            type="session",
            content=summary,
            metadata={
                "started_at": session_data.get("started_at"),
                "ended_at": datetime.now().isoformat(),
                "tasks_count": len(session_data.get("tasks", [])),
                "files_count": len(session_data.get("files_modified", [])),
            }
        )
        
        self.store.add(entry)
        
        # Clean up session file
        session_file.unlink()
    
    def _auto_summarize_session(self, session_data: dict) -> str:
        """Generate automatic session summary."""
        parts = []
        
        tasks = session_data.get("tasks", [])
        if tasks:
            parts.append(f"Completed tasks: {', '.join(tasks)}")
        
        files = session_data.get("files_modified", [])
        if files:
            parts.append(f"Modified files: {', '.join(files[:5])}")
            if len(files) > 5:
                parts.append(f"  ...and {len(files) - 5} more")
        
        decisions = session_data.get("decisions", [])
        if decisions:
            parts.append(f"Key decisions: {'; '.join(decisions)}")
        
        learnings = session_data.get("learnings", [])
        if learnings:
            parts.append(f"Learnings: {'; '.join(learnings)}")
        
        return "\n".join(parts) if parts else "Session with no recorded activity."
    
    def record_task(self, task: str) -> None:
        """Record a completed task in current session."""
        self._update_session("tasks", task)
    
    def record_file(self, file_path: str) -> None:
        """Record a modified file in current session."""
        self._update_session("files_modified", file_path)
    
    def record_decision(self, decision: str) -> None:
        """Record a decision in current session with git context."""
        self._update_session("decisions", decision)
        
        # Also add to long-term memory with branch/commit context
        entry = self._create_entry_with_context(
            prefix="decision",
            entry_type="decision",
            content=decision,
        )
        self.store.add(entry)
    
    def record_learning(self, learning: str) -> None:
        """Record a learning in current session with git context."""
        self._update_session("learnings", learning)
        
        # Also add to long-term memory with branch/commit context
        entry = self._create_entry_with_context(
            prefix="learning",
            entry_type="learning",
            content=learning,
        )
        self.store.add(entry)
    
    def record_error(self, error: str, solution: str = None) -> None:
        """Record an error and optional solution with git context."""
        content = f"Error: {error}"
        if solution:
            content += f"\nSolution: {solution}"
        
        self._update_session("errors", error)
        
        entry = self._create_entry_with_context(
            prefix="error",
            entry_type="error",
            content=content,
            extra_metadata={
                "error": error,
                "solution": solution,
            }
        )
        self.store.add(entry)
    
    def _update_session(self, key: str, value: str) -> None:
        """Update current session data."""
        session_file = self.workspace / ".up" / "current_session.json"
        
        if session_file.exists():
            data = json.loads(session_file.read_text())
            if key not in data:
                data[key] = []
            if value not in data[key]:
                data[key].append(value)
            session_file.write_text(json.dumps(data, indent=2))
    
    def _get_current_session_id(self) -> str:
        """Get current session ID."""
        session_file = self.workspace / ".up" / "current_session.json"
        if session_file.exists():
            data = json.loads(session_file.read_text())
            return data.get("session_id", "unknown")
        return "no_session"
    
    # -------------------------------------------------------------------------
    # Auto-Update from Git
    # -------------------------------------------------------------------------
    
    def index_recent_commits(self, count: int = 10) -> int:
        """Index recent git commits into memory with branch context.
        
        Each commit is tagged with the branch it was indexed from.
        This allows tracking which branches contain which knowledge.
        """
        if not self.config.get("auto_index_commits", True):
            return 0
        
        try:
            # Get current branch for context
            git_ctx = self._get_git_context(force_refresh=True)
            current_branch = git_ctx["branch"]
            
            # Get commit log with more details
            result = subprocess.run(
                ["git", "log", f"-{count}", 
                 "--pretty=format:%H|%h|%s|%b|%D|||"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return 0
            
            indexed = 0
            commits = result.stdout.split("|||")
            
            for commit in commits:
                if not commit.strip():
                    continue
                
                parts = commit.strip().split("|", 4)
                if len(parts) < 3:
                    continue
                
                commit_hash_full = parts[0]
                commit_hash = parts[1]
                subject = parts[2]
                body = parts[3] if len(parts) > 3 else ""
                refs = parts[4] if len(parts) > 4 else ""
                
                entry_id = f"commit_{commit_hash}"
                
                # Check if already indexed
                existing = self.store.search(commit_hash, limit=1)
                if existing and any(e.id == entry_id for e in existing):
                    continue
                
                content = f"Commit {commit_hash}: {subject}"
                if body.strip():
                    content += f"\n\n{body.strip()}"
                
                # Parse refs to find associated branches/tags
                branches_in_commit = []
                tags_in_commit = []
                if refs:
                    for ref in refs.split(", "):
                        ref = ref.strip()
                        if ref.startswith("tag:"):
                            tags_in_commit.append(ref[4:].strip())
                        elif ref and not ref.startswith("HEAD"):
                            branches_in_commit.append(ref)
                
                # Convert lists to strings (ChromaDB doesn't accept lists)
                entry = MemoryEntry(
                    id=entry_id,
                    type="commit",
                    content=content,
                    metadata={
                        "hash": commit_hash,
                        "hash_full": commit_hash_full,
                        "subject": subject,
                        "branches": ", ".join(branches_in_commit) if branches_in_commit else "",
                        "tags": ", ".join(tags_in_commit) if tags_in_commit else "",
                    },
                    branch=current_branch,
                    commit=commit_hash,
                )
                self.store.add(entry)
                indexed += 1
            
            return indexed
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0
    
    def index_file_changes(self) -> int:
        """Index recent file changes."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~5..HEAD"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return 0
            
            files = result.stdout.strip().split("\n")
            indexed = 0
            
            for file_path in files:
                if not file_path.strip():
                    continue
                
                full_path = self.workspace / file_path
                if not full_path.exists():
                    continue
                
                # Only index code files
                if full_path.suffix not in {'.py', '.js', '.ts', '.tsx', '.go', '.rs'}:
                    continue
                
                try:
                    content = full_path.read_text()[:2000]  # First 2000 chars
                except Exception:
                    continue
                
                entry_id = f"file_{hashlib.md5(file_path.encode()).hexdigest()[:12]}"
                
                entry = MemoryEntry(
                    id=entry_id,
                    type="code",
                    content=f"File: {file_path}\n\n{content}",
                    metadata={"path": file_path}
                )
                self.store.add(entry)
                indexed += 1
            
            return indexed
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return 0
    
    # -------------------------------------------------------------------------
    # Search & Retrieval
    # -------------------------------------------------------------------------
    
    def search(self, query: str, limit: int = 5, 
               entry_type: Optional[str] = None,
               branch: Optional[str] = None) -> List[MemoryEntry]:
        """Search memory for relevant entries.
        
        Args:
            query: Search query
            limit: Max results
            entry_type: Filter by type (learning, decision, error, etc.)
            branch: Filter by branch (None = all branches)
        """
        results = self.store.search(query, limit * 2 if branch else limit, entry_type)
        
        # Filter by branch if specified
        if branch:
            results = [e for e in results if e.branch == branch][:limit]
        
        return results
    
    def search_on_branch(self, query: str, branch: str, limit: int = 5) -> List[MemoryEntry]:
        """Search for knowledge on a specific branch."""
        return self.search(query, limit, branch=branch)
    
    def search_current_branch(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """Search for knowledge on the current branch only."""
        git_ctx = self._get_git_context()
        return self.search(query, limit, branch=git_ctx["branch"])
    
    def recall(self, topic: str, branch: Optional[str] = None) -> str:
        """Recall information about a topic (returns formatted text).
        
        Args:
            topic: Topic to recall
            branch: Optional branch filter (None = all branches)
        """
        entries = self.search(topic, limit=5, branch=branch)
        
        if not entries:
            branch_info = f" on branch '{branch}'" if branch else ""
            return f"No memories found about '{topic}'{branch_info}."
        
        lines = [f"Memories about '{topic}':\n"]
        for entry in entries:
            branch_tag = f" @{entry.branch}" if entry.branch else ""
            lines.append(f"[{entry.type}]{branch_tag} {entry.content[:200]}...")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_branch_knowledge(self, branch: str) -> Dict[str, List[MemoryEntry]]:
        """Get all knowledge recorded on a specific branch.
        
        Returns dict organized by type:
        {
            "learnings": [...],
            "decisions": [...],
            "errors": [...],
            "commits": [...],
        }
        """
        result = {
            "learnings": [],
            "decisions": [],
            "errors": [],
            "commits": [],
        }
        
        for entry_type in result.keys():
            entries = self.store.get_by_type(entry_type[:-1] if entry_type.endswith("s") else entry_type, 100)
            result[entry_type] = [e for e in entries if e.branch == branch]
        
        return result
    
    def compare_branches(self, branch1: str, branch2: str) -> Dict[str, Any]:
        """Compare knowledge between two branches.
        
        Useful for seeing what was learned on a feature branch
        that isn't on main yet.
        """
        knowledge1 = self.get_branch_knowledge(branch1)
        knowledge2 = self.get_branch_knowledge(branch2)
        
        return {
            "branch1": {
                "name": branch1,
                "total": sum(len(v) for v in knowledge1.values()),
                "learnings": len(knowledge1["learnings"]),
                "decisions": len(knowledge1["decisions"]),
            },
            "branch2": {
                "name": branch2,
                "total": sum(len(v) for v in knowledge2.values()),
                "learnings": len(knowledge2["learnings"]),
                "decisions": len(knowledge2["decisions"]),
            },
            "unique_to_branch1": {
                "learnings": [e for e in knowledge1["learnings"] 
                             if e.content not in [x.content for x in knowledge2["learnings"]]],
                "decisions": [e for e in knowledge1["decisions"]
                             if e.content not in [x.content for x in knowledge2["decisions"]]],
            },
            "unique_to_branch2": {
                "learnings": [e for e in knowledge2["learnings"]
                             if e.content not in [x.content for x in knowledge1["learnings"]]],
                "decisions": [e for e in knowledge2["decisions"]
                             if e.content not in [x.content for x in knowledge1["decisions"]]],
            },
        }
    
    def get_recent_sessions(self, limit: int = 5) -> List[MemoryEntry]:
        """Get recent session summaries."""
        return self.store.get_by_type("session", limit)
    
    def get_learnings(self, limit: int = 10, branch: Optional[str] = None) -> List[MemoryEntry]:
        """Get recorded learnings, optionally filtered by branch."""
        entries = self.store.get_by_type("learning", limit * 2 if branch else limit)
        if branch:
            entries = [e for e in entries if e.branch == branch][:limit]
        return entries
    
    def get_decisions(self, limit: int = 10, branch: Optional[str] = None) -> List[MemoryEntry]:
        """Get recorded decisions, optionally filtered by branch."""
        entries = self.store.get_by_type("decision", limit * 2 if branch else limit)
        if branch:
            entries = [e for e in entries if e.branch == branch][:limit]
        return entries
    
    def get_errors(self, limit: int = 10, branch: Optional[str] = None) -> List[MemoryEntry]:
        """Get recorded errors, optionally filtered by branch."""
        entries = self.store.get_by_type("error", limit * 2 if branch else limit)
        if branch:
            entries = [e for e in entries if e.branch == branch][:limit]
        return entries
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get current git context and relevant memories."""
        git_ctx = self._get_git_context(force_refresh=True)
        
        return {
            "branch": git_ctx["branch"],
            "commit": git_ctx["commit"],
            "tag": git_ctx.get("tag"),
            "branch_learnings": len(self.get_learnings(100, branch=git_ctx["branch"])),
            "branch_decisions": len(self.get_decisions(100, branch=git_ctx["branch"])),
            "total_memories": self.get_stats()["total"],
        }
    
    # -------------------------------------------------------------------------
    # Management
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> dict:
        """Get memory statistics including branch info."""
        # Get entries by type
        all_entries = []
        for entry_type in ["session", "learning", "decision", "error", "commit", "code"]:
            all_entries.extend(self.store.get_by_type(entry_type, 1000))
        
        # Count branches
        branches = {}
        for entry in all_entries:
            branch = entry.branch or "unknown"
            if branch not in branches:
                branches[branch] = 0
            branches[branch] += 1
        
        # Current context
        git_ctx = self._get_git_context()
        
        stats = {
            "backend": self._backend,
            "sessions": len(self.store.get_by_type("session", 1000)),
            "learnings": len(self.store.get_by_type("learning", 1000)),
            "decisions": len(self.store.get_by_type("decision", 1000)),
            "errors": len(self.store.get_by_type("error", 1000)),
            "commits": len(self.store.get_by_type("commit", 1000)),
            "code_files": len(self.store.get_by_type("code", 1000)),
            "branches": branches,
            "branch_count": len(branches),
            "current_branch": git_ctx["branch"],
            "current_commit": git_ctx["commit"],
        }
        stats["total"] = sum(v for k, v in stats.items() if isinstance(v, int) and k not in ["branch_count"])
        return stats
    
    def clear(self) -> None:
        """Clear all memory."""
        self.store.clear()
    
    def sync(self) -> dict:
        """Sync memory with current state (index commits, files, etc.)."""
        results = {
            "commits_indexed": self.index_recent_commits(),
            "files_indexed": self.index_file_changes(),
        }
        return results


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI for memory system."""
    import sys
    
    manager = MemoryManager()
    
    if len(sys.argv) < 2:
        print("Usage: python memory.py <command> [args]")
        print("\nCommands:")
        print("  search <query>     Search memory")
        print("  recall <topic>     Recall information")
        print("  stats              Show statistics")
        print("  sync               Sync with git")
        print("  clear              Clear all memory")
        print("  start-session      Start new session")
        print("  end-session        End current session")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = manager.search(query)
        for entry in results:
            print(f"[{entry.type}] {entry.content[:100]}...")
            print()
    
    elif cmd == "recall" and len(sys.argv) > 2:
        topic = " ".join(sys.argv[2:])
        print(manager.recall(topic))
    
    elif cmd == "stats":
        stats = manager.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif cmd == "sync":
        results = manager.sync()
        print(f"Indexed {results['commits_indexed']} commits")
        print(f"Indexed {results['files_indexed']} files")
    
    elif cmd == "clear":
        manager.clear()
        print("Memory cleared.")
    
    elif cmd == "start-session":
        session_id = manager.start_session()
        print(f"Started session: {session_id}")
    
    elif cmd == "end-session":
        summary = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
        manager.end_session(summary)
        print("Session ended and saved to memory.")
    
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
