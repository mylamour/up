"""Memory data models and git context helper.

Data classes for memory entries, sessions, learnings, and errors.
"""

import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


def get_git_context(workspace: Path) -> Dict[str, str]:
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
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            context["branch"] = result.stdout.strip()

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            context["commit"] = result.stdout.strip()

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            context["commit_full"] = result.stdout.strip()

        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            cwd=workspace, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            context["tag"] = result.stdout.strip()

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return context


@dataclass
class MemoryEntry:
    """A single memory entry with git context."""
    id: str
    type: str  # 'session', 'learning', 'decision', 'error', 'code', 'commit'
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
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
