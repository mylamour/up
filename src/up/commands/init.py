"""up init - Initialize up systems in existing project."""

import os
import stat
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from up.templates import scaffold_project

console = Console()


@click.command()
@click.option(
    "--ai",
    type=click.Choice(["claude", "cursor", "both"]),
    default="both",
    help="Target AI assistant (claude, cursor, or both)",
)
@click.option(
    "--systems",
    "-s",
    multiple=True,
    type=click.Choice(["docs", "learn", "loop", "all"]),
    default=["all"],
    help="Systems to initialize",
)
@click.option(
    "--hooks/--no-hooks",
    default=True,
    help="Install git hooks for auto-sync (default: yes)",
)
@click.option(
    "--memory/--no-memory",
    default=True,
    help="Build initial memory from git history (default: yes)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files",
)
def init_cmd(ai: str, systems: tuple, hooks: bool, memory: bool, force: bool):
    """Initialize up systems in the current directory.
    
    Automatically:
    - Installs git hooks for memory auto-sync
    - Indexes existing git history to memory
    - Scans project structure for context
    
    Use --no-hooks to disable hooks.
    Use --no-memory to skip initial memory build.
    """
    cwd = Path.cwd()

    console.print(Panel.fit(
        f"[bold blue]up init[/] - Initializing in [cyan]{cwd.name}[/]",
        border_style="blue"
    ))

    # Determine which systems to install
    if "all" in systems:
        systems = ("docs", "learn", "loop")

    # Run scaffolding
    scaffold_project(
        target_dir=cwd,
        ai_target=ai,
        systems=list(systems),
        force=force,
    )

    # Install git hooks automatically
    hooks_installed = False
    if hooks:
        hooks_installed = _install_git_hooks(cwd)

    # Build initial memory from existing project
    memory_stats = None
    if memory:
        memory_stats = _build_initial_memory(cwd)

    console.print("\n[green]✓[/] Initialization complete!")
    
    if hooks_installed:
        console.print("[green]✓[/] Git hooks installed for auto-sync")
    
    if memory_stats:
        console.print(f"[green]✓[/] Memory initialized ({memory_stats['total']} entries)")
    
    _print_next_steps(systems, hooks_installed)


def _build_initial_memory(workspace: Path) -> dict:
    """Build initial memory from existing project.
    
    Indexes:
    - Existing git commits (up to 50)
    - Recent file changes
    - Project structure metadata
    
    Returns stats dict or None if failed.
    """
    try:
        import os
        import warnings
        from up.memory import MemoryManager
        
        # Suppress noisy warnings from tokenizers
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        warnings.filterwarnings("ignore", category=UserWarning)
        
        console.print("\n[dim]Building initial memory...[/]")
        
        manager = MemoryManager(workspace, use_vectors=False)  # Use fast JSON backend
        
        # Index existing commits
        commits = manager.index_recent_commits(count=50)
        console.print(f"  [dim]Indexed {commits} commits[/]")
        
        # Index recent file changes
        files = manager.index_file_changes()
        console.print(f"  [dim]Indexed {files} files[/]")
        
        # Record project initialization
        import subprocess
        
        # Get project info
        project_name = workspace.name
        
        # Detect languages/frameworks
        languages = []
        if (workspace / "pyproject.toml").exists() or (workspace / "requirements.txt").exists():
            languages.append("Python")
        if (workspace / "package.json").exists():
            languages.append("JavaScript/TypeScript")
        if (workspace / "go.mod").exists():
            languages.append("Go")
        if (workspace / "Cargo.toml").exists():
            languages.append("Rust")
        
        # Record initialization as a learning
        if languages:
            manager.record_learning(
                f"Project '{project_name}' initialized with up-cli. "
                f"Languages detected: {', '.join(languages)}. "
                f"Indexed {commits} commits and {files} files into memory."
            )
        
        stats = manager.get_stats()
        return {
            "total": stats.get("total", 0),
            "commits": commits,
            "files": files,
        }
        
    except Exception as e:
        console.print(f"  [yellow]Warning: Could not build memory: {e}[/]")
        return None


def _install_git_hooks(workspace: Path) -> bool:
    """Install git hooks for automatic memory sync.
    
    Returns True if hooks were installed successfully.
    """
    git_dir = workspace / ".git"
    
    if not git_dir.exists():
        console.print("[yellow]⚠[/] Not a git repo, skipping hooks")
        return False
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    # Post-commit hook
    post_commit = hooks_dir / "post-commit"
    post_commit_content = '''#!/bin/bash
# up-cli auto-sync hook (installed by up init)
# Indexes commits to memory automatically

# Run in background to not slow down commits
(
    sleep 1
    
    # Sync memory with latest commit
    if command -v up &> /dev/null; then
        up memory sync 2>/dev/null
    elif command -v python3 &> /dev/null; then
        python3 -m up.memory sync 2>/dev/null
    fi
) &

exit 0
'''
    
    _write_hook(post_commit, post_commit_content)
    
    # Post-checkout hook (for branch switches)
    post_checkout = hooks_dir / "post-checkout"
    post_checkout_content = '''#!/bin/bash
# up-cli context update hook (installed by up init)
# Updates context when switching branches

PREV_HEAD=$1
NEW_HEAD=$2
BRANCH_CHECKOUT=$3

# Only run on branch checkout, not file checkout
if [ "$BRANCH_CHECKOUT" = "1" ]; then
    (
        sleep 1
        if command -v up &> /dev/null; then
            up sync --no-memory 2>/dev/null
        fi
    ) &
fi

exit 0
'''
    
    _write_hook(post_checkout, post_checkout_content)
    
    return True


def _write_hook(path: Path, content: str):
    """Write hook file with executable permissions."""
    # Check for existing hook
    if path.exists():
        existing = path.read_text()
        if "up-cli" in existing:
            # Already our hook, overwrite
            pass
        else:
            # User has custom hook, append
            content = existing + "\n\n" + content
    
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _print_next_steps(systems: tuple, hooks_installed: bool):
    """Print next steps after initialization."""
    console.print("\n[bold]Next steps:[/]")

    if "docs" in systems:
        console.print("  • Edit [cyan]docs/roadmap/vision/PRODUCT_VISION.md[/]")

    if "learn" in systems:
        console.print("  • Run [cyan]up learn auto[/] to analyze your project")

    if "loop" in systems:
        console.print("  • Run [cyan]up start[/] to start development")
    
    if hooks_installed:
        console.print("\n[dim]Auto-sync enabled: commits will be indexed automatically[/]")
