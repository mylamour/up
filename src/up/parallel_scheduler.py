"""Advanced parallel task scheduling with dependency resolution.

Enhances the basic parallel loop with:
1. Dependency-aware scheduling (topological sort)
2. File-level conflict prevention (task-to-file mapping)
3. Cross-agent shared knowledge (shared context file)
4. Parallel progress monitoring (Rich live dashboard)
5. Partial merge for failed agents (cherry-pick passing files)

Uses Python's built-in graphlib.TopologicalSorter for DAG scheduling.
"""

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from graphlib import TopologicalSorter, CycleError
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Set, Any

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.text import Text

from up.git.worktree import (
    create_worktree,
    remove_worktree,
    merge_worktree,
    WorktreeState,
)
from up.git.utils import run_git, is_git_repo, get_current_branch
from up.ai_cli import check_ai_cli, run_ai_task
from up.core.state import get_state_manager, AgentState
from up.parallel import (
    ParallelExecutionManager,
    TaskResult,
    execute_task_in_worktree,
    verify_worktree,
    _mark_task_complete,
)

console = Console()


# =============================================================================
# 1. Dependency-Aware Scheduling
# =============================================================================


def build_dependency_graph(tasks: List[dict]) -> Dict[str, Set[str]]:
    """Build a dependency graph from PRD tasks.

    Args:
        tasks: List of task dicts from prd.json

    Returns:
        Dict mapping task_id -> set of dependency task_ids
    """
    graph = {}
    task_ids = {t.get("id") for t in tasks}

    for task in tasks:
        task_id = task.get("id", "")
        deps = set()
        for dep in task.get("depends_on", []):
            # Only include deps that are in our task set
            if dep in task_ids:
                deps.add(dep)
        graph[task_id] = deps

    return graph


def get_execution_waves(tasks: List[dict]) -> List[List[dict]]:
    """Schedule tasks into parallel execution waves respecting dependencies.

    Uses topological sort to find tasks that can run simultaneously.
    Returns waves where all tasks in a wave can run in parallel.

    Args:
        tasks: List of task dicts (must have 'id', optionally 'depends_on')

    Returns:
        List of waves, each wave is a list of tasks that can run in parallel
    """
    if not tasks:
        return []

    task_map = {t.get("id"): t for t in tasks}
    graph = build_dependency_graph(tasks)

    try:
        sorter = TopologicalSorter(graph)
        sorter.prepare()
    except CycleError as e:
        console.print(f"[red]Circular dependency detected:[/] {e}")
        console.print("[yellow]Falling back to sequential order[/]")
        return [[t] for t in tasks]

    waves = []
    while sorter.is_active():
        # get_ready() returns all nodes with no pending dependencies
        ready = list(sorter.get_ready())
        if not ready:
            break

        wave = [task_map[tid] for tid in ready if tid in task_map]
        waves.append(wave)

        # Mark all as done so next wave can proceed
        for tid in ready:
            sorter.done(tid)

    return waves


# =============================================================================
# 2. File-Level Conflict Prevention
# =============================================================================


@dataclass
class TaskFileMap:
    """Maps tasks to the files they're likely to modify.

    Uses heuristics from task descriptions and acceptance criteria
    to predict which files each task will touch.
    """
    task_files: Dict[str, Set[str]] = field(default_factory=dict)

    def analyze_task(self, task: dict, workspace: Path) -> Set[str]:
        """Predict files a task will modify based on its description."""
        task_id = task.get("id", "")
        files = set()

        # Extract file paths from description and criteria
        text = " ".join([
            task.get("description", ""),
            task.get("title", ""),
            " ".join(task.get("acceptanceCriteria", [])),
        ])

        # Look for file path patterns
        import re
        # Match patterns like src/up/core/state.py, tests/test_foo.py
        path_patterns = re.findall(r'[\w/]+\.(?:py|ts|js|json|md|yaml|yml)', text)
        files.update(path_patterns)

        # Match directory patterns like src/up/commands/
        dir_patterns = re.findall(r'(?:src|tests|docs)/[\w/]+', text)
        for d in dir_patterns:
            dir_path = workspace / d
            if dir_path.is_dir():
                for f in dir_path.rglob("*.py"):
                    files.add(str(f.relative_to(workspace)))

        self.task_files[task_id] = files
        return files

    def find_conflicts(self, wave: List[dict]) -> List[tuple]:
        """Find tasks in a wave that would touch the same files.

        Returns:
            List of (task_id_1, task_id_2, conflicting_files) tuples
        """
        conflicts = []
        task_ids = [t.get("id") for t in wave]

        for i, tid1 in enumerate(task_ids):
            for tid2 in task_ids[i + 1:]:
                files1 = self.task_files.get(tid1, set())
                files2 = self.task_files.get(tid2, set())
                overlap = files1 & files2
                if overlap:
                    conflicts.append((tid1, tid2, overlap))

        return conflicts

    def split_wave_by_conflicts(
        self, wave: List[dict], max_workers: int
    ) -> List[List[dict]]:
        """Split a wave into conflict-free sub-waves.

        Tasks that would touch the same files are placed in different sub-waves.
        """
        if len(wave) <= 1:
            return [wave]

        conflicts = self.find_conflicts(wave)
        if not conflicts:
            return [wave[:max_workers]]

        # Greedy coloring: assign tasks to sub-waves avoiding conflicts
        conflict_graph: Dict[str, Set[str]] = {}
        for t in wave:
            conflict_graph[t.get("id")] = set()
        for tid1, tid2, _ in conflicts:
            conflict_graph[tid1].add(tid2)
            conflict_graph[tid2].add(tid1)

        sub_waves: List[List[dict]] = []
        assigned: Dict[str, int] = {}
        task_map = {t.get("id"): t for t in wave}

        for task in wave:
            tid = task.get("id")
            # Find the first sub-wave where this task has no conflicts
            placed = False
            for i, sw in enumerate(sub_waves):
                sw_ids = {t.get("id") for t in sw}
                if not (conflict_graph[tid] & sw_ids) and len(sw) < max_workers:
                    sw.append(task)
                    assigned[tid] = i
                    placed = True
                    break
            if not placed:
                sub_waves.append([task])
                assigned[tid] = len(sub_waves) - 1

        return sub_waves


# =============================================================================
# 3. Cross-Agent Shared Knowledge
# =============================================================================


class SharedKnowledge:
    """Thread-safe shared knowledge file for cross-agent communication.

    Agents can write discoveries, warnings, and decisions that other
    agents read before starting their work.

    Stored in .up/shared_knowledge.json
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.file = workspace / ".up" / "shared_knowledge.json"
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.file.exists():
            try:
                return json.loads(self.file.read_text())
            except json.JSONDecodeError:
                pass
        return {
            "entries": [],
            "warnings": [],
            "file_locks": {},
            "completed_tasks": [],
        }

    def _save(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self._data, indent=2))

    def add_entry(self, agent_id: str, entry_type: str, content: str):
        """Add a knowledge entry from an agent."""
        with self._lock:
            self._data["entries"].append({
                "agent": agent_id,
                "type": entry_type,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            })
            self._save()

    def add_warning(self, agent_id: str, warning: str):
        """Add a warning for other agents."""
        with self._lock:
            self._data["warnings"].append({
                "agent": agent_id,
                "warning": warning,
                "timestamp": datetime.now().isoformat(),
            })
            self._save()

    def claim_files(self, agent_id: str, files: Set[str]) -> Set[str]:
        """Claim files for exclusive modification. Returns files already claimed."""
        with self._lock:
            conflicts = set()
            for f in files:
                owner = self._data["file_locks"].get(f)
                if owner and owner != agent_id:
                    conflicts.add(f)
                else:
                    self._data["file_locks"][f] = agent_id
            self._save()
            return conflicts

    def release_files(self, agent_id: str):
        """Release all file claims for an agent."""
        with self._lock:
            self._data["file_locks"] = {
                f: owner
                for f, owner in self._data["file_locks"].items()
                if owner != agent_id
            }
            self._save()

    def mark_complete(self, task_id: str):
        """Mark a task as completed (signals to dependent tasks)."""
        with self._lock:
            if task_id not in self._data["completed_tasks"]:
                self._data["completed_tasks"].append(task_id)
            self._save()

    def get_context_for_agent(self, agent_id: str) -> str:
        """Get relevant context for an agent to read before starting."""
        with self._lock:
            lines = []
            for entry in self._data["entries"][-20:]:
                if entry["agent"] != agent_id:
                    lines.append(f"[{entry['agent']}] {entry['content']}")
            for warning in self._data["warnings"][-10:]:
                lines.append(f"WARNING from {warning['agent']}: {warning['warning']}")
            return "\n".join(lines) if lines else ""

    def reset(self):
        """Reset shared knowledge for a new batch."""
        with self._lock:
            self._data = {
                "entries": [],
                "warnings": [],
                "file_locks": {},
                "completed_tasks": [],
            }
            self._save()


# =============================================================================
# 4. Parallel Progress Dashboard
# =============================================================================


@dataclass
class AgentProgress:
    """Tracks progress of a single agent."""
    task_id: str
    task_title: str
    status: str = "pending"  # pending, creating, executing, verifying, merging, done, failed
    started_at: Optional[str] = None
    duration: float = 0
    commits: int = 0
    error: Optional[str] = None


class ParallelDashboard:
    """Rich live dashboard for monitoring parallel task execution."""

    def __init__(self, console: Console):
        self._console = console
        self._agents: Dict[str, AgentProgress] = {}
        self._lock = threading.Lock()
        self._live: Optional[Live] = None
        self._wave_num: int = 0
        self._total_waves: int = 0
        self._start_time: float = 0
        self._log_lines: List[str] = []

    def start(self, total_waves: int):
        self._total_waves = total_waves
        self._start_time = time.time()
        self._live = Live(self._render(), console=self._console, refresh_per_second=2)
        self._live.start()

    def stop(self):
        if self._live:
            self._live.update(self._render())
            time.sleep(0.3)
            self._live.stop()
            self._live = None

    def set_wave(self, wave_num: int):
        self._wave_num = wave_num
        self._refresh()

    def add_agent(self, task_id: str, task_title: str):
        with self._lock:
            self._agents[task_id] = AgentProgress(
                task_id=task_id,
                task_title=task_title[:40],
                status="creating",
                started_at=datetime.now().isoformat(),
            )
        self._refresh()

    def update_agent(self, task_id: str, status: str, **kwargs):
        with self._lock:
            if task_id in self._agents:
                self._agents[task_id].status = status
                for k, v in kwargs.items():
                    if hasattr(self._agents[task_id], k):
                        setattr(self._agents[task_id], k, v)
        self._refresh()

    def log(self, message: str):
        with self._lock:
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_lines.append(f"[dim]{ts}[/] {message}")
            if len(self._log_lines) > 15:
                self._log_lines = self._log_lines[-15:]
        self._refresh()

    def _refresh(self):
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Panel:
        elapsed = time.time() - self._start_time if self._start_time else 0

        # Agent table
        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Agent", style="cyan", width=12)
        table.add_column("Task", width=35)
        table.add_column("Status", width=12)
        table.add_column("Time", width=8)

        status_icons = {
            "pending": "[dim]...[/]",
            "creating": "[yellow]setup[/]",
            "executing": "[blue]AI running[/]",
            "verifying": "[cyan]testing[/]",
            "merging": "[magenta]merging[/]",
            "done": "[green]done[/]",
            "failed": "[red]failed[/]",
            "partial": "[yellow]partial[/]",
        }

        with self._lock:
            for tid, agent in self._agents.items():
                dur = ""
                if agent.started_at:
                    try:
                        start = datetime.fromisoformat(agent.started_at)
                        dur = f"{(datetime.now() - start).seconds}s"
                    except ValueError:
                        pass
                table.add_row(
                    tid,
                    agent.task_title,
                    status_icons.get(agent.status, agent.status),
                    dur,
                )

        # Log panel
        log_text = "\n".join(self._log_lines[-10:]) if self._log_lines else "[dim]Waiting...[/]"

        # Layout
        layout = Layout()
        layout.split_column(
            Layout(Panel(
                f"Wave [cyan]{self._wave_num}[/]/{self._total_waves} | "
                f"Elapsed: [cyan]{elapsed:.0f}s[/] | "
                f"Agents: [cyan]{len(self._agents)}[/]",
                style="blue",
            ), size=3),
            Layout(table, name="agents"),
            Layout(Panel(log_text, title="Log", border_style="dim"), size=13),
        )

        return Panel(layout, title="[bold]Parallel Execution Dashboard[/]", border_style="blue")


# =============================================================================
# 5. Partial Merge for Failed Agents
# =============================================================================


def get_modified_files_in_worktree(worktree_path: Path, base: str = "main") -> List[str]:
    """Get list of files modified in worktree compared to base."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")
    except Exception:
        pass
    return []


def partial_merge(
    task_id: str,
    workspace: Path,
    target_branch: str = "main",
    exclude_patterns: List[str] = None,
) -> tuple[bool, List[str]]:
    """Cherry-pick individual passing files from a failed agent.

    When an agent fails verification but some files are good,
    this extracts the passing changes.

    Args:
        task_id: Agent task ID
        workspace: Main workspace
        target_branch: Branch to apply changes to
        exclude_patterns: File patterns to exclude

    Returns:
        Tuple of (success, list_of_merged_files)
    """
    from up.git.utils import make_branch_name

    branch = make_branch_name(task_id)
    worktree_path = workspace / ".worktrees" / task_id
    exclude = exclude_patterns or []

    if not worktree_path.exists():
        return False, []

    # Get modified files
    modified = get_modified_files_in_worktree(worktree_path)
    if not modified:
        return False, []

    # Filter out excluded patterns
    import fnmatch
    filtered = [
        f for f in modified
        if not any(fnmatch.fnmatch(f, pat) for pat in exclude)
    ]

    if not filtered:
        return False, []

    # Checkout target branch in main workspace
    result = run_git("checkout", target_branch, cwd=workspace)
    if result.returncode != 0:
        return False, []

    # Cherry-pick individual files from the agent branch
    merged_files = []
    for file_path in filtered:
        try:
            result = run_git(
                "checkout", branch, "--", file_path,
                cwd=workspace,
            )
            if result.returncode == 0:
                merged_files.append(file_path)
        except Exception:
            continue

    if merged_files:
        # Stage and commit
        run_git("add", *merged_files, cwd=workspace)
        run_git(
            "commit", "-m",
            f"partial({task_id}): Cherry-pick {len(merged_files)} passing files",
            cwd=workspace,
        )

    return bool(merged_files), merged_files


# =============================================================================
# Enhanced Parallel Loop (combines all 5 improvements)
# =============================================================================


def run_enhanced_parallel_loop(
    workspace: Path,
    prd_path: Path,
    max_workers: int = 3,
    run_all: bool = False,
    timeout: int = 600,
    dry_run: bool = False,
    enable_conflict_check: bool = True,
    enable_partial_merge: bool = True,
) -> dict:
    """Run the enhanced parallel product loop.

    Improvements over the basic run_parallel_loop:
    1. Respects depends_on ordering (wave-based scheduling)
    2. Detects file conflicts before execution
    3. Shared knowledge between agents
    4. Rich live dashboard
    5. Partial merge for failed agents

    Args:
        workspace: Project root directory
        prd_path: Path to prd.json
        max_workers: Number of parallel tasks per wave
        run_all: Whether to run all tasks or just first wave
        timeout: AI timeout per task
        dry_run: Preview without executing
        enable_conflict_check: Analyze files for conflicts
        enable_partial_merge: Cherry-pick from failed agents
    """
    state_mgr = ParallelExecutionManager(workspace)
    state_mgr.set_active(True)
    knowledge = SharedKnowledge(workspace)
    knowledge.reset()

    summary = {
        "waves": 0,
        "completed": [],
        "failed": [],
        "partial_merged": [],
        "skipped_conflicts": [],
        "total_duration": 0,
    }

    start_time = time.time()

    # Load all pending tasks (cross-checked against state)
    if not prd_path.exists():
        console.print("[red]PRD file not found[/]")
        return summary

    try:
        from up.parallel import get_pending_tasks
        all_tasks = get_pending_tasks(prd_path, workspace=workspace)
    except Exception:
        # Fallback: direct read
        try:
            data = json.loads(prd_path.read_text())
            all_tasks = [s for s in data.get("userStories", []) if not s.get("passes", False)]
        except json.JSONDecodeError:
            console.print("[red]Invalid PRD JSON[/]")
            return summary

    if not all_tasks:
        console.print("[green]All tasks complete![/]")
        return summary

    # Build dependency-aware execution waves
    waves = get_execution_waves(all_tasks)
    console.print(f"\n[bold]Scheduling:[/] {len(all_tasks)} tasks in {len(waves)} waves")

    for i, wave in enumerate(waves):
        ids = [t.get("id") for t in wave]
        console.print(f"  Wave {i + 1}: {', '.join(ids)}")

    if dry_run:
        console.print("\n[yellow]DRY RUN[/] - No changes made")
        # Show file conflict analysis
        if enable_conflict_check:
            file_map = TaskFileMap()
            for task in all_tasks:
                file_map.analyze_task(task, workspace)
            for i, wave in enumerate(waves):
                conflicts = file_map.find_conflicts(wave)
                if conflicts:
                    console.print(f"\n  [yellow]Wave {i + 1} conflicts:[/]")
                    for t1, t2, files in conflicts:
                        console.print(f"    {t1} <-> {t2}: {', '.join(files)}")
        return summary

    # Check AI availability
    cli_name, cli_available = check_ai_cli()
    if not cli_available:
        console.print("[red]No AI CLI found[/]")
        return summary

    # File conflict analysis
    file_map = TaskFileMap()
    if enable_conflict_check:
        for task in all_tasks:
            file_map.analyze_task(task, workspace)

    # Start dashboard
    dashboard = ParallelDashboard(console)
    dashboard.start(total_waves=len(waves))

    try:
        for wave_idx, wave in enumerate(waves):
            wave_num = wave_idx + 1
            dashboard.set_wave(wave_num)
            summary["waves"] += 1
            dashboard.log(f"Starting wave {wave_num}/{len(waves)} ({len(wave)} tasks)")

            # Split wave by file conflicts if enabled
            if enable_conflict_check:
                sub_waves = file_map.split_wave_by_conflicts(wave, max_workers)
                if len(sub_waves) > 1:
                    dashboard.log(
                        f"Wave {wave_num} split into {len(sub_waves)} "
                        f"sub-waves to avoid conflicts"
                    )
            else:
                sub_waves = [wave[:max_workers]]

            for sub_wave in sub_waves:
                _execute_wave(
                    workspace=workspace,
                    tasks=sub_wave,
                    cli_name=cli_name,
                    timeout=timeout,
                    max_workers=max_workers,
                    state_mgr=state_mgr,
                    knowledge=knowledge,
                    dashboard=dashboard,
                    prd_path=prd_path,
                    summary=summary,
                    enable_partial_merge=enable_partial_merge,
                )

            if not run_all:
                break

    finally:
        dashboard.stop()
        state_mgr.set_active(False)

    summary["total_duration"] = time.time() - start_time

    # Print summary
    _print_enhanced_summary(summary)

    return summary


def _execute_wave(
    workspace: Path,
    tasks: List[dict],
    cli_name: str,
    timeout: int,
    max_workers: int,
    state_mgr: ParallelExecutionManager,
    knowledge: SharedKnowledge,
    dashboard: ParallelDashboard,
    prd_path: Path,
    summary: dict,
    enable_partial_merge: bool,
):
    """Execute a single wave of tasks in parallel."""
    # Phase 1: Create worktrees
    worktrees = []
    for task in tasks:
        task_id = task.get("id")
        task_title = task.get("title", task_id)
        dashboard.add_agent(task_id, task_title)
        dashboard.log(f"Creating worktree for {task_id}")

        try:
            wt_path, wt_state = create_worktree(task_id, task_title)
            worktrees.append({"path": wt_path, "state": wt_state, "task": task})
            state_mgr.add_active_worktree(task_id)

            # Write shared context into worktree
            context = knowledge.get_context_for_agent(task_id)
            if context:
                ctx_file = wt_path / ".agent_context.md"
                ctx_file.write_text(f"# Context from other agents\n\n{context}\n")

            dashboard.update_agent(task_id, "executing")
        except Exception as e:
            dashboard.update_agent(task_id, "failed", error=str(e))
            dashboard.log(f"[red]Failed to create worktree for {task_id}: {e}[/]")

    if not worktrees:
        return

    # Phase 2: Execute in parallel
    results: Dict[str, TaskResult] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(worktrees))) as executor:
        futures: Dict[Future, str] = {}
        for wt in worktrees:
            tid = wt["task"].get("id")
            future = executor.submit(
                execute_task_in_worktree, wt["path"], wt["task"], cli_name, timeout
            )
            futures[future] = tid

        for future in as_completed(futures):
            tid = futures[future]
            try:
                result = future.result()
                results[tid] = result
                if result.success:
                    dashboard.update_agent(tid, "verifying")
                    dashboard.log(f"{tid}: AI execution complete")
                    knowledge.add_entry(tid, "completion", f"Task {tid} implemented successfully")
                else:
                    dashboard.update_agent(tid, "failed", error=result.error)
                    dashboard.log(f"[red]{tid}: execution failed[/]")
                    knowledge.add_warning(tid, f"Task {tid} failed: {result.error or 'unknown'}")
            except Exception as e:
                results[tid] = TaskResult(tid, False, "failed", 0, error=str(e))
                dashboard.update_agent(tid, "failed", error=str(e))

    # Phase 3: Verify passing tasks
    for wt in worktrees:
        tid = wt["task"].get("id")
        if results.get(tid, TaskResult("", False, "failed", 0)).success:
            dashboard.log(f"Verifying {tid}...")
            verify_result = verify_worktree(wt["path"])
            results[tid] = verify_result
            if verify_result.success:
                dashboard.update_agent(tid, "merging")
            else:
                dashboard.update_agent(tid, "failed")
                dashboard.log(f"[yellow]{tid}: verification failed[/]")

    # Phase 4: Merge passing tasks + partial merge for failures
    for wt in worktrees:
        tid = wt["task"].get("id")
        result = results.get(tid)

        if result and result.success:
            dashboard.log(f"Merging {tid}...")
            if merge_worktree(tid):
                dashboard.update_agent(tid, "done")
                dashboard.log(f"[green]{tid}: merged[/]")
                summary["completed"].append(tid)
                state_mgr.record_task_complete(tid)
                knowledge.mark_complete(tid)
                _mark_task_complete(prd_path, tid)
            else:
                dashboard.update_agent(tid, "failed", error="merge conflict")
                dashboard.log(f"[red]{tid}: merge failed[/]")
                summary["failed"].append(tid)
                state_mgr.record_task_failed(tid)
        else:
            # Try partial merge if enabled
            if enable_partial_merge and result and result.error != "merge conflict":
                dashboard.log(f"Attempting partial merge for {tid}...")
                success, files = partial_merge(tid, workspace)
                if success:
                    dashboard.update_agent(tid, "partial")
                    dashboard.log(
                        f"[yellow]{tid}: partial merge ({len(files)} files)[/]"
                    )
                    summary["partial_merged"].append({
                        "task_id": tid,
                        "files": files,
                    })
                else:
                    summary["failed"].append(tid)
                    state_mgr.record_task_failed(tid)
            else:
                summary["failed"].append(tid)
                state_mgr.record_task_failed(tid)

        # Cleanup
        state_mgr.remove_active_worktree(tid)
        knowledge.release_files(tid)


def _print_enhanced_summary(summary: dict):
    """Print enhanced execution summary."""
    console.print(f"\n{'═' * 55}")
    console.print("[bold]PARALLEL EXECUTION SUMMARY[/]")
    console.print("═" * 55)

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    table.add_row("Waves", str(summary["waves"]))
    table.add_row("Completed", f"[green]{len(summary['completed'])}[/]")
    table.add_row("Failed", f"[red]{len(summary['failed'])}[/]")
    table.add_row("Partial", f"[yellow]{len(summary['partial_merged'])}[/]")
    table.add_row("Duration", f"{summary['total_duration']:.1f}s")

    console.print(table)

    if summary["completed"]:
        console.print(f"\n[green]Completed:[/] {', '.join(summary['completed'])}")
    if summary["partial_merged"]:
        for pm in summary["partial_merged"]:
            console.print(
                f"[yellow]Partial ({pm['task_id']}):[/] {len(pm['files'])} files merged"
            )
    if summary["failed"]:
        console.print(f"[red]Failed:[/] {', '.join(summary['failed'])}")
