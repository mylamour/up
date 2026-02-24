"""Helper functions for the product loop.

State loading, task finding, checkpoint operations, and PRD management.
"""

import json
import logging
import re
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from up.core.state import get_state_manager, CircuitBreakerState
from up.core.checkpoint import get_checkpoint_manager, NotAGitRepoError

console = Console()
logger = logging.getLogger(__name__)


def is_initialized(workspace: Path) -> bool:
    """Check if project is initialized with up systems."""
    return (
        (workspace / ".claude").exists()
        or (workspace / ".cursor").exists()
        or (workspace / ".up").exists()
        or (workspace / "CLAUDE.md").exists()
    )


def find_task_source(workspace: Path, prd_path: str = None) -> str:
    """Find task source file."""
    if prd_path:
        return prd_path

    # Check common locations
    sources = [
        "prd.json",
        ".claude/skills/learning-system/prd.json",
        ".cursor/skills/learning-system/prd.json",
        "TODO.md",
        "docs/todo/TODO.md",
    ]

    for source in sources:
        if (workspace / source).exists():
            return source

    return None


def load_loop_state(workspace: Path) -> dict:
    """Load loop state from unified state file.

    Returns a dict for backwards compatibility with existing code.
    Internally uses the new StateManager.
    """
    manager = get_state_manager(workspace)
    state = manager.state

    # Convert to dict format for backwards compatibility
    return {
        "version": state.version,
        "iteration": state.loop.iteration,
        "phase": state.loop.phase,
        "current_task": state.loop.current_task,
        "tasks_completed": state.loop.tasks_completed,
        "tasks_failed": state.loop.tasks_failed,
        "last_checkpoint": state.loop.last_checkpoint,
        "circuit_breaker": {
            name: {"failures": cb.failures, "state": cb.state}
            for name, cb in state.circuit_breakers.items()
        },
        "metrics": {
            "total_edits": state.metrics.total_tasks,
            "total_rollbacks": state.metrics.total_rollbacks,
            "success_rate": state.metrics.success_rate,
        },
    }


def save_loop_state(workspace: Path, state: dict) -> None:
    """Save loop state to unified state file.

    Accepts dict for backwards compatibility, converts to StateManager.
    """
    manager = get_state_manager(workspace)

    # Update loop state from dict
    manager.state.loop.iteration = state.get("iteration", 0)
    manager.state.loop.phase = state.get("phase", "IDLE")
    manager.state.loop.current_task = state.get("current_task")
    manager.state.loop.last_checkpoint = state.get("last_checkpoint")

    if "tasks_completed" in state:
        manager.state.loop.tasks_completed = state["tasks_completed"]

    # Update circuit breakers
    if "circuit_breaker" in state:
        for name, cb_data in state["circuit_breaker"].items():
            if isinstance(cb_data, dict):
                manager.state.circuit_breakers[name] = CircuitBreakerState(
                    failures=cb_data.get("failures", 0),
                    state=cb_data.get("state", "CLOSED"),
                )

    manager.save()


def count_tasks(workspace: Path, task_source: str) -> int:
    """Count remaining tasks in source file."""
    filepath = workspace / task_source

    if not filepath.exists():
        return 0

    if task_source.endswith(".json"):
        try:
            data = json.loads(filepath.read_text())
            stories = data.get("userStories", [])
            return len([s for s in stories if not s.get("passes", False)])
        except json.JSONDecodeError:
            return 0

    elif task_source.endswith(".md"):
        content = filepath.read_text()
        return len(re.findall(r"- \[ \]", content))

    return 0


def reset_circuit_breaker(workspace: Path) -> None:
    """Reset all circuit breakers to CLOSED state.

    Called by ``--resume`` so the user can retry after fixing an issue.
    """
    try:
        manager = get_state_manager(workspace)
        for cb in manager.state.circuit_breakers.values():
            cb.failures = 0
            cb.state = "CLOSED"
            cb.opened_at = None
        manager.state.loop.consecutive_failures = 0
        manager.save()
    except Exception as exc:
        logger.debug("Failed to reset circuit breakers: %s", exc)


def check_circuit_breaker(state: dict, workspace: Path = None) -> dict:
    """Check circuit breaker status.

    Uses the StateManager's CircuitBreakerState objects so that
    cooldown-based auto-reset (OPEN → HALF_OPEN) is honoured.
    Falls back to raw dict check when no workspace is available.
    """
    if workspace:
        try:
            manager = get_state_manager(workspace)
            for name, cb in manager.state.circuit_breakers.items():
                if not cb.can_execute():
                    return {
                        "open": True,
                        "circuit": name,
                        "reason": f"{name} circuit opened after {cb.failures} failures",
                        "can_retry": False,
                    }
                # can_execute() may have transitioned OPEN → HALF_OPEN; persist it
                if cb.state == "HALF_OPEN":
                    manager.save()
            return {"open": False}
        except Exception:
            pass  # Fall through to dict-based check

    # Fallback: raw dict check (no cooldown support)
    cb = state.get("circuit_breaker", {})

    for name, circuit in cb.items():
        if isinstance(circuit, dict):
            cb_state = circuit.get("state", "CLOSED")
            failures = circuit.get("failures", 0)

            if cb_state == "OPEN":
                return {
                    "open": True,
                    "circuit": name,
                    "reason": f"{name} circuit opened after {failures} failures",
                    "can_retry": False,
                }

    return {"open": False}


def get_next_task_from_prd(prd_path: Path, workspace: Path = None, auto_sync: bool = False) -> dict:
    """Get next incomplete task from PRD.

    Cross-checks against state.tasks_completed to skip tasks
    that were implemented manually (e.g., in Cursor) but not
    marked in the PRD.

    By default this function is read-only. Set auto_sync=True to
    persist PRD pass-state updates for tasks already completed in state.
    """
    from dataclasses import asdict
    from up.core.prd_schema import load_prd, save_prd, PRDValidationError

    try:
        prd = load_prd(prd_path)
    except PRDValidationError:
        return None

    # Get completed tasks from state for cross-check
    completed_in_state = set()
    if workspace:
        try:
            from up.core.state import get_state_manager
            sm = get_state_manager(workspace)
            completed_in_state = set(sm.state.loop.tasks_completed)
        except Exception as exc:
            logger.debug("Failed to read completed tasks from state: %s", exc)

    # Find first truly incomplete task
    synced = False
    for story in prd.userStories:
        if story.passes:
            continue
        if story.id in completed_in_state:
            if auto_sync:
                story.passes = True
                story.completedAt = story.completedAt or time.strftime("%Y-%m-%d")
                synced = True
            continue
        return asdict(story)

    if auto_sync and synced:
        try:
            save_prd(prd, prd_path)
        except Exception as exc:
            logger.warning("Failed to persist PRD auto-sync updates: %s", exc)

    return None


def display_status_table(state: dict, task_source: str, workspace: Path, resume: bool):
    """Display status table."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value")

    iteration = state.get("iteration", 0)
    table.add_row("Iteration", f"[cyan]{iteration}[/]")

    phase = state.get("phase", "INIT")
    table.add_row("Phase", f"[cyan]{phase}[/]")

    if task_source:
        task_count = count_tasks(workspace, task_source)
        table.add_row("Tasks", f"[cyan]{task_count}[/] remaining from {task_source}")
    else:
        table.add_row("Tasks", "[dim]No task source[/]")

    completed = len(state.get("tasks_completed", []))
    table.add_row("Completed", f"[green]{completed}[/]")

    success_rate = state.get("metrics", {}).get("success_rate", 1.0)
    table.add_row("Success Rate", f"[green]{success_rate*100:.0f}%[/]")

    mode = "Resume" if resume else "Fresh Start"
    table.add_row("Mode", mode)

    console.print(table)


def create_checkpoint(workspace: Path, name: str, task_id: str = None) -> bool:
    """Create a git checkpoint using the unified CheckpointManager."""
    try:
        manager = get_checkpoint_manager(workspace)
        manager.save(message=name, task_id=task_id)
        return True
    except NotAGitRepoError:
        return False
    except Exception:
        return False


def rollback_checkpoint(workspace: Path, checkpoint_id: str = None) -> bool:
    """Rollback to checkpoint using the unified CheckpointManager."""
    try:
        manager = get_checkpoint_manager(workspace)
        manager.restore(checkpoint_id=checkpoint_id)
        return True
    except Exception:
        return False


def mark_task_complete(workspace: Path, task_source: str, task_id: str) -> None:
    """Mark a task as complete in the PRD."""
    if not task_source or not task_source.endswith(".json"):
        return

    prd_path = workspace / task_source
    if not prd_path.exists():
        return

    try:
        from up.core.prd_schema import load_prd, save_prd
        prd = load_prd(prd_path)
        if prd.mark_complete(task_id, date=time.strftime("%Y-%m-%d")):
            save_prd(prd, prd_path)
    except Exception as exc:
        logger.warning("Failed to mark task complete in PRD (%s): %s", task_id, exc)


def _format_prd_extras(task: dict) -> str:
    """Format acceptance criteria, file hints, and dependencies from a PRD task."""
    parts = []

    criteria = task.get("acceptanceCriteria", [])
    if criteria:
        lines = "\n".join(f"  - {c}" for c in criteria)
        parts.append(f"Acceptance Criteria:\n{lines}")

    files = task.get("files", [])
    if files:
        lines = "\n".join(f"  - {f}" for f in files)
        parts.append(f"Relevant Files:\n{lines}")

    depends = task.get("depends_on", [])
    if depends:
        parts.append(f"Depends On: {', '.join(depends)}")

    return ("\n\n" + "\n\n".join(parts)) if parts else ""


def build_research_prompt(workspace: Path, task: dict, task_source: str) -> str:
    """Build a prompt for the AI to research the task."""
    task_id = task.get("id", "unknown")
    task_title = task.get("title", "")
    task_desc = task.get("description", task_title)
    extras = _format_prd_extras(task)

    progress_md = workspace / ".up/thoughts/progress.md"
    progress_info = ""
    if progress_md.exists():
        progress_info = f"\n\nPrevious Progress Handoff:\n{progress_md.read_text()}\n"

    return f"""PHASE 1: RESEARCH

Task ID: {task_id}
Title: {task_title}
Description: {task_desc}{extras}{progress_info}

Your objective is to thoroughly research the codebase to understand how to implement this task.
Do NOT make any code changes yet.

Instructions:
1. Search and read relevant files to understand the current architecture and data flow.
2. Identify all files that will need to be created or modified.
3. Identify any potential edge cases or conflicts.
4. Summarize your findings and save them to '.up/thoughts/research.md'.

When you have saved your findings, end your turn."""


def build_plan_prompt(workspace: Path, task: dict, task_source: str) -> str:
    """Build a prompt for the AI to plan the task implementation."""
    task_id = task.get("id", "unknown")
    task_title = task.get("title", "")
    task_desc = task.get("description", task_title)
    extras = _format_prd_extras(task)

    return f"""PHASE 2: PLAN

Task ID: {task_id}
Title: {task_title}
Description: {task_desc}{extras}

Your objective is to create a step-by-step implementation plan based on your previous research.
Do NOT make any code changes yet.

Instructions:
1. Read your findings from '.up/thoughts/research.md'.
2. Create a detailed, step-by-step plan of exact changes needed.
3. Include specific files, functions to modify, and how to test.
4. Save this detailed plan to '.up/thoughts/plan.md'.

When you have saved the plan, end your turn so a human can review it."""


def build_implement_prompt(workspace: Path, task: dict, task_source: str) -> str:
    """Build a prompt for the AI to implement the task based on the plan."""
    task_id = task.get("id", "unknown")
    task_title = task.get("title", "")
    task_desc = task.get("description", task_title)
    extras = _format_prd_extras(task)

    return f"""PHASE 3: IMPLEMENT

Task ID: {task_id}
Title: {task_title}
Description: {task_desc}{extras}

Your objective is to implement the task according to the agreed plan.

Instructions:
1. Read the plan from '.up/thoughts/plan.md'.
2. Execute the plan step-by-step.
3. Make minimal, focused changes.
4. Follow existing code style and patterns.
5. Add or update tests if appropriate.
6. When implementation is complete, summarize your progress and write it to '.up/thoughts/progress.md' to compact context.
7. End your turn when all changes are made and tests pass."""


def build_implementation_prompt(workspace: Path, task: dict, task_source: str) -> str:
    """Build a prompt for the AI to implement the task."""
    task_id = task.get("id", "unknown")
    task_title = task.get("title", "")
    task_desc = task.get("description", task_title)
    priority = task.get("priority", "medium")

    # Read project context
    context = ""
    readme = workspace / "README.md"
    if not readme.exists():
        readme = workspace / "Readme.md"
    if readme.exists():
        content = readme.read_text()
        if len(content) > 2000:
            content = content[:2000] + "..."
        context = f"\n\nProject README:\n{content}"

    return f"""Implement this task in the current project:

Task ID: {task_id}
Title: {task_title}
Description: {task_desc}
Priority: {priority}

Requirements:
1. Make minimal, focused changes
2. Follow existing code style and patterns
3. Add tests if appropriate
4. Update documentation if needed
{context}

Implement this task now. Make the necessary code changes."""
