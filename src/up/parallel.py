"""Parallel task execution using Git worktrees.

This module enables running multiple AI tasks simultaneously,
each in its own isolated Git worktree. Tasks are verified
independently and merged to main when successful.

Uses the unified state system in .up/state.json for consistency.
"""

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from up.git.worktree import (
    create_worktree,
    remove_worktree,
    list_worktrees,
    merge_worktree,
    create_checkpoint,
    count_commits_since,
    WorktreeState,
)
from up.ai_cli import check_ai_cli, run_ai_task
from up.core.state import get_state_manager, AgentState

console = Console()


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    phase: str  # "executed", "verified", "merged", "failed"
    duration_seconds: float
    commits: int = 0
    error: Optional[str] = None
    test_results: Optional[dict] = None


class ParallelExecutionManager:
    """Manages parallel execution state using unified state system.
    
    This replaces the old ParallelState dataclass to use .up/state.json
    instead of the legacy .parallel_state.json file.
    
    All state mutations are protected by a threading.Lock to prevent
    race conditions when multiple threads modify state concurrently.
    The underlying StateManager also uses filelock for cross-process safety.
    """
    
    def __init__(self, workspace: Path = None):
        self.workspace = workspace or Path.cwd()
        self._state_manager = get_state_manager(self.workspace)
        self._lock = threading.Lock()
    
    @property
    def state(self):
        """Get the parallel state from unified state."""
        return self._state_manager.state.parallel
    
    @property
    def iteration(self) -> int:
        return self.state.current_batch
    
    @iteration.setter
    def iteration(self, value: int):
        with self._lock:
            self.state.current_batch = value
            self._state_manager.save()
    
    @property
    def parallel_limit(self) -> int:
        return self.state.max_workers
    
    @parallel_limit.setter
    def parallel_limit(self, value: int):
        with self._lock:
            self.state.max_workers = value
            self._state_manager.save()
    
    @property
    def active_worktrees(self) -> List[str]:
        return self.state.agents
    
    def add_active_worktree(self, task_id: str):
        """Add a worktree to active list (thread-safe)."""
        with self._lock:
            if task_id not in self.state.agents:
                self.state.agents.append(task_id)
                self._state_manager.save()
    
    def remove_active_worktree(self, task_id: str):
        """Remove a worktree from active list (thread-safe)."""
        with self._lock:
            if task_id in self.state.agents:
                self.state.agents.remove(task_id)
                self._state_manager.save()
    
    def set_active(self, active: bool):
        """Set parallel execution active state (thread-safe)."""
        with self._lock:
            self.state.active = active
            self._state_manager.save()
    
    def save(self):
        """Explicit save (thread-safe, for compatibility)."""
        with self._lock:
            self._state_manager.save()
    
    def record_task_complete(self, task_id: str):
        """Record a task completion in metrics (thread-safe)."""
        with self._lock:
            self._state_manager.record_task_complete(task_id)
    
    def record_task_failed(self, task_id: str):
        """Record a task failure in metrics (thread-safe)."""
        with self._lock:
            self._state_manager.record_task_failed(task_id)


def get_pending_tasks(prd_path: Path, limit: int = None) -> list[dict]:
    """Get pending tasks from PRD file.
    
    Args:
        prd_path: Path to prd.json
        limit: Maximum tasks to return
    
    Returns:
        List of pending task dicts
    """
    if not prd_path.exists():
        return []
    
    try:
        data = json.loads(prd_path.read_text())
        stories = data.get("userStories", [])
        
        pending = [s for s in stories if not s.get("passes", False)]
        
        if limit:
            pending = pending[:limit]
        
        return pending
    except json.JSONDecodeError:
        return []


def execute_task_in_worktree(
    worktree_path: Path,
    task: dict,
    cli_name: str = "claude",
    timeout: int = 600
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
        # Update state to executing
        state = WorktreeState.load(worktree_path)
        state.status = "executing"
        state.phase = "CHECKPOINT"
        state.save(worktree_path)
        
        # Create checkpoint
        checkpoint = create_checkpoint(worktree_path, f"{task_id}-start")
        state.checkpoints.append({
            "name": checkpoint,
            "time": datetime.now().isoformat()
        })
        state.save(worktree_path)
        
        # Build implementation prompt
        prompt = _build_task_prompt(task)
        
        # Run AI implementation
        state.phase = "AI_IMPL"
        state.save(worktree_path)
        
        success, output = run_ai_task(
            workspace=worktree_path,
            prompt=prompt,
            cli_name=cli_name,
            timeout=timeout
        )
        
        state.ai_invocations.append({
            "success": success,
            "duration_seconds": time.time() - start_time,
            "output_preview": output[:500] if output else ""
        })
        state.save(worktree_path)
        
        if not success:
            state.status = "failed"
            state.error = output[:500] if output else "AI execution failed"
            state.save(worktree_path)
            
            return TaskResult(
                task_id=task_id,
                success=False,
                phase="executed",
                duration_seconds=time.time() - start_time,
                error=state.error
            )
        
        # Commit AI changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=worktree_path,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"feat({task_id}): {task.get('title', 'Implement task')}"],
            cwd=worktree_path,
            capture_output=True
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
            commits=commits
        )
        
    except Exception as e:
        return TaskResult(
            task_id=task_id,
            success=False,
            phase="failed",
            duration_seconds=time.time() - start_time,
            error=str(e)
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
    
    test_results = {
        "tests": None,
        "lint": None,
        "type_check": None
    }
    
    # Run pytest if available
    result = subprocess.run(
        ["pytest", "-q", "--tb=no"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    test_results["tests"] = result.returncode == 0
    
    # Run ruff if available
    result = subprocess.run(
        ["ruff", "check", "src/", "--quiet"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    test_results["lint"] = result.returncode == 0
    
    # Run mypy if available
    result = subprocess.run(
        ["mypy", "src/", "--ignore-missing-imports", "--no-error-summary"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    test_results["type_check"] = result.returncode == 0
    
    # All must pass (None counts as pass - tool not available)
    passed = all(
        v is None or v is True
        for v in test_results.values()
    )
    
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
        test_results=test_results
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


def run_parallel_loop(
    workspace: Path,
    prd_path: Path,
    max_workers: int = 3,
    run_all: bool = False,
    timeout: int = 600,
    dry_run: bool = False
) -> dict:
    """Run the parallel product loop.
    
    Args:
        workspace: Project root directory
        prd_path: Path to prd.json
        max_workers: Number of parallel tasks
        run_all: Whether to run all tasks or just one batch
        timeout: AI timeout per task
        dry_run: Preview without executing
    
    Returns:
        Summary dict with results
    """
    # Use unified state management
    state_mgr = ParallelExecutionManager(workspace)
    state_mgr.iteration += 1
    state_mgr.parallel_limit = max_workers
    state_mgr.set_active(True)
    
    summary = {
        "batches": 0,
        "completed": [],
        "failed": [],
        "total_duration": 0
    }
    
    start_time = time.time()
    
    try:
        while True:
            # Get pending tasks
            tasks = get_pending_tasks(prd_path, limit=max_workers)
            
            if not tasks:
                console.print("\n[green]✓[/] All tasks completed!")
                break
            
            summary["batches"] += 1
            console.print(f"\n[bold]Batch {summary['batches']}:[/] {len(tasks)} tasks")
            
            if dry_run:
                for task in tasks:
                    console.print(f"  Would execute: {task.get('id')} - {task.get('title')}")
                if not run_all:
                    break
                continue
            
            # Phase 1: Create worktrees
            console.print("\n[dim]Creating worktrees...[/]")
            worktrees = []
            for task in tasks:
                task_id = task.get("id")
                wt_path, wt_state = create_worktree(
                    task_id,
                    task.get("title", "")
                )
                worktrees.append({
                    "path": wt_path,
                    "state": wt_state,
                    "task": task
                })
                console.print(f"  ✓ {wt_path}")
                state_mgr.add_active_worktree(task_id)
            
            # Phase 2: Execute in parallel
            console.print("\n[dim]Executing tasks...[/]")
            
            cli_name, cli_available = check_ai_cli()
            if not cli_available:
                console.print("[yellow]No AI CLI found. Skipping execution.[/]")
                for wt in worktrees:
                    remove_worktree(wt["task"].get("id"))
                break
            
            results = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        execute_task_in_worktree,
                        wt["path"],
                        wt["task"],
                        cli_name,
                        timeout
                    ): wt["task"].get("id")
                    for wt in worktrees
                }
                
                for future in as_completed(futures):
                    task_id = futures[future]
                    try:
                        result = future.result()
                        results[task_id] = result
                        status = "✓" if result.success else "✗"
                        console.print(f"  {status} {task_id}: {result.phase}")
                    except Exception as e:
                        results[task_id] = TaskResult(
                            task_id=task_id,
                            success=False,
                            phase="failed",
                            duration_seconds=0,
                            error=str(e)
                        )
            
            # Phase 3: Verify
            console.print("\n[dim]Verifying...[/]")
            for wt in worktrees:
                task_id = wt["task"].get("id")
                if results.get(task_id, TaskResult("", False, "failed", 0)).success:
                    verify_result = verify_worktree(wt["path"])
                    results[task_id] = verify_result
                    
                    status = "✅" if verify_result.success else "❌"
                    test_info = ""
                    if verify_result.test_results:
                        test_info = f" (tests: {verify_result.test_results.get('tests', '?')})"
                    console.print(f"  {status} {task_id}{test_info}")
            
            # Phase 4: Merge passed tasks
            console.print("\n[dim]Merging...[/]")
            for wt in worktrees:
                task_id = wt["task"].get("id")
                result = results.get(task_id)
                
                if result and result.success:
                    if merge_worktree(task_id):
                        console.print(f"  ✓ {task_id} merged")
                        summary["completed"].append(task_id)
                        state_mgr.record_task_complete(task_id)
                        
                        # Mark task complete in PRD
                        _mark_task_complete(prd_path, task_id)
                    else:
                        console.print(f"  ✗ {task_id} merge failed")
                        summary["failed"].append(task_id)
                        state_mgr.record_task_failed(task_id)
                else:
                    console.print(f"  - {task_id} skipped (not passed)")
                    summary["failed"].append(task_id)
                    state_mgr.record_task_failed(task_id)
                
                # Remove from active
                state_mgr.remove_active_worktree(task_id)
            
            if not run_all:
                break
    finally:
        # Mark parallel execution as inactive
        state_mgr.set_active(False)
    
    summary["total_duration"] = time.time() - start_time
    
    # Print summary
    _print_summary(summary)
    
    return summary


def _mark_task_complete(prd_path: Path, task_id: str):
    """Mark a task as complete in the PRD."""
    if not prd_path.exists():
        return
    
    try:
        data = json.loads(prd_path.read_text())
        for story in data.get("userStories", []):
            if story.get("id") == task_id:
                story["passes"] = True
                story["completedAt"] = datetime.now().strftime("%Y-%m-%d")
                break
        prd_path.write_text(json.dumps(data, indent=2))
    except (json.JSONDecodeError, IOError):
        pass


def _print_summary(summary: dict):
    """Print execution summary."""
    console.print("\n" + "═" * 50)
    console.print("[bold]SUMMARY[/]")
    console.print("═" * 50)
    
    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    
    table.add_row("Batches", str(summary["batches"]))
    table.add_row("Completed", f"[green]{len(summary['completed'])}[/]")
    table.add_row("Failed", f"[red]{len(summary['failed'])}[/]")
    table.add_row("Duration", f"{summary['total_duration']:.1f}s")
    
    console.print(table)
    
    if summary["completed"]:
        console.print(f"\n[green]Completed:[/] {', '.join(summary['completed'])}")
    if summary["failed"]:
        console.print(f"[red]Failed:[/] {', '.join(summary['failed'])}")
