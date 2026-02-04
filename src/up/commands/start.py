"""up start - Start the product loop."""

import json
import subprocess
import shutil
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tqdm import tqdm

console = Console()


def check_ai_cli() -> tuple[str, bool]:
    """Check which AI CLI is available."""
    if shutil.which("claude"):
        return "claude", True
    if shutil.which("agent"):
        return "agent", True
    return "", False


@click.command()
@click.option("--resume", "-r", is_flag=True, help="Resume from last checkpoint")
@click.option("--dry-run", is_flag=True, help="Preview without executing")
@click.option("--task", "-t", help="Start with specific task ID")
@click.option("--prd", "-p", type=click.Path(exists=True), help="Path to PRD file")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with confirmations")
@click.option("--no-ai", is_flag=True, help="Disable auto AI implementation")
@click.option("--all", "run_all", is_flag=True, help="Run all tasks automatically")
def start_cmd(resume: bool, dry_run: bool, task: str, prd: str, interactive: bool, no_ai: bool, run_all: bool):
    """Start the product loop for autonomous development.
    
    Uses Claude/Cursor AI by default to implement tasks automatically.
    
    The product loop implements SESRC principles:
    - Stable: Graceful degradation
    - Efficient: Token budgets
    - Safe: Input validation
    - Reliable: Checkpoints & rollback
    - Cost-effective: Early termination
    
    \b
    Examples:
      up start                  # Auto-implement next task with AI
      up start --all            # Auto-implement ALL tasks
      up start --resume         # Resume from checkpoint
      up start --task US-003    # Implement specific task
      up start --dry-run        # Preview mode
      up start --no-ai          # Manual mode (show instructions only)
    """
    cwd = Path.cwd()
    
    # Check if initialized with progress
    console.print()
    with tqdm(total=4, desc="Initializing", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        
        # Step 1: Check initialization
        pbar.set_description("Checking project")
        if not _is_initialized(cwd):
            pbar.close()
            console.print("\n[red]Error:[/] Project not initialized.")
            console.print("Run [cyan]up init[/] first.")
            raise SystemExit(1)
        pbar.update(1)
        time.sleep(0.2)
        
        # Step 2: Find task source
        pbar.set_description("Finding tasks")
        task_source = _find_task_source(cwd, prd)
        pbar.update(1)
        time.sleep(0.2)
        
        # Step 3: Load state
        pbar.set_description("Loading state")
        state = _load_loop_state(cwd)
        pbar.update(1)
        time.sleep(0.2)
        
        # Step 4: Check circuit breaker
        pbar.set_description("Checking circuits")
        cb_status = _check_circuit_breaker(state)
        pbar.update(1)
        time.sleep(0.1)
    
    console.print()
    console.print(Panel.fit(
        "[bold blue]Product Loop[/] - SESRC Autonomous Development",
        border_style="blue"
    ))
    
    # Display status table
    _display_status_table(state, task_source, cwd, resume)
    
    # Check for task sources
    if not task_source and not resume:
        console.print("\n[yellow]Warning:[/] No task source found.")
        console.print("\nCreate one of:")
        console.print("  • [cyan]prd.json[/] - Structured user stories")
        console.print("  • [cyan]TODO.md[/] - Task list")
        console.print("\nOr run [cyan]up learn plan[/] to generate a PRD.")
        raise SystemExit(1)
    
    # Check circuit breaker
    if cb_status.get("open"):
        console.print(f"\n[red]Circuit breaker OPEN:[/] {cb_status.get('reason')}")
        console.print("Run [cyan]up start --resume[/] after fixing the issue.")
        raise SystemExit(1)
    
    # Dry run mode
    if dry_run:
        console.print("\n[yellow]DRY RUN MODE[/] - No changes will be made")
        _preview_loop(cwd, state, task_source, task)
        return
    
    # Interactive confirmation
    if interactive:
        if not click.confirm("\nStart the product loop?"):
            console.print("[dim]Cancelled[/]")
            return
    
    # Check AI availability
    use_ai = not no_ai
    cli_name, cli_available = check_ai_cli()
    
    if use_ai and not cli_available:
        console.print("\n[yellow]No AI CLI found. Running in manual mode.[/]")
        console.print("Install Claude CLI or Cursor Agent for auto-implementation.")
        use_ai = False
    
    # Start the loop with progress
    console.print("\n[bold green]Starting product loop...[/]")
    
    if use_ai:
        _run_ai_product_loop(cwd, state, task_source, task, cli_name, run_all)
    else:
        _run_product_loop_with_progress(cwd, state, task_source, task, resume)


def _display_status_table(state: dict, task_source: str, workspace: Path, resume: bool):
    """Display status table."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value")
    
    # Iteration
    iteration = state.get("iteration", 0)
    table.add_row("Iteration", f"[cyan]{iteration}[/]")
    
    # Phase
    phase = state.get("phase", "INIT")
    table.add_row("Phase", f"[cyan]{phase}[/]")
    
    # Task source
    if task_source:
        task_count = _count_tasks(workspace, task_source)
        table.add_row("Tasks", f"[cyan]{task_count}[/] remaining from {task_source}")
    else:
        table.add_row("Tasks", "[dim]No task source[/]")
    
    # Completed
    completed = len(state.get("tasks_completed", []))
    table.add_row("Completed", f"[green]{completed}[/]")
    
    # Success rate
    success_rate = state.get("metrics", {}).get("success_rate", 1.0)
    table.add_row("Success Rate", f"[green]{success_rate*100:.0f}%[/]")
    
    # Mode
    mode = "Resume" if resume else "Fresh Start"
    table.add_row("Mode", mode)
    
    console.print(table)


def _is_initialized(workspace: Path) -> bool:
    """Check if project is initialized with up systems."""
    return (
        (workspace / ".claude").exists() or 
        (workspace / ".cursor").exists() or
        (workspace / "CLAUDE.md").exists()
    )


def _find_task_source(workspace: Path, prd_path: str = None) -> str:
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


def _load_loop_state(workspace: Path) -> dict:
    """Load loop state from file."""
    state_file = workspace / ".loop_state.json"
    
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except json.JSONDecodeError:
            pass
    
    return {
        "version": "1.0",
        "iteration": 0,
        "phase": "INIT",
        "tasks_completed": [],
        "tasks_remaining": [],
        "circuit_breaker": {},
        "metrics": {"total_edits": 0, "total_rollbacks": 0, "success_rate": 1.0},
    }


def _save_loop_state(workspace: Path, state: dict) -> None:
    """Save loop state to file."""
    from datetime import datetime
    state["last_updated"] = datetime.now().isoformat()
    (workspace / ".loop_state.json").write_text(json.dumps(state, indent=2))


def _count_tasks(workspace: Path, task_source: str) -> int:
    """Count tasks in source file."""
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
        # Count unchecked items
        import re
        return len(re.findall(r"- \[ \]", content))
    
    return 0


def _check_circuit_breaker(state: dict) -> dict:
    """Check circuit breaker status."""
    cb = state.get("circuit_breaker", {})
    
    for name, circuit in cb.items():
        if isinstance(circuit, dict) and circuit.get("state") == "OPEN":
            return {
                "open": True,
                "circuit": name,
                "reason": f"{name} circuit opened after {circuit.get('failures', 0)} failures",
            }
    
    return {"open": False}


def _preview_loop(workspace: Path, state: dict, task_source: str, specific_task: str = None):
    """Preview what the loop would do."""
    console.print("\n[bold]Preview:[/]")
    
    # Show phases with progress simulation
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
    
    # Show next task
    if specific_task:
        console.print(f"\n  Target task: [cyan]{specific_task}[/]")
    elif task_source and task_source.endswith(".json"):
        next_task = _get_next_task_from_prd(workspace / task_source)
        if next_task:
            console.print(f"\n  Next task: [cyan]{next_task.get('id')}[/] - {next_task.get('title')}")


def _get_next_task_from_prd(prd_path: Path) -> dict:
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


def _run_product_loop_with_progress(
    workspace: Path, 
    state: dict, 
    task_source: str, 
    specific_task: str = None,
    resume: bool = False
):
    """Run the product loop with progress indicators."""
    from datetime import datetime
    
    # Update state
    if not resume:
        state["iteration"] = state.get("iteration", 0) + 1
        state["phase"] = "OBSERVE"
        state["started_at"] = datetime.now().isoformat()
    
    # Get task info
    next_task = None
    if specific_task:
        next_task = {"id": specific_task, "title": specific_task}
    elif task_source and task_source.endswith(".json"):
        next_task = _get_next_task_from_prd(workspace / task_source)
    
    # Show task info
    if next_task:
        console.print(f"\n[bold]Task:[/] [cyan]{next_task.get('id')}[/] - {next_task.get('title', 'N/A')}")
    
    # Simulate loop phases with progress
    phases = [
        ("OBSERVE", "Reading task requirements"),
        ("CHECKPOINT", "Creating checkpoint"),
        ("EXECUTE", "Ready for implementation"),
        ("VERIFY", "Verification pending"),
        ("COMMIT", "Awaiting completion"),
    ]
    
    console.print("\n[bold]Loop Progress:[/]")
    
    with tqdm(total=len(phases), desc="Initializing loop", 
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
        
        for i, (phase, desc) in enumerate(phases):
            state["phase"] = phase
            pbar.set_description(f"{phase}: {desc}")
            pbar.update(1)
            
            # Only run through OBSERVE and CHECKPOINT automatically
            if i >= 2:
                break
            
            time.sleep(0.5)
    
    # Save state
    _save_loop_state(workspace, state)
    
    # Generate instructions for AI
    console.print("\n" + "─" * 50)
    console.print("\n[bold green]✓[/] Loop initialized at [cyan]EXECUTE[/] phase")
    
    # Show instructions panel
    instructions = _generate_loop_instructions(workspace, state, task_source, specific_task)
    console.print(Panel(
        instructions,
        title="[bold]AI Instructions[/]",
        border_style="green"
    ))
    
    # Show next steps
    console.print("\n[bold]Next Steps:[/]")
    console.print("  1. Use [cyan]/product-loop[/] in your AI assistant")
    console.print("  2. Or implement the task manually")
    console.print("  3. Run [cyan]up status[/] to check progress")
    console.print("  4. Run [cyan]up dashboard[/] for live monitoring")


def _generate_loop_instructions(
    workspace: Path, 
    state: dict, 
    task_source: str,
    specific_task: str = None
) -> str:
    """Generate instructions for the AI to execute the loop."""
    
    task_info = ""
    if specific_task:
        task_info = f"Task: {specific_task}"
    elif task_source:
        next_task = None
        if task_source.endswith(".json"):
            next_task = _get_next_task_from_prd(workspace / task_source)
        
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
  ├─ Checkpoint: git stash push -m "cp-{state.get('iteration', 1)}"
  ├─ Verify: pytest && mypy src/ && ruff check src/
  ├─ Rollback: git stash pop
  └─ Complete: Update .loop_state.json

Circuit Breaker: 3 failures → OPEN
State File: .loop_state.json
"""


def _run_ai_product_loop(
    workspace: Path,
    state: dict,
    task_source: str,
    specific_task: str = None,
    cli_name: str = "claude",
    run_all: bool = False
):
    """Run the product loop with AI auto-implementation."""
    from datetime import datetime
    
    # Get all tasks
    tasks_to_run = []
    
    if specific_task:
        tasks_to_run = [{"id": specific_task, "title": specific_task, "description": specific_task}]
    elif task_source and task_source.endswith(".json"):
        prd_path = workspace / task_source
        if prd_path.exists():
            try:
                data = json.loads(prd_path.read_text())
                stories = data.get("userStories", [])
                # Get incomplete tasks
                for story in stories:
                    if not story.get("passes", False):
                        tasks_to_run.append(story)
                        if not run_all:
                            break  # Only first task if not --all
            except json.JSONDecodeError:
                pass
    
    if not tasks_to_run:
        console.print("\n[green]✓[/] All tasks completed!")
        return
    
    console.print(f"\n[bold]Tasks to implement:[/] {len(tasks_to_run)}")
    
    # Process each task
    completed = 0
    failed = 0
    
    for task in tqdm(tasks_to_run, desc="Implementing", unit="task"):
        task_id = task.get("id", "unknown")
        task_title = task.get("title", "No title")
        task_desc = task.get("description", task_title)
        
        console.print(f"\n{'─' * 50}")
        console.print(f"[bold cyan]Task {task_id}:[/] {task_title}")
        
        # Update state
        state["iteration"] = state.get("iteration", 0) + 1
        state["phase"] = "EXECUTE"
        state["current_task"] = task_id
        _save_loop_state(workspace, state)
        
        # Create checkpoint
        console.print("[dim]Creating checkpoint...[/]")
        checkpoint_name = f"cp-{task_id}-{state['iteration']}"
        _create_checkpoint(workspace, checkpoint_name)
        
        # Build prompt for AI
        prompt = _build_implementation_prompt(workspace, task, task_source)
        
        # Run AI
        console.print(f"[yellow]Running {cli_name}...[/]")
        success, output = _run_ai_implementation(workspace, prompt, cli_name)
        
        if success:
            console.print(f"[green]✓[/] Task {task_id} implemented")
            completed += 1
            
            # Mark task as complete in PRD
            _mark_task_complete(workspace, task_source, task_id)
            
            # Update state
            state["tasks_completed"] = state.get("tasks_completed", []) + [task_id]
            state["phase"] = "COMMIT"
        else:
            console.print(f"[red]✗[/] Task {task_id} failed")
            console.print(f"[dim]{output[:200]}...[/]" if len(output) > 200 else f"[dim]{output}[/]")
            failed += 1
            
            # Rollback
            console.print("[yellow]Rolling back...[/]")
            _rollback_checkpoint(workspace, checkpoint_name)
            
            # Update circuit breaker
            cb = state.get("circuit_breaker", {})
            cb["failures"] = cb.get("failures", 0) + 1
            if cb["failures"] >= 3:
                cb["state"] = "OPEN"
                console.print("[red]Circuit breaker OPEN - stopping loop[/]")
                state["circuit_breaker"] = cb
                _save_loop_state(workspace, state)
                break
            state["circuit_breaker"] = cb
        
        _save_loop_state(workspace, state)
    
    # Summary
    console.print(f"\n{'─' * 50}")
    console.print(Panel.fit(
        f"[bold]Loop Complete[/]\n\n"
        f"Completed: [green]{completed}[/]\n"
        f"Failed: [red]{failed}[/]\n"
        f"Remaining: {len(tasks_to_run) - completed - failed}",
        border_style="blue"
    ))
    
    if completed > 0:
        console.print("\n[bold]Next Steps:[/]")
        console.print("  1. Review changes: [cyan]git diff[/]")
        console.print("  2. Run tests: [cyan]pytest[/]")
        console.print("  3. Commit if satisfied: [cyan]git commit -am 'Implement tasks'[/]")


def _build_implementation_prompt(workspace: Path, task: dict, task_source: str) -> str:
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


def _run_ai_implementation(workspace: Path, prompt: str, cli_name: str) -> tuple[bool, str]:
    """Run AI CLI to implement the task."""
    try:
        if cli_name == "claude":
            cmd = ["claude", "-p", prompt]
        else:
            cmd = ["agent", "-p", prompt]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=workspace
        )
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr or "Unknown error"
    
    except subprocess.TimeoutExpired:
        return False, "AI implementation timed out (5 minutes)"
    except Exception as e:
        return False, str(e)


def _create_checkpoint(workspace: Path, name: str) -> bool:
    """Create a git stash checkpoint."""
    try:
        subprocess.run(
            ["git", "stash", "push", "-m", name],
            capture_output=True,
            cwd=workspace,
            timeout=30
        )
        return True
    except Exception:
        return False


def _rollback_checkpoint(workspace: Path, name: str) -> bool:
    """Rollback to checkpoint using git stash."""
    try:
        # First, reset any uncommitted changes
        subprocess.run(
            ["git", "checkout", "."],
            capture_output=True,
            cwd=workspace,
            timeout=30
        )
        return True
    except Exception:
        return False


def _mark_task_complete(workspace: Path, task_source: str, task_id: str) -> None:
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


if __name__ == "__main__":
    start_cmd()
