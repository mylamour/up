"""up dashboard - Interactive health dashboard."""

import json
import time
from pathlib import Path

import click
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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
    """Create context budget panel."""
    context_file = workspace / ".claude/context_budget.json"
    
    if not context_file.exists():
        return Panel(
            "[dim]Not configured[/]",
            title="Context Budget",
            border_style="dim"
        )
    
    try:
        data = json.loads(context_file.read_text())
        usage = data.get("usage_percent", 0)
        status = data.get("status", "OK")
        remaining = data.get("remaining_tokens", 0)
        
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
Entries: {data.get('entry_count', 0)}"""
        
        return Panel(content, title="Context Budget", border_style=color)
        
    except (json.JSONDecodeError, KeyError):
        return Panel("[red]Error reading state[/]", title="Context Budget")


def create_circuit_panel(workspace: Path) -> Panel:
    """Create circuit breaker panel."""
    loop_file = workspace / ".loop_state.json"
    
    if not loop_file.exists():
        return Panel(
            "[dim]Not active[/]",
            title="Circuit Breaker",
            border_style="dim"
        )
    
    try:
        data = json.loads(loop_file.read_text())
        cb = data.get("circuit_breaker", {})
        
        lines = []
        for name, state in cb.items():
            if isinstance(state, dict):
                cb_state = state.get("state", "UNKNOWN")
                failures = state.get("failures", 0)
                
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
        
        content = "\n".join(lines) if lines else "[dim]No circuits[/]"
        return Panel(content, title="Circuit Breaker", border_style="green")
        
    except (json.JSONDecodeError, KeyError):
        return Panel("[red]Error[/]", title="Circuit Breaker")


def create_progress_panel(workspace: Path) -> Panel:
    """Create progress panel."""
    loop_file = workspace / ".loop_state.json"
    
    if not loop_file.exists():
        return Panel(
            "[dim]No active loop[/]",
            title="Product Loop",
            border_style="dim"
        )
    
    try:
        data = json.loads(loop_file.read_text())
        
        iteration = data.get("iteration", 0)
        phase = data.get("phase", "UNKNOWN")
        current = data.get("current_task")
        completed = len(data.get("tasks_completed", []))
        remaining = len(data.get("tasks_remaining", []))
        total = completed + remaining
        
        metrics = data.get("metrics", {})
        success_rate = metrics.get("success_rate", 1.0)
        
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
        
    except (json.JSONDecodeError, KeyError):
        return Panel("[red]Error[/]", title="Product Loop")


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
