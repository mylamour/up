"""Learning system CLI commands (v1.0 simplified routing).

up learn              → Auto-analyze project + generate PRD
up learn "topic"      → Research specific topic
up learn --status     → Show learning system status
"""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from up.learn.analyzer import analyze_project
from up.learn.plan import learn_analyze, learn_plan, learn_status
from up.learn.research import learn_from_file, learn_from_project, learn_from_topic
from up.learn.utils import display_profile, is_valid_path, save_profile

console = Console()


@click.command()
@click.argument("topic_or_path", required=False)
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
@click.option("--no-ai", is_flag=True, help="Disable AI analysis")
@click.option("--status", "show_status", is_flag=True, help="Show learning system status")
@click.option("--auto-start", is_flag=True, help="Auto-start product loop after PRD generation")
def learn_cmd(topic_or_path: str, workspace: str, no_ai: bool, show_status: bool, auto_start: bool):
    """Analyze project, research topics, and generate improvement PRD.

    \b
    Usage:
      up learn                    Auto-analyze + generate PRD
      up learn "topic"            Research a specific topic
      up learn path/to/file       Analyze a file or project
      up learn --status           Show learning system status
    """
    ws = Path(workspace) if workspace else Path.cwd()
    use_ai = not no_ai

    if show_status:
        learn_status(ws)
        return

    # Topic or path provided: research mode
    if topic_or_path:
        if is_valid_path(topic_or_path):
            p = Path(topic_or_path)
            if p.is_file():
                learn_from_file(ws, topic_or_path, use_ai=use_ai)
            else:
                learn_from_project(ws, topic_or_path, use_ai=use_ai)
        else:
            learn_from_topic(ws, topic_or_path, use_ai=use_ai)
        return

    # No argument: full pipeline (analyze → plan)
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Full Pipeline",
        border_style="blue"
    ))

    # Step 1: Analyze project
    console.print("\n[bold]Step 1:[/] Analyzing project...")
    profile = analyze_project(ws)
    if profile:
        display_profile(profile)
        save_profile(ws, profile)

    # Step 2: Analyze research files
    console.print("\n[bold]Step 2:[/] Analyzing research files...")
    learn_analyze(ws, use_ai=use_ai)

    # Step 3: Generate PRD
    console.print("\n[bold]Step 3:[/] Generating PRD...")
    learn_plan(ws, output=None, use_ai=use_ai)

    console.print("\n[green]✓[/] Pipeline complete.")

    # US-007: Pipeline orchestration — learn -> product-loop
    prd_path = ws / "prd.json"
    if prd_path.exists():
        from up.events import EventBridge, EventType
        try:
            bridge = EventBridge(ws)
            bridge.emit_simple(EventType.LEARNING_COMPLETE, source="learn")
        except Exception:
            pass

        if auto_start:
            console.print("\n[bold]Auto-starting product loop...[/]")
            _start_product_loop(ws)
        else:
            from rich.prompt import Confirm
            if Confirm.ask("\nPRD ready. Start product loop?", default=False):
                _start_product_loop(ws)
            else:
                console.print("[dim]Run [cyan]up start[/] to begin development.[/dim]")
    else:
        console.print("[dim]No prd.json generated. Run [cyan]up start[/] manually.[/dim]")


def _start_product_loop(workspace: Path) -> None:
    """Hand off to the product loop."""
    import subprocess
    import sys

    try:
        subprocess.run(
            [sys.executable, "-m", "up", "start", "--prd", str(workspace / "prd.json")],
            cwd=workspace,
        )
    except Exception as e:
        console.print(f"[red]Failed to start product loop:[/red] {e}")
        console.print("[dim]Run [cyan]up start[/] manually.[/dim]")


# Export for external use
__all__ = [
    "learn_cmd",
    "analyze_project",
    "learn_from_topic",
    "learn_from_file",
    "learn_from_project",
    "learn_analyze",
    "learn_plan",
    "learn_status",
]
