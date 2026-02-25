"""up status - Show system health and status."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from up.commands.start.helpers import is_initialized

console = Console()


@click.command()
@click.option(
    "--json", "as_json",
    is_flag=True,
    help="Output as JSON",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Include provenance summary",
)
def status_cmd(as_json: bool, verbose: bool):
    """Show current status of all up systems.
    
    Displays health information for:
    - Context budget (token usage)
    - Circuit breaker states
    - Product loop progress
    - Learning system state
    
    Use --verbose for provenance summary.
    """
    cwd = Path.cwd()
    
    status = collect_status(cwd)

    if verbose:
        status["provenance"] = _collect_provenance_summary(cwd)
    
    if as_json:
        console.print(json.dumps(status, indent=2))
        return
    
    display_status(status, verbose=verbose)


def collect_status(workspace: Path) -> dict:
    """Collect status from all systems."""
    status = {
        "workspace": str(workspace),
        "initialized": False,
        "state_version": None,
        "context_budget": None,
        "loop_state": None,
        "circuit_breaker": None,
        "checkpoints": None,
        "agents": None,
        "doom_loop": None,
        "skills": [],
        "hooks": None,
        "memory": None,
        "plugins": None,
        "provenance_chain": None,
    }
    
    # Check if initialized
    status["initialized"] = is_initialized(workspace)
    
    if not status["initialized"]:
        return status
    
    # Try to load unified state first
    try:
        from up.core.state import get_state_manager
        manager = get_state_manager(workspace)
        state = manager.state
        status["state_version"] = state.version
        
        # Context budget from unified state
        status["context_budget"] = {
            "budget": state.context.budget,
            "total_tokens": state.context.total_tokens,
            "remaining_tokens": state.context.remaining_tokens,
            "usage_percent": state.context.usage_percent,
            "status": state.context.status,
        }
        
        # Loop state from unified state
        status["loop_state"] = {
            "iteration": state.loop.iteration,
            "phase": state.loop.phase,
            "current_task": state.loop.current_task,
            "tasks_completed": len(state.loop.tasks_completed),
            "tasks_failed": len(state.loop.tasks_failed),
            "success_rate": state.metrics.success_rate,
            "last_checkpoint": state.loop.last_checkpoint,
        }
        
        # Circuit breakers
        status["circuit_breaker"] = {
            name: {"state": cb.state, "failures": cb.failures}
            for name, cb in state.circuit_breakers.items()
        }
        
        # Checkpoints
        status["checkpoints"] = {
            "total": len(state.checkpoints),
            "last": state.loop.last_checkpoint,
            "recent": state.checkpoints[-5:] if state.checkpoints else [],
        }
        
        # Agents
        if state.agents:
            status["agents"] = {
                task_id: {
                    "status": agent.status,
                    "phase": agent.phase,
                    "worktree": agent.worktree_path,
                }
                for task_id, agent in state.agents.items()
            }
        
        # Doom loop detection
        is_doom, doom_msg = manager.check_doom_loop()
        if is_doom or state.loop.consecutive_failures > 0:
            status["doom_loop"] = {
                "triggered": is_doom,
                "consecutive_failures": state.loop.consecutive_failures,
                "threshold": state.loop.doom_loop_threshold,
                "message": doom_msg if is_doom else None,
            }
            
    except ImportError:
        # Fallback to old state files
        _collect_legacy_status(workspace, status)
    
    # Git hooks status
    from up.commands.sync import check_hooks_installed
    status["hooks"] = check_hooks_installed(workspace)
    
    # Memory status
    memory_dir = workspace / ".up" / "memory"
    if memory_dir.exists():
        try:
            from up.memory import MemoryManager
            manager = MemoryManager(workspace, use_vectors=False)
            stats = manager.get_stats()
            status["memory"] = {
                "total": stats.get("total", 0),
                "branch": stats.get("current_branch", "unknown"),
                "commit": stats.get("current_commit", "unknown"),
            }
        except Exception:
            status["memory"] = {"total": 0}
    
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

    # Plugins
    try:
        from up.plugins.registry import PluginRegistry
        reg = PluginRegistry(workspace)
        reg.load()
        all_plugins = reg.list_all()
        enabled = [p for p in all_plugins if p.get("enabled", True)]
        status["plugins"] = {
            "total": len(all_plugins),
            "enabled": len(enabled),
            "names": [p.get("name", "?") for p in enabled],
        }
    except Exception:
        # Fallback: count plugin dirs
        builtin = workspace / ".up" / "plugins" / "builtin"
        installed = workspace / ".up" / "plugins" / "installed"
        count = 0
        if builtin.exists():
            count += sum(1 for d in builtin.iterdir() if d.is_dir() and (d / "plugin.json").exists())
        if installed.exists():
            count += sum(1 for d in installed.iterdir() if d.is_dir() and (d / "plugin.json").exists())
        if count:
            status["plugins"] = {"total": count, "enabled": count, "names": []}

    # Provenance chain health
    try:
        from up.core.provenance import get_provenance_manager
        prov = get_provenance_manager(workspace)
        entries = prov.list_entries(limit=1000)
        if entries:
            by_id = {e.id for e in entries}
            broken = sum(1 for e in entries if e.parent_id and e.parent_id not in by_id)
            last = max(entries, key=lambda e: e.created_at)
            status["provenance_chain"] = {
                "length": len(entries),
                "integrity": "pass" if broken == 0 else "fail",
                "broken_links": broken,
                "last_operation": last.task_id,
                "last_status": last.status,
            }
    except Exception:
        pass

    return status


def _collect_provenance_summary(workspace: Path) -> dict:
    """Collect provenance statistics for --verbose output."""
    try:
        from up.core.provenance import get_provenance_manager
        prov = get_provenance_manager(workspace)
        return prov.get_stats()
    except Exception:
        return {}


def _collect_legacy_status(workspace: Path, status: dict) -> None:
    """Collect status from legacy state files."""
    # Context budget (old location)
    context_file = workspace / ".claude/context_budget.json"
    if context_file.exists():
        try:
            status["context_budget"] = json.loads(context_file.read_text())
        except json.JSONDecodeError:
            status["context_budget"] = {"error": "Invalid JSON"}
    
    # Loop state (old location)
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


def display_status(status: dict, verbose: bool = False) -> None:
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
    
    # Product Loop State
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
            failed = loop.get("tasks_failed", 0)
            remaining = loop.get("tasks_remaining", 0)
            total = completed + failed + remaining if remaining else completed + failed
            
            if total > 0:
                progress = completed / total * 100
                bar_len = 20
                filled = int(bar_len * completed / total)
                bar = "█" * filled + "░" * (bar_len - filled)
                console.print(f"  Progress: [{bar}] {progress:.0f}% ({completed}/{total})")
            
            success_rate = loop.get("success_rate", 1.0)
            console.print(f"  Success Rate: {success_rate * 100:.0f}%")
            
            last_cp = loop.get("last_checkpoint")
            if last_cp:
                console.print(f"  Last Checkpoint: [cyan]{last_cp}[/]")
    else:
        console.print("  [dim]Not active[/]")
    
    # Doom Loop Detection
    if status.get("doom_loop"):
        doom = status["doom_loop"]
        console.print("\n[bold]Doom Loop Detection[/]")
        if doom["triggered"]:
            console.print(f"  [red]⚠ TRIGGERED[/] - {doom['consecutive_failures']}/{doom['threshold']} failures")
            console.print(f"  [dim]{doom.get('message', '')}[/]")
        else:
            console.print(f"  Consecutive Failures: {doom['consecutive_failures']}/{doom['threshold']}")
    
    # Checkpoints
    if status.get("checkpoints"):
        cp = status["checkpoints"]
        console.print("\n[bold]Checkpoints[/]")
        console.print(f"  Total: {cp['total']}")
        if cp.get("recent"):
            console.print(f"  Recent: {', '.join(cp['recent'][-3:])}")
    
    # Active Agents
    if status.get("agents"):
        console.print("\n[bold]Active Agents[/]")
        for task_id, agent in status["agents"].items():
            status_icon = "🟢" if agent["status"] == "passed" else "🟡" if agent["status"] in ["executing", "verifying"] else "🔴"
            console.print(f"  {status_icon} {task_id}: {agent['status']} ({agent['phase']})")
    
    # Memory
    console.print("\n[bold]Memory[/]")
    if status["memory"]:
        mem = status["memory"]
        total = mem.get("total", 0)
        branch = mem.get("branch", "unknown")
        commit = mem.get("commit", "unknown")
        console.print(f"  📚 {total} entries | Branch: [cyan]{branch}[/] @ {commit}")
    else:
        console.print("  [dim]Not initialized — memory builds automatically via git hooks[/]")
    
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
            console.print("\n  [dim]Run [cyan]up init[/] to reinstall missing hooks[/]")
    else:
        console.print("  [yellow]✗ Not installed[/]")
        console.print("  [dim]Run [cyan]up init --hooks[/] to enable auto-sync on commits[/]")

    # Plugins
    console.print("\n[bold]Plugins[/]")
    if status.get("plugins"):
        plug = status["plugins"]
        console.print(f"  Installed: {plug['total']} | Enabled: {plug['enabled']}")
        if plug.get("names"):
            console.print(f"  Active: {', '.join(plug['names'][:8])}")
    else:
        console.print("  [dim]No plugins installed[/]")

    # Provenance Chain
    console.print("\n[bold]Provenance Chain[/]")
    if status.get("provenance_chain"):
        pc = status["provenance_chain"]
        integrity = pc["integrity"]
        icon = "[green]✓[/]" if integrity == "pass" else "[red]✗[/]"
        console.print(f"  {icon} Integrity: {integrity.upper()} | Length: {pc['length']}")
        if pc.get("broken_links", 0) > 0:
            console.print(f"  [red]Broken links: {pc['broken_links']}[/]")
        console.print(f"  Last: {pc.get('last_operation', '?')} ({pc.get('last_status', '?')})")
    else:
        console.print("  [dim]No provenance data[/]")

    # Skills
    console.print("\n[bold]Skills[/]")
    if status["skills"]:
        for skill in status["skills"]:
            console.print(f"  • {skill}")
    else:
        console.print("  [dim]No skills installed[/]")
    
    # Provenance (verbose only)
    if verbose and status.get("provenance"):
        prov = status["provenance"]
        console.print("\n[bold]Provenance Summary[/]")
        total = prov.get("total_operations", 0)
        accepted = prov.get("accepted", 0)
        rejected = prov.get("rejected", 0)
        pending = prov.get("pending", 0)
        rate = prov.get("acceptance_rate", 0)
        console.print(f"  Operations: {total} (accepted: {accepted}, rejected: {rejected}, pending: {pending})")
        console.print(f"  Acceptance Rate: {rate*100:.0f}%")
        test_rate = prov.get("test_pass_rate", 0)
        console.print(f"  Test Pass Rate: {test_rate*100:.0f}%")
        models = prov.get("models_used", {})
        if models:
            model_str = ", ".join(f"{m}: {c}" for m, c in models.items())
            console.print(f"  Models: {model_str}")
    elif verbose:
        console.print("\n[bold]Provenance Summary[/]")
        console.print("  [dim]No provenance data — run [cyan]up start[/] to generate[/]")


if __name__ == "__main__":
    status_cmd()
