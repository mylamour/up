"""Learning system CLI commands.

This module provides the main CLI entry points for the learning system.
The implementation is split across several submodules:
- utils: Shared utilities
- analyzer: Project analysis
- research: Topic and file learning
- plan: PRD generation
"""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from up.learn.utils import check_vision_map_exists, is_valid_path, find_skill_dir, display_profile, save_profile
from up.learn.analyzer import analyze_project, learn_self_improvement
from up.learn.research import learn_from_topic, learn_from_file, learn_from_project
from up.learn.plan import learn_analyze, learn_plan, learn_status

console = Console()


@click.group(invoke_without_command=True)
@click.argument("topic_or_path", required=False)
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
@click.option("--no-ai", is_flag=True, help="Disable AI analysis")
@click.pass_context
def learn_cmd(ctx, topic_or_path: str, workspace: str, no_ai: bool):
    """Learning system - analyze, research, and improve.
    
    \b
    Usage:
      up learn                    Auto-analyze and improve
      up learn "topic"            Learn about a specific topic
      up learn "file.md"          Analyze file with AI
      up learn "project/path"     Compare and learn from another project
    
    \b
    Subcommands:
      up learn auto               Analyze project (no vision check)
      up learn analyze            Analyze all research files
      up learn plan               Generate improvement PRD
      up learn status             Show learning system status
    """
    if ctx.invoked_subcommand is not None:
        return
    
    ctx.ensure_object(dict)
    ctx.obj['workspace'] = workspace
    ctx.obj['no_ai'] = no_ai
    
    # Check if topic_or_path is a subcommand
    subcommands = ["auto", "analyze", "plan", "status"]
    if topic_or_path in subcommands:
        subcmd = ctx.command.commands[topic_or_path]
        ctx.invoke(subcmd, workspace=workspace)
        return
    
    ws = Path(workspace) if workspace else Path.cwd()
    use_ai = not no_ai
    
    # No argument: self-improvement mode
    if not topic_or_path:
        vision_exists, vision_path = check_vision_map_exists(ws)
        
        if not vision_exists:
            console.print(Panel.fit(
                "[yellow]Vision Map Not Configured[/]",
                border_style="yellow"
            ))
            console.print("\nThe learning system requires a configured vision map.")
            console.print(f"\nPlease configure: [cyan]{vision_path}[/]")
            console.print("\n[bold]Alternatives:[/]")
            console.print("  • [cyan]up learn auto[/] - Analyze without vision map")
            console.print("  • [cyan]up learn \"topic\"[/] - Learn about specific topic")
            return
        
        learn_self_improvement(ws, use_ai=use_ai)
        return
    
    # Has argument: determine if topic or path
    if is_valid_path(topic_or_path):
        learn_from_project(ws, topic_or_path, use_ai=use_ai)
    else:
        learn_from_topic(ws, topic_or_path, use_ai=use_ai)


@learn_cmd.command("auto")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
def auto_cmd(workspace: str):
    """Auto-analyze project and identify improvements."""
    ws = Path(workspace) if workspace else Path.cwd()
    
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Auto Analysis",
        border_style="blue"
    ))
    
    profile = analyze_project(ws)
    
    if profile is None:
        console.print("[red]Error: Could not analyze project[/]")
        return
    
    display_profile(profile)
    
    save_path = save_profile(ws, profile)
    console.print(f"\n[green]✓[/] Profile saved to: [cyan]{save_path}[/]")
    
    console.print("\n[bold]Next Steps:[/]")
    if profile.get("research_topics"):
        console.print("  1. Research topics with: [cyan]up learn \"topic\"[/]")
    console.print("  2. Generate PRD with: [cyan]up learn plan[/]")
    console.print("  3. Start development with: [cyan]up start[/]")


@learn_cmd.command("analyze")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
def analyze_cmd(workspace: str):
    """Analyze all research files with AI."""
    ws = Path(workspace) if workspace else Path.cwd()
    learn_analyze(ws)


@learn_cmd.command("plan")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def plan_cmd(workspace: str, output: str):
    """Generate improvement PRD from analysis."""
    ws = Path(workspace) if workspace else Path.cwd()
    learn_plan(ws, output)


@learn_cmd.command("status")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
def status_cmd(workspace: str):
    """Show learning system status."""
    ws = Path(workspace) if workspace else Path.cwd()
    learn_status(ws)


# Export for external use
__all__ = [
    "learn_cmd",
    "analyze_project",
    "learn_self_improvement",
    "learn_from_topic",
    "learn_from_file",
    "learn_from_project",
    "learn_analyze",
    "learn_plan",
    "learn_status",
]
