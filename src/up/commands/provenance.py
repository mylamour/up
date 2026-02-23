"""up provenance - View AI operation history and lineage."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from up.core.provenance import get_provenance_manager, ProvenanceEntry

console = Console()


@click.group()
def provenance():
    """View AI operation history and lineage.
    
    Track the provenance of AI-generated code changes,
    including models used, prompts, and verification results.
    """
    pass


@provenance.command("show")
@click.argument("entry_id", required=False)
@click.option("--task", "-t", help="Show by task ID")
def show_cmd(entry_id: str, task: str):
    """Show details of a provenance entry.
    
    \b
    Examples:
      up provenance show abc123def456
      up provenance show --task US-007
    """
    cwd = Path.cwd()
    manager = get_provenance_manager(cwd)
    
    entry = None
    if entry_id:
        entry = manager.get_entry(entry_id)
    elif task:
        entry = manager.get_entry_for_task(task)
    else:
        console.print("[yellow]Provide an entry ID or --task[/]")
        return
    
    if not entry:
        console.print("[red]Entry not found[/]")
        return
    
    _display_entry(entry)



# Removed in v1.0: list, stats, verify
# Provenance stats available via 'up status --verbose'


def _display_entry(entry: ProvenanceEntry) -> None:
    """Display a single provenance entry in detail."""
    status_color = {
        "accepted": "green",
        "rejected": "red",
        "pending": "yellow",
    }.get(entry.status, "white")
    
    console.print(Panel.fit(
        f"[bold]Provenance Entry[/] [{status_color}]{entry.status.upper()}[/]",
        border_style=status_color
    ))
    
    # Basic info
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")
    
    table.add_row("ID", f"[cyan]{entry.id}[/]")
    table.add_row("Task", f"{entry.task_id} - {entry.task_title}")
    table.add_row("AI Model", entry.ai_model)
    table.add_row("Branch", entry.branch)
    table.add_row("Commit", entry.commit_sha or "-")
    table.add_row("Created", entry.created_at)
    if entry.completed_at:
        table.add_row("Completed", entry.completed_at)
    
    console.print(table)
    
    # Prompt preview
    if entry.prompt_preview:
        console.print("\n[bold]Prompt Preview[/]")
        console.print(f"[dim]{entry.prompt_preview}[/]")
    
    # Files
    if entry.files_modified:
        console.print("\n[bold]Files Modified[/]")
        for f in entry.files_modified[:10]:
            console.print(f"  • {f}")
        if len(entry.files_modified) > 10:
            console.print(f"  ... and {len(entry.files_modified) - 10} more")
    
    # Context files
    if entry.context_files:
        console.print("\n[bold]Context Files[/]")
        for f in entry.context_files[:5]:
            console.print(f"  • {f}")
    
    # Verification
    console.print("\n[bold]Verification[/]")
    
    def status_icon(val):
        if val is True:
            return "[green]✓[/]"
        elif val is False:
            return "[red]✗[/]"
        return "[dim]-[/]"
    
    console.print(f"  Tests: {status_icon(entry.tests_passed)}")
    console.print(f"  Lint: {status_icon(entry.lint_passed)}")
    console.print(f"  Type Check: {status_icon(entry.type_check_passed)}")
    
    if entry.verification_notes:
        console.print(f"\n[bold]Notes[/]")
        console.print(f"  {entry.verification_notes}")
    
    # Hashes
    console.print("\n[bold]Content Hashes[/]")
    console.print(f"  Prompt: {entry.prompt_hash}")
    console.print(f"  Context: {entry.context_hash or '-'}")
