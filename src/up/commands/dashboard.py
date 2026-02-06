"""up dashboard - Interactive health dashboard."""

import time
from pathlib import Path

import click
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from up.core.state import get_state_manager

console = Console()


@click.command()
@click.option("--refresh", "-r", default=5, help="Refresh interval in seconds")
@click.option("--once", is_flag=True, help="Show once without refresh")
def dashboard_cmd(refresh: int, once: bool):
    """Show interactive health dashboard.
    
    Displays real-time status of all up systems:
    - Context budget usage
    - Circuit breaker states  
    - Product loop progress
    - Recent activity
    """
    if once:
        dashboard = create_dashboard(Path.cwd())
        console.print(dashboard)
        return
    
    try:
        with Live(create_dashboard(Path.cwd()), refresh_per_second=1, console=console) as live:
            while True:
                time.sleep(refresh)
                live.update(create_dashboard(Path.cwd()))
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped[/]")


def create_dashboard(workspace: Path) -> Panel:
    """Create the dashboard layout."""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    
    # Header
    layout["header"].update(Panel(
        Text("UP-CLI Health Dashboard", style="bold white", justify="center"),
        style="blue"
    ))
    
    # Left side - Status panels
    left_content = Layout()
    left_content.split_column(
        Layout(create_context_panel(workspace), name="context"),
        Layout(create_circuit_panel(workspace), name="circuit"),
    )
    layout["left"].update(left_content)
    
    # Right side - Progress and activity
    right_content = Layout()
    right_content.split_column(
        Layout(create_progress_panel(workspace), name="progress"),
        Layout(create_skills_panel(workspace), name="skills"),
    )
    layout["right"].update(right_content)
    
    # Footer
    layout["footer"].update(Panel(
        Text("Press Ctrl+C to exit | Refreshing every 5s", style="dim", justify="center"),
        style="dim"
    ))
    
    return Panel(layout, title="[bold]up-cli[/]", border_style="blue")


def create_context_panel(workspace: Path) -> Panel:
    """Create context budget panel using StateManager API."""
    try:
        sm = get_state_manager(workspace)
        ctx = sm.state.context
        
        usage = ctx.usage_percent
        status = ctx.status
        remaining = ctx.remaining_tokens
        
        # Create progress bar
        bar_width = 20
        filled = int(bar_width * usage / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Color based on status
        if status == "CRITICAL":
            color = "red"
        elif status == "WARNING":
            color = "yellow"
        else:
            color = "green"
        
        content = f"""[{color}]{status}[/]

[{bar}] {usage:.1f}%

Remaining: {remaining:,} tokens
Entries: {len(ctx.entries)}"""
        
        return Panel(content, title="Context Budget", border_style=color)
        
    except Exception:
        return Panel("[dim]Not configured[/]", title="Context Budget", border_style="dim")


def create_circuit_panel(workspace: Path) -> Panel:
    """Create circuit breaker panel using StateManager API."""
    try:
        sm = get_state_manager(workspace)
        breakers = sm.state.circuit_breakers
        
        if not breakers:
            return Panel("[dim]No circuits[/]", title="Circuit Breaker", border_style="dim")
        
        lines = []
        for name, cb in breakers.items():
            cb_state = cb.state
            failures = cb.failures
            
            if cb_state == "OPEN":
                icon = "🔴"
                color = "red"
            elif cb_state == "HALF_OPEN":
                icon = "🟡"
                color = "yellow"
            else:
                icon = "🟢"
                color = "green"
            
            lines.append(f"{icon} [{color}]{name}[/]: {cb_state} ({failures} failures)")
        
        content = "\n".join(lines)
        return Panel(content, title="Circuit Breaker", border_style="green")
        
    except Exception:
        return Panel("[dim]Not active[/]", title="Circuit Breaker", border_style="dim")


def create_progress_panel(workspace: Path) -> Panel:
    """Create progress panel using StateManager API."""
    try:
        sm = get_state_manager(workspace)
        loop = sm.state.loop
        metrics = sm.state.metrics
        
        iteration = loop.iteration
        phase = loop.phase
        current = loop.current_task
        completed = len(loop.tasks_completed)
        total = metrics.total_tasks or (completed + len(loop.tasks_failed))
        success_rate = metrics.success_rate
        
        # Progress bar
        if total > 0:
            progress = completed / total
            bar_width = 20
            filled = int(bar_width * progress)
            bar = "█" * filled + "░" * (bar_width - filled)
            progress_line = f"[{bar}] {progress*100:.0f}%"
        else:
            progress_line = "[dim]No tasks[/]"
        
        content = f"""Iteration: {iteration}
Phase: [cyan]{phase}[/]
Current: {current or '[dim]None[/]'}

{progress_line}
Completed: {completed}/{total}
Success: {success_rate*100:.0f}%"""
        
        return Panel(content, title="Product Loop", border_style="cyan")
        
    except Exception:
        return Panel("[dim]No active loop[/]", title="Product Loop", border_style="dim")


def create_skills_panel(workspace: Path) -> Panel:
    """Create skills panel."""
    skills = []
    
    skills_dirs = [
        workspace / ".claude/skills",
        workspace / ".cursor/skills",
    ]
    
    for skills_dir in skills_dirs:
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    skills.append(skill_dir.name)
    
    if not skills:
        return Panel(
            "[dim]No skills installed[/]",
            title="Skills",
            border_style="dim"
        )
    
    content = "\n".join(f"• {skill}" for skill in sorted(set(skills)))
    return Panel(content, title="Skills", border_style="magenta")


if __name__ == "__main__":
    dashboard_cmd()
