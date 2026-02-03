"""up status - Show system health and status."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


@click.command()
@click.option(
    "--json", "as_json",
    is_flag=True,
    help="Output as JSON",
)
def status_cmd(as_json: bool):
    """Show current status of all up systems.
    
    Displays health information for:
    - Context budget (token usage)
    - Circuit breaker states
    - Product loop progress
    - Learning system state
    """
    cwd = Path.cwd()
    
    status = collect_status(cwd)
    
    if as_json:
        console.print(json.dumps(status, indent=2))
        return
    
    # Display rich formatted output
    display_status(status)


def collect_status(workspace: Path) -> dict:
    """Collect status from all systems."""
    status = {
        "workspace": str(workspace),
        "initialized": False,
        "context_budget": None,
        "loop_state": None,
        "circuit_breaker": None,
        "skills": [],
        "hooks": None,
        "memory": None,
    }
    
    # Check if initialized
    claude_dir = workspace / ".claude"
    cursor_dir = workspace / ".cursor"
    up_dir = workspace / ".up"
    status["initialized"] = claude_dir.exists() or cursor_dir.exists() or up_dir.exists()
    
    if not status["initialized"]:
        return status
    
    # Git hooks status
    from up.commands.sync import check_hooks_installed
    status["hooks"] = check_hooks_installed(workspace)
    
    # Memory status
    memory_dir = workspace / ".up" / "memory"
    if memory_dir.exists():
        try:
            from up.memory import MemoryManager
            manager = MemoryManager(workspace, use_vectors=False)  # Fast - JSON only
            stats = manager.get_stats()
            status["memory"] = {
                "total": stats.get("total", 0),
                "branch": stats.get("current_branch", "unknown"),
                "commit": stats.get("current_commit", "unknown"),
            }
        except Exception:
            status["memory"] = {"total": 0}
    
    # Context budget
    context_file = workspace / ".claude/context_budget.json"
    if context_file.exists():
        try:
            status["context_budget"] = json.loads(context_file.read_text())
        except json.JSONDecodeError:
            status["context_budget"] = {"error": "Invalid JSON"}
    
    # Loop state
    loop_file = workspace / ".loop_state.json"
    if loop_file.exists():
        try:
            data = json.loads(loop_file.read_text())
            status["loop_state"] = {
                "iteration": data.get("iteration", 0),
                "phase": data.get("phase", "UNKNOWN"),
                "current_task": data.get("current_task"),
                "tasks_completed": len(data.get("tasks_completed", [])),
                "tasks_remaining": len(data.get("tasks_remaining", [])),
                "success_rate": data.get("metrics", {}).get("success_rate", 1.0),
            }
            status["circuit_breaker"] = data.get("circuit_breaker", {})
        except json.JSONDecodeError:
            status["loop_state"] = {"error": "Invalid JSON"}
    
    # Skills
    skills_dirs = [
        workspace / ".claude/skills",
        workspace / ".cursor/skills",
    ]
    for skills_dir in skills_dirs:
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    status["skills"].append(skill_dir.name)
    
    return status


def display_status(status: dict) -> None:
    """Display status in rich format."""
    
    # Header
    workspace_name = Path(status["workspace"]).name
    if status["initialized"]:
        header = f"[bold green]✓[/] {workspace_name} - up systems active"
    else:
        header = f"[bold yellow]○[/] {workspace_name} - not initialized"
        console.print(Panel(header, border_style="yellow"))
        console.print("\nRun [cyan]up init[/] to initialize up systems.")
        return
    
    console.print(Panel(header, border_style="green"))
    
    # Context Budget
    console.print("\n[bold]Context Budget[/]")
    if status["context_budget"]:
        budget = status["context_budget"]
        if "error" in budget:
            console.print(f"  [red]Error: {budget['error']}[/]")
        else:
            usage = budget.get("usage_percent", 0)
            remaining = budget.get("remaining_tokens", 0)
            budget_status = budget.get("status", "OK")
            
            # Color based on status
            if budget_status == "CRITICAL":
                color = "red"
                icon = "🔴"
            elif budget_status == "WARNING":
                color = "yellow"
                icon = "🟡"
            else:
                color = "green"
                icon = "🟢"
            
            console.print(f"  {icon} Status: [{color}]{budget_status}[/]")
            console.print(f"  Usage: {usage:.1f}% ({remaining:,} tokens remaining)")
    else:
        console.print("  [dim]Not configured[/]")
    
    # Circuit Breaker
    console.print("\n[bold]Circuit Breaker[/]")
    if status["circuit_breaker"]:
        cb = status["circuit_breaker"]
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
                
                console.print(f"  {icon} {name}: [{color}]{cb_state}[/] (failures: {failures})")
    else:
        console.print("  [dim]Not active[/]")
    
    # Loop State
    console.print("\n[bold]Product Loop[/]")
    if status["loop_state"]:
        loop = status["loop_state"]
        if "error" in loop:
            console.print(f"  [red]Error: {loop['error']}[/]")
        else:
            console.print(f"  Iteration: {loop.get('iteration', 0)}")
            console.print(f"  Phase: {loop.get('phase', 'UNKNOWN')}")
            
            current = loop.get("current_task")
            if current:
                console.print(f"  Current Task: [cyan]{current}[/]")
            
            completed = loop.get("tasks_completed", 0)
            remaining = loop.get("tasks_remaining", 0)
            total = completed + remaining
            
            if total > 0:
                progress = completed / total * 100
                bar_len = 20
                filled = int(bar_len * completed / total)
                bar = "█" * filled + "░" * (bar_len - filled)
                console.print(f"  Progress: [{bar}] {progress:.0f}% ({completed}/{total})")
            
            success_rate = loop.get("success_rate", 1.0)
            console.print(f"  Success Rate: {success_rate * 100:.0f}%")
    else:
        console.print("  [dim]Not active[/]")
    
    # Memory
    console.print("\n[bold]Memory[/]")
    if status["memory"]:
        mem = status["memory"]
        total = mem.get("total", 0)
        branch = mem.get("branch", "unknown")
        commit = mem.get("commit", "unknown")
        console.print(f"  📚 {total} entries | Branch: [cyan]{branch}[/] @ {commit}")
    else:
        console.print("  [dim]Not initialized - run [cyan]up memory sync[/][/]")
    
    # Git Hooks
    console.print("\n[bold]Auto-Sync (Git Hooks)[/]")
    hooks = status.get("hooks", {})
    if hooks.get("git"):
        post_commit = hooks.get("post_commit", False)
        post_checkout = hooks.get("post_checkout", False)
        
        if post_commit and post_checkout:
            console.print("  [green]✓ Enabled[/] - commits auto-indexed to memory")
        else:
            console.print("  [yellow]⚠ Partially installed[/]")
            if not post_commit:
                console.print("    • Missing: post-commit hook")
            if not post_checkout:
                console.print("    • Missing: post-checkout hook")
            console.print("\n  [dim]Run [cyan]up hooks[/] to install missing hooks[/]")
    else:
        console.print("  [yellow]✗ Not installed[/]")
        console.print("  [dim]Run [cyan]up hooks[/] to enable auto-sync on commits[/]")
    
    # Skills
    console.print("\n[bold]Skills[/]")
    if status["skills"]:
        for skill in status["skills"]:
            console.print(f"  • {skill}")
    else:
        console.print("  [dim]No skills installed[/]")


if __name__ == "__main__":
    status_cmd()
