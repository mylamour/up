"""Event system for up-cli lifecycle integration.

Provides event-driven communication between systems:
- Memory
- Docs
- Learn
- Product Loop

Events flow through a central bridge that dispatches to handlers.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Core event types in the lifecycle."""

    # Git events
    GIT_COMMIT = "git.commit"
    GIT_PUSH = "git.push"

    # File events
    FILE_CHANGED = "file.changed"
    FILE_CREATED = "file.created"
    FILE_DELETED = "file.deleted"

    # Session events
    SESSION_START = "session.start"
    SESSION_END = "session.end"
    SESSION_ACTIVITY = "session.activity"

    # Task events
    TASK_START = "task.start"
    TASK_COMPLETE = "task.complete"
    TASK_FAILED = "task.failed"
    TASK_BLOCKED = "task.blocked"

    # Error events
    ERROR_OCCURRED = "error.occurred"
    ERROR_FIXED = "error.fixed"

    # Learning events
    LEARNING_DISCOVERED = "learning.discovered"
    LEARNING_NEEDED = "learning.needed"
    PATTERN_DETECTED = "pattern.detected"

    # Decision events
    DECISION_MADE = "decision.made"

    # Milestone events
    MILESTONE_REACHED = "milestone.reached"

    # System events
    SYNC_REQUESTED = "sync.requested"
    CONTEXT_UPDATED = "context.updated"

    # Hook pipeline events (for plugin system)
    PRE_TOOL_USE = "hook.pre_tool_use"
    POST_TOOL_USE = "hook.post_tool_use"
    PRE_EXECUTE = "hook.pre_execute"
    POST_EXECUTE = "hook.post_execute"


@dataclass
class Event:
    """An event in the lifecycle system."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
        }


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBridge:
    """Central event bridge that dispatches events to handlers.
    
    Implements a simple pub/sub pattern for loose coupling between systems.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern - one bridge per process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, workspace: Path | None = None):
        if self._initialized:
            return

        self.workspace = workspace or Path.cwd()
        self.handlers: dict[EventType, list[EventHandler]] = {}
        self.event_log: list[Event] = []
        self.config = self._load_config()
        self._initialized = True

    def _load_config(self) -> dict:
        """Load automation configuration."""
        config_file = self.workspace / ".up" / "config.json"
        if config_file.exists():
            try:
                return json.loads(config_file.read_text())
            except json.JSONDecodeError:
                pass

        # Default configuration
        return {
            "automation": {
                "memory": {
                    "auto_index_commits": True,
                    "auto_record_tasks": True,
                    "auto_record_errors": True,
                    "session_timeout_minutes": 30,
                },
                "docs": {
                    "auto_update_context": True,
                    "auto_update_handoff": True,
                    "auto_changelog_on_milestone": True,
                },
                "learn": {
                    "auto_trigger_on_repeated_error": True,
                    "auto_trigger_threshold": 2,
                },
            }
        }

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self.handlers:
            self.handlers[event_type] = [
                h for h in self.handlers[event_type] if h != handler
            ]

    def emit(self, event: Event) -> None:
        """Emit an event to all subscribed handlers."""
        # Log event
        self.event_log.append(event)
        if len(self.event_log) > 100:
            self.event_log = self.event_log[-100:]

        # Dispatch to handlers
        if event.type in self.handlers:
            for handler in self.handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    # Log but don't fail on handler errors
                    logger.warning("Event handler error for %s: %s", event.type, e)

    def emit_simple(
        self,
        event_type: EventType,
        source: str = "unknown",
        **data
    ) -> None:
        """Convenience method to emit an event with data."""
        event = Event(type=event_type, data=data, source=source)
        self.emit(event)

    def get_recent_events(self, limit: int = 20) -> list[Event]:
        """Get recent events."""
        return self.event_log[-limit:]

    def clear_handlers(self) -> None:
        """Clear all handlers (useful for testing)."""
        self.handlers.clear()


# =============================================================================
# Default Event Handlers
# =============================================================================

def create_memory_handlers(bridge: EventBridge) -> None:
    """Register memory-related event handlers."""
    from up.memory import MemoryManager

    config = bridge.config.get("automation", {}).get("memory", {})

    def on_task_complete(event: Event):
        if not config.get("auto_record_tasks", True):
            return
        manager = MemoryManager(bridge.workspace)
        task = event.data.get("task", "Unknown task")
        manager.record_task(task)

        files = event.data.get("files", [])
        for f in files:
            manager.record_file(f)

    def on_error_occurred(event: Event):
        if not config.get("auto_record_errors", True):
            return
        manager = MemoryManager(bridge.workspace)
        error = event.data.get("error", "Unknown error")
        solution = event.data.get("solution")
        manager.record_error(error, solution)

    def on_learning_discovered(event: Event):
        manager = MemoryManager(bridge.workspace)
        learning = event.data.get("learning", "")
        if learning:
            manager.record_learning(learning)

    def on_decision_made(event: Event):
        manager = MemoryManager(bridge.workspace)
        decision = event.data.get("decision", "")
        if decision:
            manager.record_decision(decision)

    def on_git_commit(event: Event):
        if not config.get("auto_index_commits", True):
            return
        manager = MemoryManager(bridge.workspace)
        manager.index_recent_commits(count=1)

    def on_session_end(event: Event):
        manager = MemoryManager(bridge.workspace)
        summary = event.data.get("summary")
        manager.end_session(summary)

    # Register handlers
    bridge.subscribe(EventType.TASK_COMPLETE, on_task_complete)
    bridge.subscribe(EventType.ERROR_OCCURRED, on_error_occurred)
    bridge.subscribe(EventType.LEARNING_DISCOVERED, on_learning_discovered)
    bridge.subscribe(EventType.DECISION_MADE, on_decision_made)
    bridge.subscribe(EventType.GIT_COMMIT, on_git_commit)
    bridge.subscribe(EventType.SESSION_END, on_session_end)


def create_docs_handlers(bridge: EventBridge) -> None:
    """Register docs-related event handlers."""
    config = bridge.config.get("automation", {}).get("docs", {})

    def on_task_complete(event: Event):
        if not config.get("auto_update_context", True):
            return
        _update_context_md(
            bridge.workspace,
            recent_change=event.data.get("task"),
            files=event.data.get("files", [])
        )

    def on_session_end(event: Event):
        if not config.get("auto_update_handoff", True):
            return
        _update_handoff_md(
            bridge.workspace,
            summary=event.data.get("summary"),
            tasks=event.data.get("tasks", []),
            files=event.data.get("files", [])
        )

    def on_milestone_reached(event: Event):
        if not config.get("auto_changelog_on_milestone", True):
            return
        _create_changelog_entry(
            bridge.workspace,
            milestone=event.data.get("milestone"),
            changes=event.data.get("changes", [])
        )

    # Register handlers
    bridge.subscribe(EventType.TASK_COMPLETE, on_task_complete)
    bridge.subscribe(EventType.SESSION_END, on_session_end)
    bridge.subscribe(EventType.MILESTONE_REACHED, on_milestone_reached)


def _update_context_md(workspace: Path, recent_change: str = None, files: list[str] = None):
    """Update docs/CONTEXT.md with recent changes."""
    context_file = workspace / "docs" / "CONTEXT.md"
    if not context_file.exists():
        return

    try:
        content = context_file.read_text()

        # Update the "Updated" date
        from datetime import date
        today = date.today().isoformat()

        import re
        content = re.sub(
            r'\*\*Updated\*\*:\s*[\d-]+',
            f'**Updated**: {today}',
            content
        )

        # Update recent changes section if present
        if recent_change and "## Recent Changes" in content:
            # Find the section and prepend new change
            lines = content.split("\n")
            new_lines = []
            in_recent = False
            added = False

            for line in lines:
                new_lines.append(line)
                if line.startswith("## Recent Changes"):
                    in_recent = True
                elif in_recent and line.startswith("- ") and not added:
                    # Insert before first item
                    new_lines.insert(-1, f"- {recent_change}")
                    added = True
                    in_recent = False

            content = "\n".join(new_lines)

        context_file.write_text(content)

    except Exception as e:
        logger.debug("Docs update failed: %s", e)


def _get_pending_prd_task_titles(workspace: Path, limit: int = 5) -> list[str]:
    """Return titles of next pending tasks from PRD (toward target)."""
    for name in ("prd.json", "docs/prd.json"):
        prd_path = workspace / name
        if not prd_path.exists():
            continue
        try:
            data = json.loads(prd_path.read_text())
            stories = data.get("userStories", [])
            pending = [s.get("title", s.get("id", "")) for s in stories if not s.get("passes", False)]
            return pending[:limit]
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _update_handoff_md(
    workspace: Path,
    summary: str = None,
    tasks: list[str] = None,
    files: list[str] = None
):
    """Update docs/handoff/LATEST.md with session summary."""
    handoff_file = workspace / "docs" / "handoff" / "LATEST.md"
    handoff_file.parent.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    now = datetime.now()

    content = f"""# Latest Session Handoff

**Date**: {now.strftime('%Y-%m-%d')}
**Time**: {now.strftime('%H:%M')}
**Status**: 🟢 Ready

---

## Session Summary

{summary or 'Session completed.'}

## What Was Done

"""

    if tasks:
        for task in tasks:
            content += f"- {task}\n"
    else:
        content += "- Session work completed\n"

    content += """
## Files Modified

"""

    if files:
        for f in files[:10]:  # Limit to 10
            content += f"- `{f}`\n"
        if len(files) > 10:
            content += f"- ...and {len(files) - 10} more\n"
    else:
        content += "- No files recorded\n"

    # Target-aware next steps: pending PRD tasks + generic
    pending_titles = _get_pending_prd_task_titles(workspace)
    content += "\n## Next Steps (toward target)\n\n"
    if pending_titles:
        content += "**Suggested (from PRD):**\n"
        for i, title in enumerate(pending_titles[:5], 1):
            content += f"{i}. {title}\n"
        content += "\n**Always:**\n"
    content += "1. Review changes\n"
    content += "2. Run tests\n"
    content += "3. See [TARGET.md](../TARGET.md) for vision and metrics\n"
    content += "\n---\n\n*Auto-generated by up-cli*\n"

    handoff_file.write_text(content)


def _create_changelog_entry(workspace: Path, milestone: str = None, changes: list[str] = None):
    """Create a changelog entry for a milestone."""
    changelog_dir = workspace / "docs" / "changelog"
    changelog_dir.mkdir(parents=True, exist_ok=True)

    from datetime import date
    today = date.today()
    filename = f"{today.isoformat()}-{milestone or 'update'}.md"
    filepath = changelog_dir / filename

    content = f"""# {milestone or 'Update'}

**Date**: {today.isoformat()}
**Status**: ✅ Completed

---

## Summary

Milestone completed.

## Changes

"""

    if changes:
        for change in changes:
            content += f"- {change}\n"
    else:
        content += "- Changes implemented\n"

    filepath.write_text(content)


# =============================================================================
# Initialize Default Handlers
# =============================================================================

def create_learning_handlers(bridge: EventBridge) -> None:
    """Register continuous learning event handlers."""

    def on_task_complete_learn(event: Event):
        try:
            from up.learn.continuous import check_learning_trigger
            check_learning_trigger(bridge.workspace)
        except Exception as e:
            logger.debug("Continuous learning check failed: %s", e)

    bridge.subscribe(EventType.TASK_COMPLETE, on_task_complete_learn)


def initialize_event_system(workspace: Path | None = None) -> EventBridge:
    """Initialize the event system with default handlers."""
    bridge = EventBridge(workspace)

    # Only register handlers once
    if not bridge.handlers:
        create_memory_handlers(bridge)
        create_docs_handlers(bridge)
        create_learning_handlers(bridge)

    return bridge


# =============================================================================
# Convenience Functions
# =============================================================================

def emit_task_complete(task: str, files: list[str] = None, source: str = "loop"):
    """Emit task complete event."""
    bridge = EventBridge()
    bridge.emit_simple(
        EventType.TASK_COMPLETE,
        source=source,
        task=task,
        files=files or []
    )


def emit_error(error: str, solution: str = None, source: str = "loop"):
    """Emit error occurred event."""
    bridge = EventBridge()
    bridge.emit_simple(
        EventType.ERROR_OCCURRED,
        source=source,
        error=error,
        solution=solution
    )


def emit_learning(learning: str, source: str = "learn"):
    """Emit learning discovered event."""
    bridge = EventBridge()
    bridge.emit_simple(
        EventType.LEARNING_DISCOVERED,
        source=source,
        learning=learning
    )


def emit_decision(decision: str, source: str = "user"):
    """Emit decision made event."""
    bridge = EventBridge()
    bridge.emit_simple(
        EventType.DECISION_MADE,
        source=source,
        decision=decision
    )


def emit_session_end(summary: str = None, tasks: list[str] = None, files: list[str] = None):
    """Emit session end event."""
    bridge = EventBridge()
    bridge.emit_simple(
        EventType.SESSION_END,
        source="session",
        summary=summary,
        tasks=tasks or [],
        files=files or []
    )


def emit_git_commit(commit_hash: str, message: str):
    """Emit git commit event."""
    bridge = EventBridge()
    bridge.emit_simple(
        EventType.GIT_COMMIT,
        source="git",
        hash=commit_hash,
        message=message
    )
