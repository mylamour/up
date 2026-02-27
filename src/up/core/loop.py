"""Loop Orchestrator — library-level product loop logic.

Separates pure orchestration (state, tasks, circuit breakers, checkpoints)
from CLI/display concerns. Both ``up start`` and Cursor/Claude skills use this.

The orchestrator never prints, never prompts, never shells out to AI CLIs.
It returns data that callers act on.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from up.core.checkpoint import CheckpointManager, NotAGitRepoError, get_checkpoint_manager
from up.core.provenance import ProvenanceEntry, ProvenanceManager, get_provenance_manager
from up.core.state import StateManager, get_state_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Result Data Classes
# =============================================================================

@dataclass
class CircuitBreakerStatus:
    """Result of a circuit breaker check."""
    can_execute: bool
    circuit_name: str | None = None
    state: str = "CLOSED"
    failures: int = 0
    message: str = ""


@dataclass
class TaskInfo:
    """A task to execute."""
    id: str
    title: str
    description: str = ""
    priority: str = "medium"
    acceptance_criteria: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskInfo":
        return cls(
            id=data.get("id", "unknown"),
            title=data.get("title", ""),
            description=data.get("description", data.get("title", "")),
            priority=data.get("priority", "medium"),
            acceptance_criteria=data.get("acceptanceCriteria", []),
            files=data.get("files", []),
            depends_on=data.get("depends_on", []),
        )


@dataclass
class BeginTaskResult:
    """Result of beginning a task."""
    success: bool
    checkpoint_id: str | None = None
    provenance_id: str | None = None
    error: str | None = None


@dataclass
class TaskPrompts:
    """Prompts for each phase of task execution."""
    research: str = ""
    plan: str = ""
    implement: str = ""
    memory_hint: str | None = None


@dataclass
class FailureResult:
    """Result of recording a failure."""
    rolled_back: bool = False
    circuit_open: bool = False
    doom_loop: bool = False
    message: str = ""
    consecutive_failures: int = 0


@dataclass
class SuccessResult:
    """Result of recording a success."""
    task_id: str = ""
    committed: bool = False
    commit_message: str = ""


@dataclass
class VerificationCommands:
    """Shell commands for verification, usable by skills."""
    test_cmd: str = ""
    lint_cmd: str = ""
    type_check_cmd: str = ""


# =============================================================================
# Loop Orchestrator
# =============================================================================

class LoopOrchestrator:
    """Library-level product loop orchestration.

    Manages state transitions, task selection, circuit breakers, checkpoints,
    and provenance — without any CLI, display, or AI subprocess dependencies.

    Usage (from CLI)::

        orch = LoopOrchestrator(workspace)
        tasks = orch.get_tasks(task_source="prd.json")
        for task in tasks:
            result = orch.begin_task(task)
            # ... run AI phases ...
            orch.record_success(task)

    Usage (from skill/Cursor)::

        orch = LoopOrchestrator(workspace)
        task = orch.get_next_task(task_source="prd.json")
        result = orch.begin_task(task)
        prompts = orch.build_prompts(task, "prd.json")
        cmds = orch.get_verification_commands()
        # ... skill executes prompts and cmds directly ...
        orch.record_success(task)
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self._sm: StateManager | None = None
        self._cm: CheckpointManager | None = None
        self._pm: ProvenanceManager | None = None
        self._current_provenance: ProvenanceEntry | None = None

    @property
    def state_manager(self) -> StateManager:
        if self._sm is None:
            self._sm = get_state_manager(self.workspace)
        return self._sm

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        if self._cm is None:
            self._cm = get_checkpoint_manager(self.workspace)
        return self._cm

    @property
    def provenance_manager(self) -> ProvenanceManager:
        if self._pm is None:
            self._pm = get_provenance_manager(self.workspace)
        return self._pm

    # -----------------------------------------------------------------
    # Task selection
    # -----------------------------------------------------------------

    def find_task_source(self, prd_path: str | None = None) -> str | None:
        """Locate the task source file (PRD or TODO)."""
        if prd_path:
            return prd_path
        candidates = [
            "prd.json",
            ".claude/skills/learning-system/prd.json",
            ".cursor/skills/learning-system/prd.json",
            "TODO.md",
            "docs/todo/TODO.md",
        ]
        for c in candidates:
            if (self.workspace / c).exists():
                return c
        return None

    def get_next_task(
        self,
        task_source: str | None = None,
        specific_task: str | None = None,
    ) -> TaskInfo | None:
        """Get the single next task to execute.

        If *specific_task* is given, returns a stub TaskInfo for it.
        Otherwise reads the PRD and returns the first incomplete story
        not already in ``tasks_completed``.
        """
        if specific_task:
            return TaskInfo(id=specific_task, title=specific_task, description=specific_task)

        source = task_source or self.find_task_source()
        if not source:
            return None

        task_dict = self._next_from_prd(source)
        if task_dict is None:
            return None
        return TaskInfo.from_dict(task_dict)

    def get_tasks(
        self,
        task_source: str | None = None,
        specific_task: str | None = None,
        run_all: bool = False,
    ) -> list[TaskInfo]:
        """Get task(s) to execute. Returns a list (possibly empty)."""
        if specific_task:
            return [TaskInfo(id=specific_task, title=specific_task, description=specific_task)]

        source = task_source or self.find_task_source()
        if not source or not source.endswith(".json"):
            task = self.get_next_task(task_source=source)
            return [task] if task else []

        from dataclasses import asdict

        from up.core.prd_schema import PRDValidationError, load_prd

        prd_path = self.workspace / source
        try:
            prd = load_prd(prd_path)
        except PRDValidationError:
            return []

        completed = set(self.state_manager.state.loop.tasks_completed)
        tasks: list[TaskInfo] = []
        for story in prd.userStories:
            if story.passes or story.id in completed:
                continue
            tasks.append(TaskInfo.from_dict(asdict(story)))
            if not run_all:
                break
        return tasks

    def _next_from_prd(self, task_source: str) -> dict | None:
        """Get next incomplete task dict from PRD file.

        Reads the PRD directly to avoid circular imports
        (core must not import from commands layer).
        """
        from dataclasses import asdict

        from up.core.prd_schema import PRDValidationError, load_prd

        prd_path = self.workspace / task_source
        if not prd_path.exists():
            return None

        try:
            prd = load_prd(prd_path)
        except PRDValidationError:
            return None

        completed = set(self.state_manager.state.loop.tasks_completed)
        for story in prd.userStories:
            if story.passes or story.id in completed:
                continue
            return asdict(story)
        return None

    # -----------------------------------------------------------------
    # Circuit breaker
    # -----------------------------------------------------------------

    def check_circuit_breaker(self) -> CircuitBreakerStatus:
        """Check whether the task circuit breaker allows execution."""
        cb = self.state_manager.get_circuit_breaker("task")
        can = cb.can_execute()
        # Persist any OPEN→HALF_OPEN transition
        if cb.state == "HALF_OPEN":
            self.state_manager.save()
        return CircuitBreakerStatus(
            can_execute=can,
            circuit_name="task",
            state=cb.state,
            failures=cb.failures,
            message="" if can else f"Circuit breaker OPEN after {cb.failures} failures",
        )

    def reset_circuit_breaker(self) -> None:
        """Reset all circuit breakers (used by --resume)."""
        for cb in self.state_manager.state.circuit_breakers.values():
            cb.failures = 0
            cb.state = "CLOSED"
            cb.opened_at = None
        self.state_manager.state.loop.consecutive_failures = 0
        self.state_manager.save()

    # -----------------------------------------------------------------
    # Task lifecycle
    # -----------------------------------------------------------------

    def begin_task(self, task: TaskInfo, task_source: str | None = None) -> BeginTaskResult:
        """Begin a task: bump iteration, create checkpoint, start provenance.

        Returns a result indicating whether the task can proceed.
        """
        sm = self.state_manager

        # Update loop state
        new_iter = sm.state.loop.iteration + 1
        sm.update_loop(
            iteration=new_iter,
            phase="EXECUTE",
            current_task=task.id,
        )

        # Create checkpoint
        checkpoint_id = f"cp-{task.id}-{new_iter}"
        try:
            self.checkpoint_manager.save(message=checkpoint_id, task_id=task.id)
        except NotAGitRepoError:
            return BeginTaskResult(success=False, error="Not a git repo — no checkpoint safety net")
        except Exception as exc:
            return BeginTaskResult(success=False, error=f"Checkpoint failed: {exc}")

        sm.update_loop(last_checkpoint=checkpoint_id)

        # Start provenance tracking
        provenance_id = None
        try:
            source = task_source or self.find_task_source() or ""
            entry = self.provenance_manager.start_operation(
                task_id=task.id,
                task_title=task.title,
                prompt=f"Task {task.id}: {task.title}",
                ai_model="orchestrator",
                context_files=[source] if source else [],
            )
            self._current_provenance = entry
            provenance_id = entry.id
        except Exception as exc:
            logger.debug("Provenance tracking failed: %s", exc)

        return BeginTaskResult(
            success=True,
            checkpoint_id=checkpoint_id,
            provenance_id=provenance_id,
        )

    # -----------------------------------------------------------------
    # Prompts
    # -----------------------------------------------------------------

    def build_prompts(self, task: TaskInfo, task_source: str | None = None) -> TaskPrompts:
        """Build AI prompts for all three phases.

        These are the same prompts used by ``up start`` but returned as
        data so skills can feed them to the AI directly.
        """
        from up.commands.start.helpers import (
            build_implement_prompt,
            build_plan_prompt,
            build_research_prompt,
        )

        source = task_source or self.find_task_source() or ""
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "acceptanceCriteria": task.acceptance_criteria,
            "files": task.files,
            "depends_on": task.depends_on,
        }

        hint = self.get_memory_hint(task)

        return TaskPrompts(
            research=build_research_prompt(self.workspace, task_dict, source),
            plan=build_plan_prompt(self.workspace, task_dict, source),
            implement=build_implement_prompt(self.workspace, task_dict, source),
            memory_hint=hint,
        )

    def get_memory_hint(self, task: TaskInfo) -> str | None:
        """Query memory for hints relevant to this task."""
        try:
            from up.memory import MemoryManager
            from up.memory.patterns import ErrorPatternExtractor

            state_file = self.workspace / ".up" / "state.json"
            if not state_file.exists():
                return None

            data = json.loads(state_file.read_text())
            last_error = data.get("loop", {}).get("last_error", "")
            if not last_error:
                return None

            extractor = ErrorPatternExtractor()
            keywords = extractor.extract(last_error)
            if not keywords:
                return None

            manager = MemoryManager(self.workspace, use_vectors=False)
            results = manager.search(" ".join(keywords), limit=3, entry_type="error")
            if not results:
                return None

            best = results[0]
            content = best.content if hasattr(best, "content") else str(best)
            return (
                f"Past solution found:\n"
                f"Previously, a similar error was solved by: {content}\n"
                f"Consider this approach."
            )
        except Exception as exc:
            logger.debug("Memory hint lookup failed: %s", exc)
            return None

    # -----------------------------------------------------------------
    # Success / failure recording
    # -----------------------------------------------------------------

    def record_success(
        self,
        task: TaskInfo,
        task_source: str | None = None,
        tests_passed: bool | None = None,
        lint_passed: bool | None = None,
        type_check_passed: bool | None = None,
        files_modified: list[str] | None = None,
    ) -> SuccessResult:
        """Record a successful task completion.

        Updates state, marks PRD complete, completes provenance.
        Does NOT commit — caller decides whether to commit.
        """
        sm = self.state_manager

        # Mark task complete in PRD
        source = task_source or self.find_task_source()
        if source and source.endswith(".json"):
            from up.commands.start.helpers import mark_task_complete
            mark_task_complete(self.workspace, source, task.id)

        # Update state
        sm.record_task_complete(task.id)
        sm.update_loop(phase="COMMIT", current_task=task.id)

        # Reset circuit breaker on success
        cb = sm.get_circuit_breaker("task")
        cb.record_success()
        sm.save()

        # Complete provenance
        if self._current_provenance:
            try:
                self.provenance_manager.complete_operation(
                    entry_id=self._current_provenance.id,
                    files_modified=files_modified or [],
                    tests_passed=tests_passed,
                    lint_passed=lint_passed,
                    type_check_passed=type_check_passed,
                    status="accepted",
                )
            except Exception as exc:
                logger.debug("Failed to complete provenance: %s", exc)
            self._current_provenance = None

        return SuccessResult(
            task_id=task.id,
            commit_message=f"feat({task.id}): {task.title}",
        )

    def record_failure(
        self,
        task: TaskInfo,
        error: str | None = None,
        rollback: bool = True,
    ) -> FailureResult:
        """Record a task failure.

        Rolls back checkpoint, updates circuit breaker, checks doom loop.
        """
        sm = self.state_manager

        # Rollback
        rolled_back = False
        if rollback:
            try:
                from up.commands.start.helpers import rollback_checkpoint
                rolled_back = rollback_checkpoint(self.workspace)
                if rolled_back:
                    sm.record_rollback()
            except Exception as exc:
                logger.debug("Rollback failed: %s", exc)

        # Record failure in state
        sm.record_task_failed(task.id)

        # Store last error for memory hint on retry
        if error:
            try:
                sm.state.loop.__dict__["last_error"] = error[:1000]
                sm.save()
            except Exception:
                pass

        # Circuit breaker
        cb = sm.get_circuit_breaker("task")
        cb.record_failure()
        sm.save()
        circuit_open = not cb.can_execute()

        # Doom loop check
        is_doom, doom_msg = sm.check_doom_loop()

        # Reject provenance
        if self._current_provenance:
            try:
                self.provenance_manager.reject_operation(
                    self._current_provenance.id,
                    reason=error[:500] if error else "Task failed",
                )
            except Exception as exc:
                logger.debug("Failed to reject provenance: %s", exc)
            self._current_provenance = None

        return FailureResult(
            rolled_back=rolled_back,
            circuit_open=circuit_open,
            doom_loop=is_doom,
            message=doom_msg if is_doom else (
                "Circuit breaker OPEN" if circuit_open else ""
            ),
            consecutive_failures=sm.state.loop.consecutive_failures,
        )

    # -----------------------------------------------------------------
    # Verification
    # -----------------------------------------------------------------

    def get_verification_commands(self) -> VerificationCommands:
        """Return shell commands for verification.

        Skills can run these directly via Bash tool instead of
        importing subprocess-based verification code.
        """
        cfg = self.state_manager.config
        return VerificationCommands(
            test_cmd="python3 -m pytest -x -q --tb=short 2>&1 | tail -20",
            lint_cmd="python3 -m ruff check . 2>&1 | tail -10",
            type_check_cmd="python3 -m mypy src/ --ignore-missing-imports --no-error-summary 2>&1 | tail -10",
        )

    def run_verification(self):
        """Run verification using subprocess (works in both CLI and skill).

        Returns a VerificationResult from the verification module.
        """
        from up.commands.start.verification import run_full_verification
        return run_full_verification(self.workspace)

    def check_verification(self, result) -> bool:
        """Check if verification result passes required checks."""
        required = self.state_manager.config.verify_required_checks
        return result.all_required_passed(required)

    # -----------------------------------------------------------------
    # Status / summary
    # -----------------------------------------------------------------

    def get_status(self) -> dict:
        """Return current loop status as a plain dict."""
        sm = self.state_manager
        loop = sm.state.loop
        cb = sm.get_circuit_breaker("task")
        return {
            "iteration": loop.iteration,
            "phase": loop.phase,
            "current_task": loop.current_task,
            "tasks_completed": list(loop.tasks_completed),
            "tasks_failed": list(loop.tasks_failed),
            "consecutive_failures": loop.consecutive_failures,
            "circuit_breaker": cb.state,
            "success_rate": sm.state.metrics.success_rate,
        }

    def mark_interrupted(self) -> None:
        """Mark the current task as interrupted (for signal handlers)."""
        import time
        sm = self.state_manager
        sm.update_loop(
            phase="INTERRUPTED",
            interrupted_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        if self._current_provenance:
            try:
                self.provenance_manager.reject_operation(
                    self._current_provenance.id,
                    reason="User interrupted operation",
                )
            except Exception:
                pass
            self._current_provenance = None

    def set_idle(self) -> None:
        """Set loop phase to IDLE (end of loop)."""
        self.state_manager.update_loop(phase="IDLE", current_task=None)
