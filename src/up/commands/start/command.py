"""up start - CLI command entry point.

Routes to parallel, dry-run, AI, or manual mode based on options.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from up.ai_cli import check_ai_cli, get_ai_cli_install_instructions
from up.ui import THEME

from up.commands.start.helpers import (
    is_initialized,
    find_task_source,
    load_loop_state,
    check_circuit_breaker,
    reset_circuit_breaker,
    display_status_table,
)
from up.commands.start.loop import (
    preview_loop,
    run_manual_loop,
    run_ai_product_loop,
)

console = Console(theme=THEME)


@click.command()
@click.option("--resume", "-r", is_flag=True, help="Resume from last checkpoint (resets circuit breaker)")
@click.option("--dry-run", is_flag=True, help="Preview without executing")
@click.option("--task", "-t", help="Start with specific task ID")
@click.option("--prd", "-p", type=click.Path(exists=True), help="Path to PRD file")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode: confirm plan before implementation")
@click.option("--no-ai", is_flag=True, help="Disable auto AI implementation")
@click.option("--all", "run_all", is_flag=True, help="Run all tasks automatically")
@click.option("--timeout", default=600, help="AI task timeout in seconds (default: 600)")
@click.option("--parallel", is_flag=True, help="Run tasks in parallel Git worktrees")
@click.option("--jobs", "-j", default=3, help="Number of parallel tasks (default: 3)")
@click.option("--auto-commit", is_flag=True, help="Auto-commit after each successful task")
@click.option("--verify/--no-verify", default=True, help="Run tests before commit (default: True)")
@click.option("--sdk", is_flag=True, help="Use Agent SDK engine (persistent sessions, compaction)")
def start_cmd(
    resume, dry_run, task, prd, interactive, no_ai, run_all,
    timeout, parallel, jobs, auto_commit, verify, sdk,
):
    """Start the product loop for autonomous development.

    By default runs autonomously with no prompts. Use -i for interactive
    mode which adds a human review gate before implementation.

    \b
    Examples:
      up start                  # Auto-implement next task
      up start -i               # Interactive: review plan before implementing
      up start --all            # Auto-implement ALL tasks
      up start --resume         # Resume after failure (resets circuit breaker)
      up start --task US-003    # Implement specific task
      up start --dry-run        # Preview mode
      up start --no-ai          # Manual mode (show instructions only)
      up start --parallel -j 5  # Run 5 tasks in parallel worktrees
    """
    cwd = Path.cwd()

    # Initialization
    if not is_initialized(cwd):
        console.print("[red]Error:[/] Project not initialized. Run [cyan]up init[/] first.")
        raise SystemExit(1)

    task_source = find_task_source(cwd, prd)
    state = load_loop_state(cwd)

    # Resume resets circuit breaker so you can retry after fixing issues
    if resume:
        reset_circuit_breaker(cwd)

    cb_status = check_circuit_breaker(state, workspace=cwd)

    console.print()
    console.print(Panel.fit(
        "[bold blue]Product Loop[/] - SESRC Autonomous Development",
        border_style="blue",
    ))

    display_status_table(state, task_source, cwd, resume)

    if not task_source and not resume:
        console.print("\n[yellow]Warning:[/] No task source found.")
        console.print("  Create [cyan]prd.json[/] or run [cyan]up learn plan[/] to generate one.")
        raise SystemExit(1)

    if cb_status.get("open"):
        console.print(f"\n[red]Circuit breaker OPEN:[/] {cb_status.get('reason')}")
        console.print("Run [cyan]up start --resume[/] to reset and retry.")
        raise SystemExit(1)

    # Parallel mode
    if parallel:
        from up.parallel import run_enhanced_parallel_loop
        from up.git.utils import is_git_repo

        if not is_git_repo(cwd):
            console.print("\n[red]Error:[/] Parallel mode requires a Git repository.")
            raise SystemExit(1)

        prd_path = cwd / (prd or task_source or "prd.json")
        if not prd_path.exists():
            console.print(f"\n[red]Error:[/] PRD file not found: {prd_path}")
            raise SystemExit(1)

        console.print(f"\n[bold cyan]PARALLEL MODE[/] - {jobs} workers")

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

    if sdk:
        from up.ai_cli import check_sdk_available
        if check_sdk_available():
            cli_name = "claude-sdk"
            cli_available = True
        else:
            console.print("\n[yellow]Agent SDK not installed. Falling back to CLI mode.[/]")
            console.print("  Install with: pip install up-cli[sdk]")
            sdk = False
            cli_name, cli_available = check_ai_cli()
    else:
        cli_name, cli_available = check_ai_cli()

    if use_ai and not cli_available:
        console.print("\n[yellow]No AI engine found. Running in manual mode.[/]")
        console.print(get_ai_cli_install_instructions())
        use_ai = False

    if use_ai:
        run_ai_product_loop(
            cwd, state, task_source, task, cli_name,
            run_all, timeout, auto_commit, verify, interactive,
            use_sdk=sdk,
        )
    else:
        run_manual_loop(cwd, state, task_source, task, resume)
