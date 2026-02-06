"""up start - CLI command entry point.

Routes to parallel, dry-run, AI, or manual mode based on options.
"""

import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from tqdm import tqdm

from up.ai_cli import check_ai_cli, get_ai_cli_install_instructions
from up.ui import THEME

from up.commands.start.helpers import (
    is_initialized,
    find_task_source,
    load_loop_state,
    check_circuit_breaker,
    display_status_table,
)
from up.commands.start.loop import (
    preview_loop,
    run_manual_loop,
    run_ai_product_loop,
)

console = Console(theme=THEME)


@click.command()
@click.option("--resume", "-r", is_flag=True, help="Resume from last checkpoint")
@click.option("--dry-run", is_flag=True, help="Preview without executing")
@click.option("--task", "-t", help="Start with specific task ID")
@click.option("--prd", "-p", type=click.Path(exists=True), help="Path to PRD file")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with confirmations")
@click.option("--no-ai", is_flag=True, help="Disable auto AI implementation")
@click.option("--all", "run_all", is_flag=True, help="Run all tasks automatically")
@click.option("--timeout", default=600, help="AI task timeout in seconds (default: 600)")
@click.option("--parallel", is_flag=True, help="Run tasks in parallel Git worktrees")
@click.option("--jobs", "-j", default=3, help="Number of parallel tasks (default: 3)")
@click.option("--auto-commit", is_flag=True, help="Auto-commit after each successful task")
@click.option("--verify/--no-verify", default=True, help="Run tests before commit (default: True)")
def start_cmd(
    resume, dry_run, task, prd, interactive, no_ai, run_all,
    timeout, parallel, jobs, auto_commit, verify,
):
    """Start the product loop for autonomous development.

    Uses Claude/Cursor AI by default to implement tasks automatically.

    The product loop implements SESRC principles:
    - Stable: Graceful degradation
    - Efficient: Token budgets
    - Safe: Input validation
    - Reliable: Checkpoints & rollback
    - Cost-effective: Early termination

    \\b
    Examples:
      up start                  # Auto-implement next task with AI
      up start --all            # Auto-implement ALL tasks
      up start --resume         # Resume from checkpoint
      up start --task US-003    # Implement specific task
      up start --dry-run        # Preview mode
      up start --no-ai          # Manual mode (show instructions only)
      up start --parallel       # Run 3 tasks in parallel worktrees
      up start --parallel -j 5  # Run 5 tasks in parallel
      up start --parallel --all # Run ALL tasks in parallel batches
    """
    cwd = Path.cwd()

    # Check if initialized with progress
    console.print()
    with tqdm(total=4, desc="Initializing", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        pbar.set_description("Checking project")
        if not is_initialized(cwd):
            pbar.close()
            console.print("\n[red]Error:[/] Project not initialized.")
            console.print("Run [cyan]up init[/] first.")
            raise SystemExit(1)
        pbar.update(1)
        time.sleep(0.2)

        pbar.set_description("Finding tasks")
        task_source = find_task_source(cwd, prd)
        pbar.update(1)
        time.sleep(0.2)

        pbar.set_description("Loading state")
        state = load_loop_state(cwd)
        pbar.update(1)
        time.sleep(0.2)

        pbar.set_description("Checking circuits")
        cb_status = check_circuit_breaker(state)
        pbar.update(1)
        time.sleep(0.1)

    console.print()
    console.print(Panel.fit(
        "[bold blue]Product Loop[/] - SESRC Autonomous Development",
        border_style="blue",
    ))

    display_status_table(state, task_source, cwd, resume)

    if not task_source and not resume:
        console.print("\n[yellow]Warning:[/] No task source found.")
        console.print("\nCreate one of:")
        console.print("  • [cyan]prd.json[/] - Structured user stories")
        console.print("  • [cyan]TODO.md[/] - Task list")
        console.print("\nOr run [cyan]up learn plan[/] to generate a PRD.")
        raise SystemExit(1)

    if cb_status.get("open"):
        console.print(f"\n[red]Circuit breaker OPEN:[/] {cb_status.get('reason')}")
        console.print("Run [cyan]up start --resume[/] after fixing the issue.")
        raise SystemExit(1)

    if interactive and not dry_run:
        if not click.confirm("\nStart the product loop?"):
            console.print("[dim]Cancelled[/]")
            return

    # Parallel mode
    if parallel:
        from up.parallel_scheduler import run_enhanced_parallel_loop
        from up.git.utils import is_git_repo

        if not is_git_repo(cwd):
            console.print("\n[red]Error:[/] Parallel mode requires a Git repository.")
            console.print("Run [cyan]git init[/] first.")
            raise SystemExit(1)

        prd_path = cwd / (prd or task_source or "prd.json")
        if not prd_path.exists():
            console.print(f"\n[red]Error:[/] PRD file not found: {prd_path}")
            console.print("Run [cyan]up learn plan[/] to generate one.")
            raise SystemExit(1)

        console.print(f"\n[bold cyan]PARALLEL MODE[/] - {jobs} workers")
        console.print(f"PRD: {prd_path}")

        run_enhanced_parallel_loop(
            workspace=cwd,
            prd_path=prd_path,
            max_workers=jobs,
            run_all=run_all,
            timeout=timeout,
            dry_run=dry_run,
        )
        return

    # Dry run mode
    if dry_run:
        console.print("\n[yellow]DRY RUN MODE[/] - No changes will be made")
        preview_loop(cwd, state, task_source, task)
        return

    # Check AI availability
    use_ai = not no_ai
    cli_name, cli_available = check_ai_cli()

    if use_ai and not cli_available:
        console.print("\n[yellow]No AI CLI found. Running in manual mode.[/]")
        console.print(get_ai_cli_install_instructions())
        use_ai = False

    console.print("\n[bold green]Starting product loop...[/]")

    if use_ai:
        run_ai_product_loop(
            cwd, state, task_source, task, cli_name,
            run_all, timeout, auto_commit, verify, interactive,
        )
    else:
        run_manual_loop(cwd, state, task_source, task, resume)
