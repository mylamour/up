"""up agent - Multi-agent worktree management.

These commands enable parallel AI development using Git worktrees:
- up agent spawn: Create isolated agent environment
- up agent status: Monitor all active agents
- up agent merge: Squash and merge agent work
- up agent cleanup: Remove completed worktrees
"""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from up.core.state import get_state_manager, AgentState
from up.core.checkpoint import get_checkpoint_manager, NotAGitRepoError
from up.git.utils import is_git_repo, get_current_branch, count_commits_since, make_branch_name, preview_merge

console = Console()


# =============================================================================
# up agent spawn - Create agent worktree
# =============================================================================

@click.command("spawn")
@click.argument("name")
@click.option("--task", "-t", help="Task ID to implement")
@click.option("--branch", "-b", default="main", help="Base branch (default: main)")
@click.option("--title", help="Task title/description")
def spawn_cmd(name: str, task: str, branch: str, title: str):
    """Create an isolated agent environment.
    
    Creates a Git worktree for parallel AI development. Each agent
    works in isolation, preventing code conflicts.
    
    \b
    Examples:
      up agent spawn frontend --task US-007
      up agent spawn auth --task US-008 --title "Add authentication"
      up agent spawn api -b develop
    """
    cwd = Path.cwd()
    
    if not is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    # Create worktree directory
    worktree_dir = cwd / ".worktrees"
    worktree_path = worktree_dir / name
    agent_branch = make_branch_name(name)
    
    if worktree_path.exists():
        console.print(f"[yellow]Warning:[/] Agent '{name}' already exists")
        console.print(f"  Path: {worktree_path}")
        console.print(f"\nTo remove: [cyan]up agent cleanup {name}[/]")
        return
    
    # Create worktree
    console.print(f"Creating agent worktree: [cyan]{name}[/]")
    
    worktree_dir.mkdir(exist_ok=True)
    
    # Create branch and worktree
    result = subprocess.run(
        ["git", "worktree", "add", "-b", agent_branch, str(worktree_path), branch],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        # Branch might exist, try without -b
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_path), agent_branch],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[red]Error:[/] Failed to create worktree")
            console.print(f"[dim]{result.stderr}[/]")
            return
    
    # Copy environment files
    env_files = [".env", ".env.local", ".env.development"]
    copied = []
    for env_file in env_files:
        src = cwd / env_file
        if src.exists():
            shutil.copy(src, worktree_path / env_file)
            copied.append(env_file)
    
    # Create agent state
    agent = AgentState(
        task_id=task or name,
        task_title=title or f"Agent: {name}",
        branch=agent_branch,
        worktree_path=str(worktree_path),
        status="created",
        phase="READY",
    )
    
    # Save to unified state
    state_manager = get_state_manager(cwd)
    state_manager.add_agent(agent)
    
    # Also save state in worktree for standalone access
    agent_state_file = worktree_path / ".agent_state.json"
    agent_state_file.write_text(json.dumps({
        "task_id": agent.task_id,
        "task_title": agent.task_title,
        "branch": agent.branch,
        "status": agent.status,
        "phase": agent.phase,
        "started_at": agent.started_at,
        "parent_workspace": str(cwd),
    }, indent=2))
    
    # Display success
    console.print(f"\n[green]✓[/] Agent '[cyan]{name}[/]' created")
    console.print()
    
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")
    
    table.add_row("Path", str(worktree_path))
    table.add_row("Branch", agent_branch)
    if task:
        table.add_row("Task", task)
    if copied:
        table.add_row("Env files", ", ".join(copied))
    
    console.print(table)
    
    console.print(f"\n[bold]To work in this agent:[/]")
    console.print(f"  cd {worktree_path}")
    console.print(f"\n[bold]When done:[/]")
    console.print(f"  up agent merge {name}")


# =============================================================================
# up agent status - Monitor all agents
# =============================================================================

@click.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status_cmd(as_json: bool):
    """Show status of all active agents.
    
    Lists all agent worktrees with their current status,
    commits, and health indicators.
    """
    cwd = Path.cwd()
    
    if not is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    # Get agents from state
    state_manager = get_state_manager(cwd)
    agents = state_manager.state.agents
    
    # Also check for worktrees not in state
    worktree_dir = cwd / ".worktrees"
    if worktree_dir.exists():
        for wt_path in worktree_dir.iterdir():
            if wt_path.is_dir():
                agent_id = wt_path.name
                if agent_id not in agents:
                    # Found orphan worktree
                    state_file = wt_path / ".agent_state.json"
                    if state_file.exists():
                        try:
                            data = json.loads(state_file.read_text())
                            agents[agent_id] = AgentState(
                                task_id=data.get("task_id", agent_id),
                                task_title=data.get("task_title", ""),
                                branch=data.get("branch", make_branch_name(agent_id)),
                                worktree_path=str(wt_path),
                                status=data.get("status", "unknown"),
                                phase=data.get("phase", "UNKNOWN"),
                            )
                        except json.JSONDecodeError:
                            pass
    
    if not agents:
        console.print("[dim]No active agents[/]")
        console.print("\nCreate one with: [cyan]up agent spawn <name>[/]")
        return
    
    # JSON output
    if as_json:
        output = {
            task_id: {
                "task_title": agent.task_title,
                "branch": agent.branch,
                "worktree": agent.worktree_path,
                "status": agent.status,
                "phase": agent.phase,
                "started_at": agent.started_at,
            }
            for task_id, agent in agents.items()
        }
        console.print(json.dumps(output, indent=2))
        return
    
    # Table output
    table = Table(title="Active Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Task")
    table.add_column("Status")
    table.add_column("Commits")
    table.add_column("Branch")
    
    for task_id, agent in agents.items():
        # Count commits
        wt_path = Path(agent.worktree_path)
        commits = 0
        if wt_path.exists():
            commits = count_commits_since(wt_path, "main")
        
        # Status icon
        status_icons = {
            "created": "🟡",
            "executing": "🔵",
            "verifying": "🟠",
            "passed": "🟢",
            "failed": "🔴",
            "merged": "✅",
        }
        icon = status_icons.get(agent.status, "⚪")
        
        table.add_row(
            task_id,
            agent.task_title[:30] + "..." if len(agent.task_title) > 30 else agent.task_title,
            f"{icon} {agent.status}",
            str(commits),
            agent.branch,
        )
    
    console.print(table)
    
    console.print(f"\n[dim]Total agents: {len(agents)}[/]")


# =============================================================================
# up agent merge - Squash and merge agent work
# =============================================================================

@click.command("merge")
@click.argument("name")
@click.option("--target", "-t", default="main", help="Target branch (default: main)")
@click.option("--no-squash", is_flag=True, help="Don't squash commits")
@click.option("--message", "-m", help="Custom commit message")
@click.option("--keep", "-k", is_flag=True, help="Keep worktree after merge")
def merge_cmd(name: str, target: str, no_squash: bool, message: str, keep: bool):
    """Merge agent work into target branch.
    
    Squashes all agent commits into a single clean commit
    and merges into the target branch.
    
    \b
    Examples:
      up agent merge frontend              # Merge to main
      up agent merge auth --target develop # Merge to develop
      up agent merge api --no-squash       # Keep individual commits
    """
    cwd = Path.cwd()
    
    if not is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    state_manager = get_state_manager(cwd)
    agents = state_manager.state.agents
    
    # Find agent
    agent = agents.get(name)
    worktree_path = cwd / ".worktrees" / name
    
    if not agent and not worktree_path.exists():
        console.print(f"[red]Error:[/] Agent '{name}' not found")
        console.print(f"\nList agents: [cyan]up agent status[/]")
        return
    
    # Get branch name
    agent_branch = agent.branch if agent else make_branch_name(name)
    
    # Check branch hierarchy enforcement
    try:
        config = state_manager.config
        if getattr(config, "branch_hierarchy_enforcement", False):
            from up.commands.branch import _can_merge
            can_merge_hierarchy, reason = _can_merge(agent_branch, target)
            if not can_merge_hierarchy:
                console.print(f"[red]Branch hierarchy violation:[/] {reason}")
                console.print("[dim]Use --force or disable enforcement in .up/config.json[/]")
                return
    except Exception:
        pass  # Don't block merge if hierarchy check fails
    
    # Check for commits
    commits = count_commits_since(worktree_path, target)
    
    console.print(f"[bold]Merging agent:[/] {name}")
    console.print(f"  Branch: {agent_branch}")
    console.print(f"  Commits: {commits}")
    console.print(f"  Target: {target}")

    # Preview merge for conflicts
    can_merge, conflicts = preview_merge(agent_branch, target, cwd)
    if not can_merge:
        console.print(f"\n[red]Merge conflicts detected![/]")
        if conflicts:
            console.print("[yellow]Conflicting files:[/]")
            for f in conflicts:
                console.print(f"  • {f}")
        console.print(f"\nResolve conflicts manually or use:")
        console.print(f"  cd {worktree_path}")
        console.print(f"  git merge {target}")
        return

    if commits == 0:
        console.print("\n[yellow]No commits to merge[/]")
        if not keep:
            if click.confirm("Remove worktree anyway?"):
                _remove_worktree(cwd, name, agent_branch)
        return
    
    # Create checkpoint before merge
    try:
        checkpoint_manager = get_checkpoint_manager(cwd)
        checkpoint_manager.save(message=f"Before merge: {name}", task_id=name)
        console.print("[dim]Checkpoint created[/]")
    except NotAGitRepoError:
        pass
    
    # Checkout target branch
    result = subprocess.run(
        ["git", "checkout", target],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        console.print(f"[red]Error:[/] Failed to checkout {target}")
        console.print(f"[dim]{result.stderr}[/]")
        return
    
    # Merge
    squash = not no_squash
    
    if squash:
        # Squash merge
        result = subprocess.run(
            ["git", "merge", "--squash", agent_branch],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[red]Error:[/] Merge failed")
            console.print(f"[dim]{result.stderr}[/]")
            return
        
        # Commit
        commit_msg = message or f"feat({name}): {agent.task_title if agent else 'Agent work'}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[yellow]Warning:[/] Commit may have failed")
            console.print(f"[dim]{result.stderr}[/]")
    else:
        # Regular merge
        commit_msg = message or f"Merge {agent_branch} into {target}"
        result = subprocess.run(
            ["git", "merge", agent_branch, "-m", commit_msg],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            console.print(f"[red]Error:[/] Merge failed")
            console.print(f"[dim]{result.stderr}[/]")
            return
    
    console.print(f"\n[green]✓[/] Merged {commits} commit(s) to {target}")
    
    # Update state
    if agent:
        agent.status = "merged"
        agent.completed_at = datetime.now().isoformat()
        state_manager.save()
    
    # Cleanup
    if not keep:
        _remove_worktree(cwd, name, agent_branch)
        console.print(f"[green]✓[/] Removed worktree and branch")
        
        # Remove from state
        state_manager.remove_agent(name)


def _remove_worktree(cwd: Path, name: str, branch: str):
    """Remove worktree and branch."""
    worktree_path = cwd / ".worktrees" / name
    
    # Remove worktree
    if worktree_path.exists():
        subprocess.run(
            ["git", "worktree", "remove", str(worktree_path), "--force"],
            cwd=cwd,
            capture_output=True
        )
    
    # Delete branch
    subprocess.run(
        ["git", "branch", "-D", branch],
        cwd=cwd,
        capture_output=True
    )


# =============================================================================
# up agent cleanup - Remove completed worktrees
# =============================================================================

@click.command("cleanup")
@click.argument("name", required=False)
@click.option("--all", "cleanup_all", is_flag=True, help="Remove all agents")
@click.option("--merged", is_flag=True, help="Remove only merged agents")
@click.option("--force", "-f", is_flag=True, help="Force removal")
def cleanup_cmd(name: str, cleanup_all: bool, merged: bool, force: bool):
    """Remove agent worktrees.
    
    Cleans up completed or abandoned agent environments.
    
    \b
    Examples:
      up agent cleanup frontend   # Remove specific agent
      up agent cleanup --all      # Remove all agents
      up agent cleanup --merged   # Remove only merged agents
    """
    cwd = Path.cwd()
    
    if not is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    state_manager = get_state_manager(cwd)
    agents = state_manager.state.agents.copy()
    
    removed = []
    
    if name:
        # Remove specific agent
        agent = agents.get(name)
        branch = agent.branch if agent else make_branch_name(name)
        
        if not force:
            if not click.confirm(f"Remove agent '{name}'?"):
                return
        
        _remove_worktree(cwd, name, branch)
        state_manager.remove_agent(name)
        removed.append(name)
        
    elif cleanup_all:
        # Remove all agents
        if not force:
            if not click.confirm(f"Remove all {len(agents)} agents?"):
                return
        
        for task_id, agent in agents.items():
            _remove_worktree(cwd, task_id, agent.branch)
            removed.append(task_id)
        
        state_manager.state.agents.clear()
        state_manager.state.parallel.agents.clear()
        state_manager.save()
        
    elif merged:
        # Remove only merged agents
        for task_id, agent in agents.items():
            if agent.status == "merged":
                _remove_worktree(cwd, task_id, agent.branch)
                state_manager.remove_agent(task_id)
                removed.append(task_id)
    
    else:
        console.print("Specify an agent name or use --all/--merged")
        console.print("\nUsage:")
        console.print("  up agent cleanup <name>")
        console.print("  up agent cleanup --all")
        console.print("  up agent cleanup --merged")
        return
    
    if removed:
        console.print(f"[green]✓[/] Removed {len(removed)} agent(s): {', '.join(removed)}")
    else:
        console.print("[dim]No agents to remove[/]")


# =============================================================================
# Command Group
# =============================================================================

@click.group()
def agent():
    """Multi-agent worktree management.
    
    Enable parallel AI development by creating isolated
    Git worktrees for each task.
    """
    pass


agent.add_command(spawn_cmd, name="spawn")
agent.add_command(status_cmd, name="status")
agent.add_command(merge_cmd, name="merge")
agent.add_command(cleanup_cmd, name="cleanup")
