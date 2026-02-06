"""Helper functions for the product loop.

State loading, task finding, checkpoint operations, and PRD management.
"""

import json
import re
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from up.core.state import get_state_manager, CircuitBreakerState
from up.core.checkpoint import get_checkpoint_manager, NotAGitRepoError

console = Console()


def is_initialized(workspace: Path) -> bool:
    """Check if project is initialized with up systems."""
    return (
        (workspace / ".claude").exists()
        or (workspace / ".cursor").exists()
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


def check_circuit_breaker(state: dict) -> dict:
    """Check circuit breaker status."""
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


def get_next_task_from_prd(prd_path: Path) -> dict:
    """Get next incomplete task from PRD."""
    if not prd_path.exists():
        return None

    try:
        data = json.loads(prd_path.read_text())
        stories = data.get("userStories", [])

        # Find first incomplete task
        for story in sorted(stories, key=lambda s: s.get("priority", 999)):
            if not story.get("passes", False):
                return story

        return None
    except json.JSONDecodeError:
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
        data = json.loads(prd_path.read_text())
        stories = data.get("userStories", [])

        for story in stories:
            if story.get("id") == task_id:
                story["passes"] = True
                story["completedAt"] = time.strftime("%Y-%m-%d")
                break

        prd_path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


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
