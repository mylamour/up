"""Product loop execution (AI and manual modes).

Contains the main AI product loop and manual/preview modes.
"""

import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from tqdm import tqdm

from up.ai_cli import run_ai_task
from up.core.state import get_state_manager, StateManager
from up.core.provenance import get_provenance_manager, ProvenanceEntry
from up.ui import ProductLoopDisplay, TaskStatus
from up.ui.loop_display import LoopStatus

from up.commands.start.helpers import (
    save_loop_state,
    get_next_task_from_prd,
    create_checkpoint,
    rollback_checkpoint,
    mark_task_complete,
    build_implementation_prompt,
)
from up.commands.start.verification import (
    run_verification_with_results,
    get_modified_files,
    get_diff_summary,
    commit_changes,
)

console = Console()

# Global state for interrupt handling
_state_manager: StateManager = None
_checkpoint_manager = None
_current_workspace = None
_current_provenance_entry: ProvenanceEntry = None
_current_display: Optional[ProductLoopDisplay] = None


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

    console.print("\n\n[yellow]Interrupted! Saving state...[/]")

    if _state_manager and _current_workspace:
        _state_manager.update_loop(
            phase="INTERRUPTED",
            interrupted_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        console.print("[green]✓[/] State saved to .up/state.json")
        last_cp = _state_manager.state.loop.last_checkpoint
        console.print(f"[dim]Checkpoint: {last_cp or 'none'}[/]")

        # Mark any in-progress provenance entry as rejected
        if _current_provenance_entry and _current_workspace:
            try:
                prov_mgr = get_provenance_manager(_current_workspace)
                prov_mgr.reject_operation(
                    _current_provenance_entry.id,
                    reason="User interrupted operation",
                )
                console.print("[dim]Provenance entry marked as interrupted[/]")
            except Exception:
                pass

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
):
    """Run the product loop with AI auto-implementation."""
    global _state_manager, _checkpoint_manager, _current_workspace
    global _current_provenance_entry, _current_display

    from up.core.checkpoint import get_checkpoint_manager

    _current_workspace = workspace
    _state_manager = get_state_manager(workspace)
    _checkpoint_manager = get_checkpoint_manager(workspace)
    provenance_manager = get_provenance_manager(workspace)
    signal.signal(signal.SIGINT, handle_interrupt)

    # Get all tasks
    all_tasks = []
    tasks_to_run = []

    if specific_task:
        tasks_to_run = [{"id": specific_task, "title": specific_task, "description": specific_task}]
        all_tasks = tasks_to_run
    elif task_source and task_source.endswith(".json"):
        prd_path = workspace / task_source
        if prd_path.exists():
            try:
                data = json.loads(prd_path.read_text())
                stories = data.get("userStories", [])
                all_tasks = stories
                for story in stories:
                    if not story.get("passes", False):
                        tasks_to_run.append(story)
                        if not run_all:
                            break
            except json.JSONDecodeError:
                pass

    if not tasks_to_run:
        console.print("\n[green]✓[/] All tasks completed!")
        return

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
            task_id = task.get("id", "unknown")
            task_title = task.get("title", "No title")

            display.set_current_task(task_id, "CHECKPOINT")
            display.increment_iteration()
            display.log(f"Starting task {task_id}: {task_title[:40]}...")

            state["iteration"] = state.get("iteration", 0) + 1
            state["phase"] = "EXECUTE"
            state["current_task"] = task_id
            save_loop_state(workspace, state)

            # Checkpoint
            display.log("Creating checkpoint...")
            checkpoint_name = f"cp-{task_id}-{state['iteration']}"
            create_checkpoint(workspace, checkpoint_name, task_id=task_id)

            # Build prompt
            prompt = build_implementation_prompt(workspace, task, task_source)

            # Start provenance tracking
            try:
                _current_provenance_entry = provenance_manager.start_operation(
                    task_id=task_id,
                    task_title=task_title,
                    prompt=prompt,
                    ai_model=cli_name,
                    context_files=[task_source] if task_source else [],
                )
                display.log(f"Provenance: {_current_provenance_entry.id[:8]}...")
            except Exception:
                _current_provenance_entry = None

            # Run AI
            display.set_phase("EXECUTE")
            display.log(f"Running {cli_name}...")
            success, output = run_ai_task(workspace, prompt, cli_name, timeout=timeout)

            if success:
                display.log_success(f"Task {task_id} implemented")

                # Verify
                verification_passed = True
                tests_passed = None
                lint_passed = None

                if verify:
                    display.set_phase("VERIFY")
                    display.set_status(LoopStatus.VERIFYING)
                    display.log("Running verification...")
                    tests_passed, lint_passed = run_verification_with_results(workspace)
                    verification_passed = tests_passed is not False

                    if not verification_passed:
                        display.log_warning(f"Verification failed for {task_id}")
                        if _current_provenance_entry:
                            try:
                                provenance_manager.reject_operation(
                                    _current_provenance_entry.id, reason="Verification failed"
                                )
                            except Exception:
                                pass
                            _current_provenance_entry = None

                        if interactive:
                            display.stop()
                            if not click.confirm("Continue anyway?"):
                                console.print("[yellow]Rolling back...[/]")
                                rollback_checkpoint(workspace)
                                failed += 1
                                _state_manager.record_task_failed(task_id)
                                display.start()
                                display.update_task_status(task_id, TaskStatus.ROLLED_BACK)
                                continue
                            display.start()
                        else:
                            display.log("Rolling back changes...")
                            rollback_checkpoint(workspace)
                            failed += 1
                            _state_manager.record_task_failed(task_id)
                            display.update_task_status(task_id, TaskStatus.ROLLED_BACK)
                            continue

                completed += 1

                # Complete provenance
                if _current_provenance_entry:
                    try:
                        modified_files = get_modified_files(workspace)
                        provenance_manager.complete_operation(
                            entry_id=_current_provenance_entry.id,
                            files_modified=modified_files,
                            tests_passed=tests_passed,
                            lint_passed=lint_passed,
                            status="accepted",
                        )
                    except Exception:
                        pass
                    _current_provenance_entry = None

                mark_task_complete(workspace, task_source, task_id)
                _state_manager.record_task_complete(task_id)
                display.update_task_status(task_id, TaskStatus.COMPLETE)
                display.set_status(LoopStatus.RUNNING)

                state["tasks_completed"] = state.get("tasks_completed", []) + [task_id]
                state["phase"] = "COMMIT"

                # Commit
                if auto_commit:
                    should_commit = True
                    if interactive:
                        display.stop()
                        console.print("\n[bold]Phase: COMMIT[/]")
                        console.print(get_diff_summary(workspace))
                        should_commit = click.confirm("Commit changes?")
                        display.start()

                    if should_commit:
                        commit_msg = f"feat({task_id}): {task_title}"
                        commit_changes(workspace, commit_msg)
                        display.log_success(f"Committed: {commit_msg[:40]}...")
                else:
                    display.log("Changes staged (--auto-commit to commit)")
            else:
                display.log_error(f"Task {task_id} failed")
                failed += 1

                if _current_provenance_entry:
                    try:
                        provenance_manager.reject_operation(
                            _current_provenance_entry.id,
                            reason=output[:500] if output else "AI implementation failed",
                        )
                    except Exception:
                        pass
                    _current_provenance_entry = None

                display.log("Rolling back changes...")
                rollback_checkpoint(workspace)
                display.update_task_status(task_id, TaskStatus.FAILED)

                _state_manager.record_task_failed(task_id)

                is_doom, doom_msg = _state_manager.check_doom_loop()
                if is_doom:
                    display.log_error(doom_msg[:50])

                cb = _state_manager.get_circuit_breaker("task")
                cb.record_failure()
                _state_manager.save()

                if not cb.can_execute():
                    cooldown = _state_manager.config.circuit_breaker_cooldown_minutes
                    display.log_error(f"Circuit breaker OPEN - cooldown {cooldown}m")
                    display.set_status(LoopStatus.FAILED)
                    break

                state["circuit_breaker"] = {"failures": cb.failures, "state": cb.state}

            save_loop_state(workspace, state)

    finally:
        display.set_status(LoopStatus.COMPLETE if failed == 0 else LoopStatus.FAILED)
        time.sleep(0.5)
        display.stop()
        _current_display = None

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
