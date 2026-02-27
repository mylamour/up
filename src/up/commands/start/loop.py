"""Product loop execution (AI and manual modes).

Contains the main AI product loop and manual/preview modes.
"""

import json
import logging
import signal
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from tqdm import tqdm

from up.ai_cli import run_ai_task
from up.commands.start.helpers import (
    build_implement_prompt,
    build_plan_prompt,
    build_research_prompt,
    get_next_task_from_prd,
    save_loop_state,
)
from up.commands.start.verification import (
    commit_changes,
    get_diff_summary,
    get_modified_files,
)
from up.core.loop import LoopOrchestrator
from up.core.prd_schema import PRDValidationError, load_prd
from up.ui import ProductLoopDisplay, TaskStatus
from up.ui.loop_display import LoopStatus

console = Console()
logger = logging.getLogger(__name__)


def _get_memory_hint(workspace: Path, task: dict) -> str | None:
    """Check for memory hints from auto-recall for the current task.

    Returns a formatted hint string to prepend to the AI prompt, or None.
    """
    try:
        from up.memory import MemoryManager
        from up.memory.patterns import ErrorPatternExtractor

        # Check if there's a recent error for this task in state
        state_file = workspace / ".up" / "state.json"
        if not state_file.exists():
            return None

        state_data = json.loads(state_file.read_text())
        last_error = state_data.get("loop", {}).get("last_error", "")
        if not last_error:
            return None

        extractor = ErrorPatternExtractor()
        keywords = extractor.extract(last_error)
        if not keywords:
            return None

        query = " ".join(keywords)
        manager = MemoryManager(workspace, use_vectors=False)
        results = manager.search(query, limit=3, entry_type="error")

        if not results:
            return None

        best = results[0]
        content = best.content if hasattr(best, "content") else str(best)
        ts = best.timestamp if hasattr(best, "timestamp") else "unknown"

        logger.info("Memory recall: applied hint from %s", ts)
        return (
            f"Past solution found:\n"
            f"Previously, a similar error was solved by: {content}\n"
            f"Consider this approach."
        )
    except Exception as exc:
        logger.debug("Memory hint lookup failed: %s", exc)
        return None


def _restore_terminal():
    """Restore terminal to sane state after Rich Live display."""
    try:
        import os
        if os.isatty(sys.stdin.fileno()):
            os.system("stty sane 2>/dev/null")
    except Exception:
        pass


# Global state for interrupt handling
_orchestrator: LoopOrchestrator | None = None
_current_workspace = None
_current_display: ProductLoopDisplay | None = None


def handle_interrupt(signum, frame):
    """Handle Ctrl+C interrupt - save state and checkpoint info."""
    global _current_display

    # Stop the display first if active
    if _current_display:
        _current_display.set_status(LoopStatus.PAUSED)
        _current_display.log_warning("Interrupted by user")
        time.sleep(0.3)
        _current_display.stop()
        _current_display = None

    _restore_terminal()
    console.print("\n\n[yellow]Interrupted! Saving state...[/]")

    if _orchestrator and _current_workspace:
        _orchestrator.mark_interrupted()
        console.print("[green]✓[/] State saved to .up/state.json")
        last_cp = _orchestrator.state_manager.state.loop.last_checkpoint
        console.print(f"[dim]Checkpoint: {last_cp or 'none'}[/]")
        console.print("\nTo resume: [cyan]up start --resume[/]")
        console.print("To rollback: [cyan]up reset[/]")

    sys.exit(130)


def preview_loop(workspace: Path, state: dict, task_source: str, specific_task: str = None):
    """Preview what the loop would do."""
    console.print("\n[bold]Preview:[/]")

    phases = [
        ("OBSERVE", "Read task and understand requirements"),
        ("CHECKPOINT", "Create git stash checkpoint"),
        ("EXECUTE", "Implement the task"),
        ("VERIFY", "Run tests, types, lint"),
        ("COMMIT", "Update state and commit"),
    ]

    console.print()
    for phase, desc in tqdm(phases, desc="Phases", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"):
        time.sleep(0.3)

    console.print()
    for phase, desc in phases:
        console.print(f"  [cyan]{phase}[/]: {desc}")

    if specific_task:
        console.print(f"\n  Target task: [cyan]{specific_task}[/]")
    elif task_source and task_source.endswith(".json"):
        next_task = get_next_task_from_prd(workspace / task_source)
        if next_task:
            console.print(f"\n  Next task: [cyan]{next_task.get('id')}[/] - {next_task.get('title')}")


def run_manual_loop(
    workspace: Path,
    state: dict,
    task_source: str,
    specific_task: str = None,
    resume: bool = False,
):
    """Run the product loop with progress indicators (manual mode)."""
    if not resume:
        state["iteration"] = state.get("iteration", 0) + 1
        state["phase"] = "OBSERVE"
        state["started_at"] = datetime.now().isoformat()

    next_task = None
    if specific_task:
        next_task = {"id": specific_task, "title": specific_task}
    elif task_source and task_source.endswith(".json"):
        next_task = get_next_task_from_prd(workspace / task_source)

    if next_task:
        console.print(f"\n[bold]Task:[/] [cyan]{next_task.get('id')}[/] - {next_task.get('title', 'N/A')}")

    phases = [
        ("OBSERVE", "Reading task requirements"),
        ("CHECKPOINT", "Creating checkpoint"),
        ("EXECUTE", "Ready for implementation"),
        ("VERIFY", "Verification pending"),
        ("COMMIT", "Awaiting completion"),
    ]

    console.print("\n[bold]Loop Progress:[/]")

    with tqdm(
        total=len(phases),
        desc="Initializing loop",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    ) as pbar:
        for i, (phase, desc) in enumerate(phases):
            state["phase"] = phase
            pbar.set_description(f"{phase}: {desc}")
            pbar.update(1)
            if i >= 2:
                break
            time.sleep(0.5)

    save_loop_state(workspace, state)

    console.print("\n" + "─" * 50)
    console.print("\n[bold green]✓[/] Loop initialized at [cyan]EXECUTE[/] phase")

    instructions = _generate_loop_instructions(workspace, state, task_source, specific_task)
    console.print(Panel(instructions, title="[bold]AI Instructions[/]", border_style="green"))

    console.print("\n[bold]Next Steps:[/]")
    console.print("  1. Use [cyan]/product-loop[/] in your AI assistant")
    console.print("  2. Or implement the task manually")
    console.print("  3. Run [cyan]up status[/] to check progress")
    console.print("  4. Run [cyan]up dashboard[/] for live monitoring")


def _generate_loop_instructions(
    workspace: Path, state: dict, task_source: str, specific_task: str = None
) -> str:
    """Generate instructions for the AI to execute the loop."""
    task_info = ""
    if specific_task:
        task_info = f"Task: {specific_task}"
    elif task_source:
        next_task = None
        if task_source.endswith(".json"):
            next_task = get_next_task_from_prd(workspace / task_source)

        if next_task:
            task_info = f"Task: {next_task.get('id')} - {next_task.get('title')}"
            if next_task.get("acceptanceCriteria"):
                criteria = next_task.get("acceptanceCriteria", [])[:3]
                task_info += "\n\nAcceptance Criteria:"
                for c in criteria:
                    task_info += f"\n  • {c}"
        else:
            task_info = f"Source: {task_source}"

    return f"""Iteration #{state.get('iteration', 1)} - Phase: EXECUTE

{task_info}

SESRC Loop Commands:
  ├─ Checkpoint: up save (creates git checkpoint)
  ├─ Verify: pytest && mypy src/ && ruff check src/
  ├─ Rollback: up reset (restores last checkpoint)
  └─ Complete: up status (view progress)

Circuit Breaker: 3 consecutive failures → OPEN
State File: .up/state.json
"""


def run_ai_product_loop(
    workspace: Path,
    state: dict,
    task_source: str,
    specific_task: str = None,
    cli_name: str = "claude",
    run_all: bool = False,
    timeout: int = 600,
    auto_commit: bool = False,
    verify: bool = True,
    interactive: bool = False,
    use_sdk: bool = False,
):
    """Run the product loop with AI auto-implementation.

    By default runs autonomously (no prompts). When ``interactive=True``,
    pauses for human review after the plan phase and on verification failure.
    """
    global _orchestrator, _current_workspace, _current_display

    _current_workspace = workspace
    orch = LoopOrchestrator(workspace)
    _orchestrator = orch
    signal.signal(signal.SIGINT, handle_interrupt)

    # Use orchestrator for task selection
    tasks_to_run = orch.get_tasks(
        task_source=task_source,
        specific_task=specific_task,
        run_all=run_all,
    )

    if not tasks_to_run:
        console.print("\n[green]✓[/] All tasks completed!")
        return

    # Build all_tasks for display (need full PRD list)
    all_tasks = []
    if task_source and task_source.endswith(".json"):
        prd_path = workspace / task_source
        try:
            prd = load_prd(prd_path)
            all_tasks = [asdict(s) for s in prd.userStories]
        except PRDValidationError:
            pass
    if not all_tasks:
        all_tasks = [{"id": t.id, "title": t.title} for t in tasks_to_run]

    # Initialize display
    display = ProductLoopDisplay(console)
    _current_display = display
    display.set_tasks(all_tasks)
    display.start()
    display.log(f"Starting product loop with {len(tasks_to_run)} tasks")
    display.log(f"AI CLI: {cli_name} (timeout: {timeout}s)")

    completed = 0
    failed = 0

    try:
        for task in tasks_to_run:
            task_id = task.id
            task_title = task.title

            display.set_current_task(task_id, "CHECKPOINT")
            display.increment_iteration()
            display.log(f"Starting task {task_id}: {task_title[:40]}...")

            # Begin task via orchestrator (state + checkpoint + provenance)
            begin_result = orch.begin_task(task, task_source=task_source)
            if not begin_result.success:
                display.log_error(f"Checkpoint failed for {task_id} — {begin_result.error}")
                failed += 1
                display.update_task_status(task_id, TaskStatus.FAILED)
                orch.state_manager.record_task_failed(task_id)
                continue
            display.log_success(f"Checkpoint: {begin_result.checkpoint_id}")
            if begin_result.provenance_id:
                display.log(f"Provenance: {begin_result.provenance_id[:8]}...")

            # Build task dict for prompt helpers
            task_dict = {
                "id": task.id, "title": task.title,
                "description": task.description, "priority": task.priority,
                "acceptanceCriteria": task.acceptance_criteria,
                "files": task.files, "depends_on": task.depends_on,
            }

            # Phase 1: Research
            display.set_phase("RESEARCH")
            display.log(f"Phase 1/3: Researching {task_id}...")
            display.log(f"  AI running: {cli_name} (timeout {timeout}s)")
            prompt = build_research_prompt(workspace, task_dict, task_source)

            # Run Phase 1
            def _on_ai_output(line: str):
                display.log(f"  {line[:120]}")

            success, output = run_ai_task(
                workspace, prompt, cli_name, timeout=timeout,
                on_output=_on_ai_output, use_sdk=use_sdk,
            )
            if success:
                display.log_success("Research complete")
            else:
                display.log_error("Research failed")

            # Phase 2: Plan
            if success:
                display.set_phase("PLAN")
                display.log("Phase 2/3: Planning implementation...")
                display.log(f"  AI running: {cli_name} (timeout {timeout}s)")
                prompt = build_plan_prompt(workspace, task_dict, task_source)
                success, output = run_ai_task(
                    workspace, prompt, cli_name, timeout=timeout,
                    continue_session=True, on_output=_on_ai_output,
                    use_sdk=use_sdk,
                )
                if success:
                    display.log_success("Plan complete")
                else:
                    display.log_error("Plan failed")

            # Human Review Gate (only in interactive mode)
            if success and interactive:
                display.stop()
                console.print(f"\n[bold]Plan for {task_id}:[/] .up/thoughts/plan.md")
                from rich.prompt import Confirm
                if not Confirm.ask("Proceed with implementation?", default=True):
                    console.print("[yellow]Rolling back...[/]")
                    orch.record_failure(task, error="Human review rejected plan")
                    failed += 1
                    display.start()
                    display.update_task_status(task_id, TaskStatus.ROLLED_BACK)
                    continue
                display.start()

            # Phase 3: Implement
            if success:
                display.set_phase("IMPLEMENT")
                display.log("Phase 3/3: Implementing code changes...")
                display.log(f"  AI running: {cli_name} (timeout {timeout}s)")
                prompt = build_implement_prompt(workspace, task_dict, task_source)

                # Memory hint injection via orchestrator
                memory_hint = orch.get_memory_hint(task)
                if memory_hint:
                    prompt = f"{memory_hint}\n\n{prompt}"
                    display.log("Memory recall: applied hint from past solution")

                success, output = run_ai_task(
                    workspace, prompt, cli_name, timeout=timeout,
                    continue_session=True, on_output=_on_ai_output,
                    use_sdk=use_sdk,
                )
                if success:
                    display.log_success("Implementation complete")
                else:
                    display.log_error("Implementation failed")

            if success:
                display.log_success(f"Task {task_id} implemented")

                # Verify
                verification_passed = True
                tests_passed = None
                lint_passed = None
                type_check_passed = None

                if verify:
                    display.set_phase("VERIFY")
                    display.set_status(LoopStatus.VERIFYING)
                    display.log("Running verification (tests + lint + types)...")
                    vresult = orch.run_verification()
                    tests_passed = vresult.tests_passed
                    lint_passed = vresult.lint_passed
                    type_check_passed = vresult.type_check_passed

                    verification_passed = orch.check_verification(vresult)

                    if verification_passed:
                        parts = vresult.summary_parts()
                        display.log_success(f"Verification: {', '.join(parts) or 'ok'}")

                    if not verification_passed:
                        display.log_warning(f"Verification failed for {task_id}")

                        if interactive:
                            display.stop()
                            from rich.prompt import Confirm
                            if not Confirm.ask("Continue anyway?", default=False):
                                console.print("[yellow]Rolling back...[/]")
                                orch.record_failure(task, error="Verification failed")
                                failed += 1
                                display.start()
                                display.update_task_status(task_id, TaskStatus.ROLLED_BACK)
                                continue
                            display.start()
                        else:
                            display.log("Rolling back changes...")
                            orch.record_failure(task, error="Verification failed")
                            failed += 1
                            display.update_task_status(task_id, TaskStatus.ROLLED_BACK)
                            continue

                completed += 1

                # Record success via orchestrator (state + PRD + provenance)
                modified_files = get_modified_files(workspace)
                success_result = orch.record_success(
                    task, task_source=task_source,
                    tests_passed=tests_passed,
                    lint_passed=lint_passed,
                    type_check_passed=type_check_passed,
                    files_modified=modified_files,
                )
                display.update_task_status(task_id, TaskStatus.COMPLETE)
                display.set_status(LoopStatus.RUNNING)

                # Intentional Compaction (V1-020)
                from up.context import ContextManager
                ctx_mgr = ContextManager(workspace)
                if ctx_mgr.budget.usage_percent >= ctx_mgr.budget.warning_threshold * 100:
                    display.log("Context budget high. Generating progress handoff...")
                    progress_file = workspace / ".up/thoughts/progress.md"
                    progress_file.parent.mkdir(parents=True, exist_ok=True)
                    prompt = (
                        f"We just completed task {task_id}. The context budget is at {ctx_mgr.budget.usage_percent:.1f}%.\n"
                        "Please summarize our progress so far: what's done, what's next, and relevant files.\n"
                        "Write this summary to '.up/thoughts/progress.md' so a new session can resume."
                    )
                    run_ai_task(workspace, prompt, cli_name, timeout=timeout,
                                use_sdk=use_sdk)
                    display.log("Progress saved. Resetting context...")
                    ctx_mgr.reset()

                # Commit
                if auto_commit:
                    should_commit = True
                    if interactive:
                        display.stop()
                        console.print("\n[bold]Phase: COMMIT[/]")
                        console.print(get_diff_summary(workspace))
                        from rich.prompt import Confirm
                        should_commit = Confirm.ask("Commit changes?", default=True)
                        display.start()

                    if should_commit:
                        commit_msg = success_result.commit_message
                        commit_changes(workspace, commit_msg)
                        display.log_success(f"Committed: {commit_msg[:40]}...")
                else:
                    display.log("Changes staged (--auto-commit to commit)")
            else:
                display.log_error(f"Task {task_id} failed")
                failed += 1

                if output:
                    for line in output.strip().splitlines()[-3:]:
                        display.log_error(f"  {line[:100]}")
                    error_log = workspace / ".up" / "logs" / f"{task_id}-error.log"
                    error_log.parent.mkdir(parents=True, exist_ok=True)
                    error_log.write_text(output)
                    display.log(f"Full error log: .up/logs/{task_id}-error.log")
                else:
                    display.log_error("No output from AI CLI (timeout or crash)")

                display.log("Rolling back changes...")
                fail_result = orch.record_failure(
                    task,
                    error=output[:500] if output else "AI implementation failed",
                )
                display.update_task_status(task_id, TaskStatus.FAILED)

                if fail_result.doom_loop:
                    display.log_error(fail_result.message[:50])

                if fail_result.circuit_open:
                    cooldown = orch.state_manager.config.circuit_breaker_cooldown_minutes
                    display.log_error(f"Circuit breaker OPEN - cooldown {cooldown}m")
                    display.set_status(LoopStatus.FAILED)
                    break

    finally:
        display.set_status(LoopStatus.COMPLETE if failed == 0 else LoopStatus.FAILED)
        time.sleep(0.5)
        display.stop()
        _current_display = None
        _restore_terminal()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Summary
    console.print(f"\n{'─' * 50}")
    console.print(
        Panel.fit(
            f"[bold]Loop Complete[/]\n\n"
            f"Completed: [green]{completed}[/]\n"
            f"Failed: [red]{failed}[/]\n"
            f"Remaining: {len(tasks_to_run) - completed - failed}",
            border_style="cyan",
        )
    )

    if completed > 0:
        if auto_commit:
            console.print("\n[green]✓[/] All changes committed automatically")
        else:
            console.print("\n[bold]Next Steps:[/]")
            console.print("  1. Review changes: [cyan]up diff[/] or [cyan]git diff[/]")
            console.print("  2. Run tests: [cyan]pytest[/]")
            console.print("  3. Commit if satisfied: [cyan]git commit -am 'Implement tasks'[/]")
            console.print("\n  [dim]Tip: Use --auto-commit to commit automatically[/]")

    if failed > 0:
        console.print("\n[bold]Recovery Options:[/]")
        console.print("  • Reset to last checkpoint: [cyan]up reset[/]")
        console.print("  • View checkpoint history: [cyan]up status[/]")
