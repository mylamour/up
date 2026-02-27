"""Parallel task execution using Git worktrees.

This module enables running multiple AI tasks simultaneously,
each in its own isolated Git worktree. Tasks are verified
independently and merged to main when successful.

Uses the unified state system in .up/state.json for consistency.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filelock import FileLock
from rich.console import Console

from up.ai_cli import run_ai_task
from up.concurrency import run_subprocess
from up.core.state import get_state_manager
from up.core.checkpoint import get_checkpoint_manager
from up.git.utils import count_commits_since
from up.git.worktree import WorktreeState

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: str
    success: bool
    phase: str  # "executed", "verified", "merged", "failed"
    duration_seconds: float
    commits: int = 0
    error: str | None = None
    test_results: dict | None = None


class ParallelExecutionManager:
    """Manages parallel execution state using unified state system.

    This replaces the old ParallelState dataclass to use .up/state.json
    instead of the legacy .parallel_state.json file.

    State mutations use StateManager.atomic_update() and FileLock for
    thread- and process-safe consistency; no separate threading lock.
    """

    def __init__(self, workspace: Path = None):
        self.workspace = workspace or Path.cwd()
        self._state_manager = get_state_manager(self.workspace)

    @property
    def state(self):
        """Get the parallel state from unified state."""
        return self._state_manager.state.parallel

    @property
    def iteration(self) -> int:
        return self.state.current_batch

    @iteration.setter
    def iteration(self, value: int):
        self._state_manager.atomic_update(lambda s: setattr(s.parallel, "current_batch", value))

    @property
    def parallel_limit(self) -> int:
        return self.state.max_workers

    @parallel_limit.setter
    def parallel_limit(self, value: int):
        self._state_manager.atomic_update(lambda s: setattr(s.parallel, "max_workers", value))

    @property
    def active_worktrees(self) -> list[str]:
        return self.state.agents

    def add_active_worktree(self, task_id: str):
        """Add a worktree to active list (thread-safe via atomic_update)."""
        def _add(s):
            if task_id not in s.parallel.agents:
                s.parallel.agents.append(task_id)
        self._state_manager.atomic_update(_add)

    def remove_active_worktree(self, task_id: str):
        """Remove a worktree from active list (thread-safe via atomic_update)."""
        def _remove(s):
            if task_id in s.parallel.agents:
                s.parallel.agents.remove(task_id)
        self._state_manager.atomic_update(_remove)

    def set_active(self, active: bool):
        """Set parallel execution active state (thread-safe via atomic_update)."""
        self._state_manager.atomic_update(lambda s: setattr(s.parallel, "active", active))

    def save(self):
        """Explicit save (for compatibility)."""
        self._state_manager.save()

    def record_task_complete(self, task_id: str):
        """Record a task completion in metrics (atomic)."""
        self._state_manager.record_task_complete(task_id)

    def record_task_failed(self, task_id: str):
        """Record a task failure in metrics (atomic)."""
        self._state_manager.record_task_failed(task_id)


def _prd_lock(prd_path: Path) -> FileLock:
    """Return a FileLock for the PRD file to prevent concurrent read/write corruption."""
    return FileLock(str(prd_path) + ".lock", timeout=30)


def get_pending_tasks(prd_path: Path, limit: int = None, workspace: Path = None) -> list[dict]:
    """Get pending tasks from PRD file.

    Cross-checks against both the PRD's `passes` field AND the
    state manager's `tasks_completed` list to avoid re-running
    tasks that were already implemented (e.g., manually in Cursor).
    PRD read/write is protected by FileLock for multi-agent safety.

    Args:
        prd_path: Path to prd.json
        limit: Maximum tasks to return
        workspace: Workspace root (for state cross-check)

    Returns:
        List of pending task dicts
    """
    if not prd_path.exists():
        return []

    lock = _prd_lock(prd_path)
    try:
        with lock:
            data = json.loads(prd_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    stories = data.get("userStories", [])

    # Get already-completed tasks from state manager (outside PRD lock to avoid deadlock)
    completed_in_state = set()
    if workspace:
        try:
            sm = get_state_manager(workspace)
            completed_in_state = set(sm.state.loop.tasks_completed)
        except Exception as e:
            logger.debug("Ignored exception: %s", e)

    # A task is pending only if BOTH:
    # 1. PRD says passes != true
    # 2. State doesn't list it as completed
    pending = []
    synced_count = 0
    for s in stories:
        task_id = s.get("id", "")
        if s.get("passes", False):
            continue  # Already marked done in PRD
        if task_id in completed_in_state:
            s["passes"] = True
            s["completedAt"] = s.get("completedAt", datetime.now().strftime("%Y-%m-%d"))
            synced_count += 1
            continue
        pending.append(s)

    # Save synced PRD if any tasks were auto-completed (hold lock for write)
    if synced_count > 0:
        try:
            with lock:
                # Re-read to avoid overwriting concurrent updates
                data = json.loads(prd_path.read_text())
                for s in data.get("userStories", []):
                    if s.get("id") in completed_in_state and not s.get("passes"):
                        s["passes"] = True
                        s["completedAt"] = s.get("completedAt", datetime.now().strftime("%Y-%m-%d"))
                prd_path.write_text(json.dumps(data, indent=2))
            console.print(f"[dim]Auto-synced {synced_count} completed tasks in PRD[/]")
        except Exception as e:
            logger.debug("Ignored exception: %s", e)

    if limit:
        pending = pending[:limit]

    return pending


def execute_task_in_worktree(
    worktree_path: Path, task: dict, cli_name: str = "claude", timeout: int = 600
) -> TaskResult:
    """Execute a single task in its worktree.

    Args:
        worktree_path: Path to the worktree
        task: Task dict from PRD
        cli_name: AI CLI to use
        timeout: Timeout in seconds

    Returns:
        TaskResult with execution outcome
    """
    task_id = task.get("id", "unknown")
    start_time = time.time()

    try:
        state = WorktreeState.load(worktree_path)
        state.status = "executing"
        state.phase = "CHECKPOINT"

        cp_manager = get_checkpoint_manager(worktree_path)
        checkpoint_meta = cp_manager.save(message=f"{task_id}-start", task_id=task_id)
        state.checkpoints.append({"name": checkpoint_meta.id, "time": datetime.now().isoformat()})
        state.phase = "AI_IMPL"
        state.save(worktree_path)

        prompt = _build_task_prompt(task)

        success, output = run_ai_task(
            workspace=worktree_path, prompt=prompt, cli_name=cli_name, timeout=timeout
        )

        state.ai_invocations.append(
            {
                "success": success,
                "duration_seconds": time.time() - start_time,
                "output_preview": output[:500] if output else "",
            }
        )

        if not success:
            state.status = "failed"
            state.error = output[:500] if output else "AI execution failed"
            state.save(worktree_path)
            return TaskResult(
                task_id=task_id,
                success=False,
                phase="executed",
                duration_seconds=time.time() - start_time,
                error=state.error,
            )

        run_subprocess(
            ["git", "add", "-A"], cwd=worktree_path, capture_output=True, timeout=30
        )
        run_subprocess(
            ["git", "commit", "-m", f"feat({task_id}): {task.get('title', 'Implement task')}"],
            cwd=worktree_path,
            capture_output=True,
            timeout=30,
        )

        state.status = "executed"
        state.phase = "VERIFY"
        state.save(worktree_path)

        commits = count_commits_since(worktree_path, "main")

        return TaskResult(
            task_id=task_id,
            success=True,
            phase="executed",
            duration_seconds=time.time() - start_time,
            commits=commits,
        )

    except Exception as e:
        return TaskResult(
            task_id=task_id,
            success=False,
            phase="failed",
            duration_seconds=time.time() - start_time,
            error=str(e),
        )


def verify_worktree(worktree_path: Path) -> TaskResult:
    """Run verification (tests, lint) in a worktree.

    Args:
        worktree_path: Path to the worktree

    Returns:
        TaskResult with verification outcome
    """
    start_time = time.time()

    try:
        state = WorktreeState.load(worktree_path)
        task_id = state.task_id
    except FileNotFoundError:
        task_id = worktree_path.name
        state = None

    test_results = {"tests": None, "lint": None, "type_check": None}

    result = run_subprocess(
        ["pytest", "-q", "--tb=no"], cwd=worktree_path, capture_output=True, text=True, timeout=300
    )
    test_results["tests"] = result.returncode == 0

    result = run_subprocess(
        ["ruff", "check", "src/", "--quiet"], cwd=worktree_path, capture_output=True, text=True, timeout=60
    )
    test_results["lint"] = result.returncode == 0

    result = run_subprocess(
        ["mypy", "src/", "--ignore-missing-imports", "--no-error-summary"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    test_results["type_check"] = result.returncode == 0

    passed = all(v is None or v is True for v in test_results.values())

    if state:
        state.verification = test_results
        state.status = "passed" if passed else "failed"
        state.phase = "MERGE" if passed else "FAILED"
        state.save(worktree_path)

    return TaskResult(
        task_id=task_id,
        success=passed,
        phase="verified",
        duration_seconds=time.time() - start_time,
        test_results=test_results,
    )


def _build_task_prompt(task: dict) -> str:
    """Build AI prompt for task implementation."""
    task_id = task.get("id", "unknown")
    title = task.get("title", "")
    description = task.get("description", title)
    criteria = task.get("acceptanceCriteria", [])

    prompt = f"""Implement task {task_id}: {title}

Description: {description}

"""

    if criteria:
        prompt += "Acceptance Criteria:\n"
        for c in criteria:
            prompt += f"  - {c}\n"
        prompt += "\n"

    prompt += """Instructions:
1. Implement the feature as described
2. Add appropriate tests
3. Ensure code passes linting
4. Commit your changes

Begin implementation."""

    return prompt


def mark_task_complete_in_prd(prd_path: Path, task_id: str):
    """Mark a task as complete in the PRD. Uses FileLock for concurrent safety."""
    if not prd_path.exists():
        return

    lock = _prd_lock(prd_path)
    try:
        with lock:
            data = json.loads(prd_path.read_text())
            for story in data.get("userStories", []):
                if story.get("id") == task_id:
                    story["passes"] = True
                    story["completedAt"] = datetime.now().strftime("%Y-%m-%d")
                    break
            prd_path.write_text(json.dumps(data, indent=2))
    except (OSError, json.JSONDecodeError):
        pass
