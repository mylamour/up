"""up sync - Sync all systems."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--memory/--no-memory", default=True, help="Sync memory system")
@click.option("--docs/--no-docs", default=True, help="Update docs")
@click.option("--full", is_flag=True, help="Full sync including file re-indexing")
def sync_cmd(memory: bool, docs: bool, full: bool):
    """Sync all up systems.
    
    Updates memory index, refreshes docs, and ensures all systems
    are in sync with current project state.
    
    \b
    Examples:
      up sync              # Standard sync
      up sync --full       # Full sync with file re-indexing
      up sync --no-docs    # Memory only
    """
    cwd = Path.cwd()
    
    console.print(Panel.fit(
        "[bold blue]Syncing Systems[/]",
        border_style="blue"
    ))
    
    results = {}
    
    # Initialize event system
    from up.events import initialize_event_system
    initialize_event_system(cwd)
    
    steps = []
    if memory:
        steps.append(("Memory", _sync_memory))
    if docs:
        steps.append(("Docs", _sync_docs))
    if full:
        steps.append(("Files", _sync_files))
    
    for name, func in steps:
        console.print(f"[dim]Syncing {name}...[/]", end=" ")
        try:
            result = func(cwd, full)
            results[name.lower()] = result
            details = ", ".join(f"{k}={v}" for k, v in result.items() if v)
            console.print(f"[green]✓[/] {details or 'done'}")
        except Exception as e:
            results[name.lower()] = {"error": str(e)}
            console.print(f"[red]✗[/] {e}")
    
    # Summary
    console.print()
    errors = [k for k, v in results.items() if "error" in v]
    if errors:
        console.print(f"[yellow]Completed with {len(errors)} error(s)[/]")
    else:
        console.print("[green]✓[/] All systems synced")


def _sync_memory(workspace: Path, full: bool) -> dict:
    """Sync memory system."""
    import os
    import sys
    import warnings
    import logging
    from up.memory import MemoryManager, _check_chromadb
    
    # Suppress noisy warnings and logs
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    warnings.filterwarnings("ignore")
    logging.getLogger("chromadb").setLevel(logging.ERROR)
    
    # Redirect stderr temporarily to suppress ChromaDB noise
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    
    try:
        # Use JSON backend if ChromaDB not available (faster, no model download)
        use_vectors = _check_chromadb()
        
        manager = MemoryManager(workspace, use_vectors=use_vectors)
        results = manager.sync()
        
        return {
            "commits": results.get("commits_indexed", 0),
            "files": results.get("files_indexed", 0),
            "backend": manager._backend,
        }
    finally:
        sys.stderr.close()
        sys.stderr = old_stderr


def _sync_docs(workspace: Path, full: bool) -> dict:
    """Sync documentation."""
    from datetime import date
    import re
    
    updated = 0
    
    # Update CONTEXT.md date
    context_file = workspace / "docs" / "CONTEXT.md"
    if context_file.exists():
        content = context_file.read_text()
        today = date.today().isoformat()
        new_content = re.sub(
            r'\*\*Updated\*\*:\s*[\d-]+',
            f'**Updated**: {today}',
            content
        )
        if new_content != content:
            context_file.write_text(new_content)
            updated += 1
    
    # Check INDEX.md exists
    index_file = workspace / "docs" / "INDEX.md"
    if index_file.exists():
        updated += 0  # Just checking
    
    return {"updated": updated}


def _sync_files(workspace: Path, full: bool) -> dict:
    """Sync file index."""
    from up.memory import MemoryManager
    
    manager = MemoryManager(workspace)
    indexed = manager.index_file_changes()
    
    return {"indexed": indexed}


def check_hooks_installed(workspace: Path) -> dict:
    """Check if up-cli hooks are installed.
    
    Returns dict with status of each hook.
    """
    git_dir = workspace / ".git"
    if not git_dir.exists():
        return {"git": False, "post_commit": False, "post_checkout": False}
    
    hooks_dir = git_dir / "hooks"
    
    result = {"git": True, "post_commit": False, "post_checkout": False}
    
    post_commit = hooks_dir / "post-commit"
    if post_commit.exists() and "up-cli" in post_commit.read_text():
        result["post_commit"] = True
    
    post_checkout = hooks_dir / "post-checkout"
    if post_checkout.exists() and "up-cli" in post_checkout.read_text():
        result["post_checkout"] = True
    
    return result


@click.command()
@click.option("--uninstall", is_flag=True, help="Remove hooks instead of installing")
@click.option("--check", is_flag=True, help="Check if hooks are installed")
def hooks_cmd(uninstall: bool, check: bool):
    """Install or uninstall git hooks for automatic syncing.
    
    Installs:
    - post-commit: Auto-index commits to memory
    - post-checkout: Update context on branch switch
    
    \b
    Examples:
      up hooks              # Install hooks
      up hooks --check      # Check status
      up hooks --uninstall  # Remove hooks
    """
    cwd = Path.cwd()
    git_dir = cwd / ".git"
    
    if not git_dir.exists():
        console.print("[red]Error:[/] Not a git repository")
        raise SystemExit(1)
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    if check:
        status = check_hooks_installed(cwd)
        console.print("\n[bold]Git Hooks Status:[/]")
        console.print(f"  post-commit:   {'[green]✓ installed[/]' if status['post_commit'] else '[yellow]✗ not installed[/]'}")
        console.print(f"  post-checkout: {'[green]✓ installed[/]' if status['post_checkout'] else '[yellow]✗ not installed[/]'}")
        
        if not status['post_commit'] or not status['post_checkout']:
            console.print("\n[dim]Run 'up hooks' to install missing hooks[/]")
        return
    
    if uninstall:
        _uninstall_hooks(hooks_dir)
    else:
        _install_hooks(hooks_dir)


def _install_hooks(hooks_dir: Path):
    """Install git hooks."""
    
    # Post-commit hook
    post_commit = hooks_dir / "post-commit"
    post_commit_content = '''#!/bin/bash
# up-cli auto-sync hook
# Indexes commits to memory automatically

# Run in background to not slow down commits
(
    # Wait a moment for git to finish
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
    console.print("[green]✓[/] Installed post-commit hook")
    
    # Post-checkout hook (for branch switches)
    post_checkout = hooks_dir / "post-checkout"
    post_checkout_content = '''#!/bin/bash
# up-cli context update hook
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
    console.print("[green]✓[/] Installed post-checkout hook")
    
    console.print("\n[bold]Hooks installed![/]")
    console.print("Memory will auto-sync on commits.")


def _write_hook(path: Path, content: str):
    """Write hook file with executable permissions."""
    import stat
    
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


def _uninstall_hooks(hooks_dir: Path):
    """Remove up-cli hooks."""
    
    for hook_name in ["post-commit", "post-checkout"]:
        hook_path = hooks_dir / hook_name
        if hook_path.exists():
            content = hook_path.read_text()
            if "up-cli" in content:
                # Remove our section
                lines = content.split("\n")
                new_lines = []
                skip = False
                for line in lines:
                    if "up-cli" in line:
                        skip = True
                    elif skip and line.startswith("exit"):
                        skip = False
                        continue
                    elif not skip:
                        new_lines.append(line)
                
                new_content = "\n".join(new_lines).strip()
                if new_content:
                    hook_path.write_text(new_content)
                else:
                    hook_path.unlink()
                
                console.print(f"[green]✓[/] Removed {hook_name} hook")
    
    console.print("\n[bold]Hooks uninstalled![/]")


if __name__ == "__main__":
    sync_cmd()
