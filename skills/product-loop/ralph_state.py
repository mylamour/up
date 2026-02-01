#!/usr/bin/env python3
"""
Ralph State Utilities

Unified interface for managing Ralph Hybrid state files.
Provides schemas, validation, and convenience functions.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# State File Paths
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StateFiles:
    """Paths to all Ralph state files."""
    base_dir: Path

    @property
    def circuit_breaker(self) -> Path:
        return self.base_dir / ".circuit_breaker_state"

    @property
    def rate_limiter(self) -> Path:
        return self.base_dir / ".rate_limiter_state"

    @property
    def response_analysis(self) -> Path:
        return self.base_dir / ".response_analysis"

    @property
    def exit_signals(self) -> Path:
        return self.base_dir / ".exit_signals"

    @property
    def session(self) -> Path:
        return self.base_dir / ".claude_session_id"

    @property
    def log(self) -> Path:
        return self.base_dir / "ralph_hybrid.log"

    @property
    def last_output(self) -> Path:
        return self.base_dir / "last_output.txt"


# ═══════════════════════════════════════════════════════════════════════════════
# PRD Schema (Optional - for structured task management)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UserStory:
    """PRD User Story schema."""
    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    priority: int = 1
    passes: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "acceptanceCriteria": self.acceptance_criteria,
            "priority": self.priority,
            "passes": self.passes,
            "notes": self.notes,
        }


@dataclass
class PRD:
    """Product Requirements Document schema."""
    project: str
    branch_name: str
    description: str
    user_stories: list[UserStory]

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "branchName": self.branch_name,
            "description": self.description,
            "userStories": [s.to_dict() for s in self.user_stories],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "PRD":
        data = json.loads(path.read_text())
        stories = [
            UserStory(
                id=s["id"],
                title=s["title"],
                description=s["description"],
                acceptance_criteria=s.get("acceptanceCriteria", []),
                priority=s.get("priority", 1),
                passes=s.get("passes", False),
                notes=s.get("notes", ""),
            )
            for s in data.get("userStories", [])
        ]
        return cls(
            project=data["project"],
            branch_name=data.get("branchName", "main"),
            description=data.get("description", ""),
            user_stories=stories,
        )

    def next_story(self) -> Optional[UserStory]:
        """Get next incomplete story by priority."""
        incomplete = [s for s in self.user_stories if not s.passes]
        if not incomplete:
            return None
        return min(incomplete, key=lambda s: s.priority)

    def mark_complete(self, story_id: str, notes: str = "") -> bool:
        """Mark a story as complete."""
        for story in self.user_stories:
            if story.id == story_id:
                story.passes = True
                if notes:
                    story.notes = notes
                return True
        return False

    @property
    def progress(self) -> tuple[int, int]:
        """Return (completed, total) counts."""
        total = len(self.user_stories)
        completed = sum(1 for s in self.user_stories if s.passes)
        return completed, total


# ═══════════════════════════════════════════════════════════════════════════════
# State Manager
# ═══════════════════════════════════════════════════════════════════════════════

class RalphStateManager:
    """Unified state management for Ralph Hybrid."""

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()
        self.state_dir = self.workspace / ".ralph"
        self.files = StateFiles(self.state_dir)

    def init(self) -> None:
        """Initialize state directory."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def reset_all(self) -> None:
        """Reset all state files."""
        import shutil
        if self.state_dir.exists():
            shutil.rmtree(self.state_dir)
        self.init()

    def get_summary(self) -> dict:
        """Get summary of all state."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "workspace": str(self.workspace),
        }

        # Circuit breaker
        if self.files.circuit_breaker.exists():
            try:
                cb = json.loads(self.files.circuit_breaker.read_text())
                summary["circuit_breaker"] = {
                    "state": cb.get("state", "UNKNOWN"),
                    "no_progress_count": cb.get("no_progress_count", 0),
                }
            except json.JSONDecodeError:
                summary["circuit_breaker"] = {"error": "Invalid JSON"}

        # Rate limiter
        if self.files.rate_limiter.exists():
            try:
                rl = json.loads(self.files.rate_limiter.read_text())
                summary["rate_limiter"] = {
                    "calls_this_hour": rl.get("calls_this_hour", 0),
                    "total_calls": rl.get("total_calls", 0),
                }
            except json.JSONDecodeError:
                summary["rate_limiter"] = {"error": "Invalid JSON"}

        # Last analysis
        if self.files.response_analysis.exists():
            try:
                ra = json.loads(self.files.response_analysis.read_text())
                summary["last_analysis"] = {
                    "status": ra.get("status", {}).get("status", "UNKNOWN"),
                    "exit_signal": ra.get("status", {}).get("exit_signal", False),
                    "should_exit": ra.get("indicators", {}).get("should_exit", False),
                }
            except json.JSONDecodeError:
                summary["last_analysis"] = {"error": "Invalid JSON"}

        return summary


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    manager = RalphStateManager()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "init":
            manager.init()
            print("State directory initialized")
        elif cmd == "reset":
            manager.reset_all()
            print("All state reset")
        elif cmd == "summary":
            print(json.dumps(manager.get_summary(), indent=2))
        else:
            print(f"Unknown command: {cmd}")
    else:
        print(json.dumps(manager.get_summary(), indent=2))
