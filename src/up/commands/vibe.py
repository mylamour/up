"""up save/reset/diff - Vibe coding safety commands.

These commands provide the core safety rails for AI-assisted development:
- up save: Create checkpoint before AI work
- up reset: Restore to checkpoint when AI fails
- up diff: Review AI changes before accepting
"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from up.core.checkpoint import (
    get_checkpoint_manager,
    CheckpointManager,
    CheckpointNotFoundError,
    NotAGitRepoError,
)
from up.core.state import get_state_manager

console = Console()


# =============================================================================
# up save - Create checkpoint
# =============================================================================

@click.command("save")
@click.argument("message", required=False)
@click.option("--task", "-t", help="Associated task ID")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output")
def save_cmd(message: str, task: str, quiet: bool):
    """Create a checkpoint before AI work.
    
    Automatically commits any dirty files and creates a tag for easy recovery.
    Use 'up reset' to restore if AI generation goes wrong.
    
    \b
    Examples:
      up save                      # Auto-named checkpoint
      up save "before auth"        # Named checkpoint
      up save -t US-004            # Link to task
    """
    cwd = Path.cwd()
    
    try:
        manager = get_checkpoint_manager(cwd)
        
        # Check for changes
        has_changes = manager._has_changes()
        
        if not has_changes and not quiet:
            console.print("[dim]No changes to checkpoint (working tree clean)[/]")
        
        # Create checkpoint
        metadata = manager.save(
            message=message,
            task_id=task,
            auto_commit=True
        )
        
        if quiet:
            console.print(metadata.id)
        else:
            console.print(f"[green]✓[/] Checkpoint created: [cyan]{metadata.id}[/]")
            if metadata.files_changed > 0:
                console.print(f"  Committed {metadata.files_changed} file(s)")
            console.print(f"  Commit: {metadata.commit_sha[:8]}")
            console.print(f"  Tag: {metadata.tag_name}")
            console.print(f"\nTo restore: [cyan]up reset {metadata.id}[/]")
        
    except NotAGitRepoError:
        console.print("[red]Error:[/] Not a git repository")
        console.print("Initialize with: [cyan]git init[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


# =============================================================================
# up reset - Restore checkpoint
# =============================================================================

@click.command("reset")
@click.argument("checkpoint_id", required=False)
@click.option("--hard", is_flag=True, default=True, help="Hard reset (discard changes)")
@click.option("--soft", is_flag=True, help="Soft reset (keep changes staged)")
@click.option("--list", "list_checkpoints", is_flag=True, help="List available checkpoints")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def reset_cmd(checkpoint_id: str, hard: bool, soft: bool, list_checkpoints: bool, yes: bool):
    """Reset to a checkpoint.
    
    Instantly restores your code to a previous checkpoint state.
    Use when AI generation produces bad results.
    
    \b
    Examples:
      up reset                     # Reset to last checkpoint
      up reset cp-20260204-1234    # Reset to specific checkpoint
      up reset --list              # Show available checkpoints
    """
    cwd = Path.cwd()
    
    try:
        manager = get_checkpoint_manager(cwd)
        
        # List mode
        if list_checkpoints:
            checkpoints = manager.list_checkpoints(limit=20)
            
            if not checkpoints:
                console.print("[dim]No checkpoints available[/]")
                return
            
            table = Table(title="Available Checkpoints")
            table.add_column("ID", style="cyan")
            table.add_column("Message")
            table.add_column("Branch")
            table.add_column("Time")
            
            for cp in checkpoints:
                table.add_row(
                    cp.id,
                    cp.message[:40] + "..." if len(cp.message) > 40 else cp.message,
                    cp.branch,
                    cp.created_at[:19]
                )
            
            console.print(table)
            return
        
        # Get checkpoint info for confirmation
        if checkpoint_id:
            target = checkpoint_id
        else:
            last = manager.get_last_checkpoint()
            if not last:
                console.print("[yellow]No checkpoints available[/]")
                console.print("Create one with: [cyan]up save[/]")
                return
            target = last.id
        
        # Show what will be reset
        stats = manager.diff_stats(target)
        
        console.print(f"[bold]Reset to checkpoint:[/] {target}")
        if stats["files"] > 0:
            console.print(f"  Changes to discard: {stats['files']} files, "
                         f"+{stats['insertions']} -{stats['deletions']}")
        
        # Confirm
        if not yes:
            if not click.confirm("Proceed with reset?"):
                console.print("[dim]Cancelled[/]")
                return
        
        # Perform reset
        use_hard = not soft
        metadata = manager.restore(checkpoint_id=target, hard=use_hard)
        
        console.print(f"\n[green]✓[/] Reset to [cyan]{metadata.id}[/]")
        console.print(f"  Commit: {metadata.commit_sha[:8]}")
        
        # Update state
        state_manager = get_state_manager(cwd)
        state_manager.state.loop.consecutive_failures = 0  # Reset doom loop counter
        state_manager.save()
        
    except NotAGitRepoError:
        console.print("[red]Error:[/] Not a git repository")
        sys.exit(1)
    except CheckpointNotFoundError as e:
        console.print(f"[red]Error:[/] {e}")
        console.print("List available: [cyan]up reset --list[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


# =============================================================================
# up diff - Review AI changes
# =============================================================================

@click.command("diff")
@click.argument("checkpoint_id", required=False)
@click.option("--stat", is_flag=True, help="Show only stats")
@click.option("--accept", "-a", is_flag=True, help="Accept changes and commit")
@click.option("--reject", "-r", is_flag=True, help="Reject changes and reset")
@click.option("--message", "-m", help="Commit message (with --accept)")
def diff_cmd(checkpoint_id: str, stat: bool, accept: bool, reject: bool, message: str):
    """Review AI changes before accepting.
    
    Shows a syntax-highlighted diff of changes since the last checkpoint.
    Can accept (commit) or reject (reset) the changes.
    
    \b
    Examples:
      up diff                      # Show diff from last checkpoint
      up diff --stat               # Show stats only
      up diff --accept             # Accept and commit changes
      up diff --reject             # Reject and reset to checkpoint
    """
    cwd = Path.cwd()
    
    try:
        manager = get_checkpoint_manager(cwd)
        
        # Get diff
        diff_output = manager.diff_from_checkpoint(checkpoint_id)
        stats = manager.diff_stats(checkpoint_id)
        
        if not diff_output and stats["files"] == 0:
            console.print("[dim]No changes since checkpoint[/]")
            return
        
        # Stats mode
        if stat:
            console.print(Panel.fit(
                f"[bold]Changes since checkpoint[/]\n\n"
                f"Files: {stats['files']}\n"
                f"Insertions: [green]+{stats['insertions']}[/]\n"
                f"Deletions: [red]-{stats['deletions']}[/]",
                border_style="blue"
            ))
            return
        
        # Reject mode
        if reject:
            console.print("[yellow]Rejecting changes...[/]")
            manager.restore(checkpoint_id=checkpoint_id)
            console.print("[green]✓[/] Changes rejected, reset to checkpoint")
            return
        
        # Accept mode
        if accept:
            # Commit the changes
            result = subprocess.run(
                ["git", "add", "-A"],
                cwd=cwd,
                capture_output=True
            )
            
            commit_msg = message or "Accept AI changes"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=cwd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓[/] Changes accepted and committed")
                console.print(f"  Message: {commit_msg}")
            else:
                console.print("[yellow]No changes to commit[/]")
            return
        
        # Show diff
        console.print(Panel.fit(
            f"[bold]Changes since checkpoint[/] "
            f"({stats['files']} files, +{stats['insertions']} -{stats['deletions']})",
            border_style="blue"
        ))
        console.print()
        
        # Syntax-highlighted diff
        syntax = Syntax(diff_output, "diff", theme="monokai", line_numbers=False)
        console.print(syntax)
        
        # Interactive prompt
        console.print()
        console.print("[bold]Actions:[/]")
        console.print("  [cyan]up diff --accept[/]  Accept changes")
        console.print("  [cyan]up diff --reject[/]  Reject and reset")
        
    except NotAGitRepoError:
        console.print("[red]Error:[/] Not a git repository")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


# =============================================================================
# Command Group (for future expansion)
# =============================================================================

@click.group()
def vibe():
    """Vibe coding safety commands."""
    pass


vibe.add_command(save_cmd, name="save")
vibe.add_command(reset_cmd, name="reset")
vibe.add_command(diff_cmd, name="diff")
