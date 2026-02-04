"""up branch - Branch hierarchy management.

Implements a tiered branch model for AI-assisted development:
- main: Stable, production-ready code
- develop: Integration branch for features
- feature/*: Feature branches from develop
- agent/*: AI worktree branches

Changes flow upward: agent/* → feature/* → develop → main
"""

import subprocess
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


# Branch hierarchy configuration
BRANCH_HIERARCHY = {
    "main": {
        "level": 0,
        "description": "Production-ready code",
        "allows_from": ["develop", "hotfix/*"],
        "protected": True,
    },
    "develop": {
        "level": 1,
        "description": "Integration branch",
        "allows_from": ["feature/*", "agent/*"],
        "protected": False,
    },
    "feature/*": {
        "level": 2,
        "description": "Feature branches",
        "allows_from": ["agent/*"],
        "protected": False,
    },
    "agent/*": {
        "level": 3,
        "description": "AI worktree branches",
        "allows_from": [],
        "protected": False,
    },
    "hotfix/*": {
        "level": 1,
        "description": "Emergency fixes",
        "allows_from": [],
        "protected": False,
    },
}


def _is_git_repo(path: Path) -> bool:
    """Check if path is a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=path,
        capture_output=True
    )
    return result.returncode == 0


def _get_current_branch(path: Path) -> str:
    """Get current branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=path,
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _get_all_branches(path: Path) -> List[str]:
    """Get all branch names."""
    result = subprocess.run(
        ["git", "branch", "-a", "--format=%(refname:short)"],
        cwd=path,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]
    return []


def _get_branch_pattern(branch: str) -> str:
    """Get the pattern that matches a branch name."""
    if branch == "main" or branch == "master":
        return "main"
    if branch == "develop" or branch == "development":
        return "develop"
    if branch.startswith("feature/"):
        return "feature/*"
    if branch.startswith("agent/"):
        return "agent/*"
    if branch.startswith("hotfix/"):
        return "hotfix/*"
    return branch


def _can_merge(source: str, target: str) -> tuple[bool, str]:
    """Check if source can be merged into target.
    
    Returns:
        (can_merge, reason)
    """
    source_pattern = _get_branch_pattern(source)
    target_pattern = _get_branch_pattern(target)
    
    target_config = BRANCH_HIERARCHY.get(target_pattern)
    
    if not target_config:
        # Unknown target branch - allow by default
        return True, "Target branch not in hierarchy"
    
    allowed = target_config.get("allows_from", [])
    
    if source_pattern in allowed:
        return True, f"Merge allowed: {source_pattern} → {target_pattern}"
    
    # Check if source is at a lower level (wrong direction)
    source_config = BRANCH_HIERARCHY.get(source_pattern)
    if source_config:
        source_level = source_config.get("level", 99)
        target_level = target_config.get("level", 99)
        
        if source_level < target_level:
            return False, f"Wrong direction: {source_pattern} (level {source_level}) cannot merge into {target_pattern} (level {target_level})"
    
    return False, f"Not allowed: {source_pattern} → {target_pattern}. Allowed sources: {', '.join(allowed)}"


@click.group()
def branch():
    """Branch hierarchy management.
    
    Enforce a tiered branch model for safe AI development.
    Changes flow upward: agent/* → feature/* → develop → main
    """
    pass


@branch.command("status")
def status_cmd():
    """Show current branch status and hierarchy."""
    cwd = Path.cwd()
    
    if not _is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    current = _get_current_branch(cwd)
    all_branches = _get_all_branches(cwd)
    
    console.print(Panel.fit(
        f"[bold]Branch Hierarchy[/]\nCurrent: [cyan]{current}[/]",
        border_style="blue"
    ))
    
    # Build hierarchy tree
    tree = Tree("[bold]Branch Hierarchy[/]")
    
    main_node = tree.add("🔒 [bold green]main[/] - Production")
    develop_node = main_node.add("📦 [yellow]develop[/] - Integration")
    
    # Group branches
    feature_branches = [b for b in all_branches if b.startswith("feature/")]
    agent_branches = [b for b in all_branches if b.startswith("agent/")]
    hotfix_branches = [b for b in all_branches if b.startswith("hotfix/")]
    
    if feature_branches:
        features = develop_node.add(f"🔧 [cyan]feature/*[/] ({len(feature_branches)})")
        for fb in feature_branches[:5]:
            is_current = "← current" if fb == current else ""
            features.add(f"[dim]{fb}[/] {is_current}")
        if len(feature_branches) > 5:
            features.add(f"[dim]... and {len(feature_branches) - 5} more[/]")
    
    if agent_branches:
        agents = develop_node.add(f"🤖 [magenta]agent/*[/] ({len(agent_branches)})")
        for ab in agent_branches[:5]:
            is_current = "← current" if ab == current else ""
            agents.add(f"[dim]{ab}[/] {is_current}")
        if len(agent_branches) > 5:
            agents.add(f"[dim]... and {len(agent_branches) - 5} more[/]")
    
    if hotfix_branches:
        hotfixes = main_node.add(f"🚨 [red]hotfix/*[/] ({len(hotfix_branches)})")
        for hb in hotfix_branches[:3]:
            hotfixes.add(f"[dim]{hb}[/]")
    
    console.print(tree)
    
    # Show allowed merges for current branch
    current_pattern = _get_branch_pattern(current)
    console.print(f"\n[bold]Current Branch:[/] {current} ({current_pattern})")
    
    # Where can we merge to?
    merge_targets = []
    for target, config in BRANCH_HIERARCHY.items():
        if current_pattern in config.get("allows_from", []):
            merge_targets.append(target)
    
    if merge_targets:
        console.print(f"[green]Can merge to:[/] {', '.join(merge_targets)}")
    else:
        console.print("[dim]No merge targets in hierarchy[/]")


@branch.command("check")
@click.argument("target", required=False)
@click.option("--source", "-s", help="Source branch (default: current)")
def check_cmd(target: str, source: str):
    """Check if merge is allowed by hierarchy.
    
    \b
    Examples:
      up branch check develop              # Check current → develop
      up branch check main -s develop      # Check develop → main
    """
    cwd = Path.cwd()
    
    if not _is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    source_branch = source or _get_current_branch(cwd)
    target_branch = target or "develop"
    
    can_merge, reason = _can_merge(source_branch, target_branch)
    
    if can_merge:
        console.print(f"[green]✓[/] {reason}")
        console.print(f"\n  {source_branch} → {target_branch}")
    else:
        console.print(f"[red]✗[/] {reason}")
        
        # Suggest correct flow
        source_pattern = _get_branch_pattern(source_branch)
        source_config = BRANCH_HIERARCHY.get(source_pattern)
        
        if source_config:
            # Find where source can go
            for t, config in BRANCH_HIERARCHY.items():
                if source_pattern in config.get("allows_from", []):
                    console.print(f"\n[dim]Suggestion: Merge to {t} first[/]")
                    break


@branch.command("enforce")
@click.option("--enable", is_flag=True, help="Enable enforcement")
@click.option("--disable", is_flag=True, help="Disable enforcement")
def enforce_cmd(enable: bool, disable: bool):
    """Enable/disable branch hierarchy enforcement.
    
    When enabled, 'up agent merge' will check hierarchy before merging.
    """
    cwd = Path.cwd()
    
    if not _is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    # Store setting in .up/config.json
    config_dir = cwd / ".up"
    config_file = config_dir / "config.json"
    
    import json
    
    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except json.JSONDecodeError:
            pass
    
    if enable:
        config["branch_hierarchy_enforcement"] = True
        console.print("[green]✓[/] Branch hierarchy enforcement enabled")
    elif disable:
        config["branch_hierarchy_enforcement"] = False
        console.print("[yellow]○[/] Branch hierarchy enforcement disabled")
    else:
        current = config.get("branch_hierarchy_enforcement", False)
        status = "[green]enabled[/]" if current else "[dim]disabled[/]"
        console.print(f"Branch hierarchy enforcement: {status}")
        console.print("\nUse [cyan]--enable[/] or [cyan]--disable[/] to change")
        return
    
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2))


@branch.command("create")
@click.argument("name")
@click.option("--type", "branch_type", type=click.Choice(["feature", "agent", "hotfix"]), 
              default="feature", help="Branch type")
@click.option("--from", "from_branch", default="develop", help="Base branch")
def create_cmd(name: str, branch_type: str, from_branch: str):
    """Create a new branch following hierarchy.
    
    \b
    Examples:
      up branch create auth                  # feature/auth from develop
      up branch create US-007 --type agent   # agent/US-007 from develop
      up branch create fix-login --type hotfix --from main
    """
    cwd = Path.cwd()
    
    if not _is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    # Build branch name
    if branch_type == "feature":
        full_name = f"feature/{name}"
    elif branch_type == "agent":
        full_name = f"agent/{name}"
    elif branch_type == "hotfix":
        full_name = f"hotfix/{name}"
        from_branch = "main"  # Hotfixes always from main
    else:
        full_name = name
    
    # Create branch
    result = subprocess.run(
        ["git", "checkout", "-b", full_name, from_branch],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        console.print(f"[green]✓[/] Created branch: [cyan]{full_name}[/]")
        console.print(f"  Based on: {from_branch}")
        
        # Show merge path
        target = "develop" if branch_type in ["feature", "agent"] else "main"
        console.print(f"\n[dim]Merge path: {full_name} → {target}[/]")
    else:
        console.print(f"[red]Error:[/] Failed to create branch")
        console.print(f"[dim]{result.stderr}[/]")
