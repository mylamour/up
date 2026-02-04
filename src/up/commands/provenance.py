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


@provenance.command("list")
@click.option("--limit", "-n", default=20, help="Number of entries to show")
@click.option("--status", type=click.Choice(["pending", "accepted", "rejected"]), help="Filter by status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_cmd(limit: int, status: str, as_json: bool):
    """List recent provenance entries.
    
    \b
    Examples:
      up provenance list
      up provenance list -n 50
      up provenance list --status accepted
    """
    cwd = Path.cwd()
    manager = get_provenance_manager(cwd)
    
    entries = manager.list_entries(limit=limit, status=status)
    
    if not entries:
        console.print("[dim]No provenance entries found[/]")
        console.print("Entries are created when running [cyan]up start[/]")
        return
    
    if as_json:
        output = [e.to_dict() for e in entries]
        console.print(json.dumps(output, indent=2))
        return
    
    table = Table(title=f"Provenance History (last {len(entries)})")
    table.add_column("ID", style="cyan")
    table.add_column("Task")
    table.add_column("Model")
    table.add_column("Status")
    table.add_column("Files")
    table.add_column("Tests")
    table.add_column("Time")
    
    for entry in entries:
        status_icon = {
            "accepted": "🟢",
            "rejected": "🔴",
            "pending": "🟡",
        }.get(entry.status, "⚪")
        
        tests_icon = "✓" if entry.tests_passed else "✗" if entry.tests_passed is False else "-"
        
        table.add_row(
            entry.id,
            entry.task_id[:10] if entry.task_id else "-",
            entry.ai_model[:10],
            f"{status_icon} {entry.status}",
            str(len(entry.files_modified)),
            tests_icon,
            entry.created_at[:16]
        )
    
    console.print(table)


@provenance.command("stats")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def stats_cmd(as_json: bool):
    """Show provenance statistics.
    
    Displays aggregated stats about AI operations,
    including acceptance rates and test results.
    """
    cwd = Path.cwd()
    manager = get_provenance_manager(cwd)
    
    stats = manager.get_stats()
    
    if as_json:
        console.print(json.dumps(stats, indent=2))
        return
    
    console.print(Panel.fit(
        "[bold]AI Operation Statistics[/]",
        border_style="blue"
    ))
    
    # Overview
    console.print("\n[bold]Overview[/]")
    console.print(f"  Total Operations: {stats['total_operations']}")
    console.print(f"  Accepted: [green]{stats['accepted']}[/]")
    console.print(f"  Rejected: [red]{stats['rejected']}[/]")
    console.print(f"  Pending: [yellow]{stats['pending']}[/]")
    
    if stats['total_operations'] > 0:
        console.print(f"  Acceptance Rate: {stats['acceptance_rate']*100:.1f}%")
    
    # Code changes
    console.print("\n[bold]Code Changes[/]")
    console.print(f"  Lines Added: [green]+{stats['total_lines_added']}[/]")
    console.print(f"  Lines Removed: [red]-{stats['total_lines_removed']}[/]")
    
    # Testing
    if stats['tests_run'] > 0:
        console.print("\n[bold]Testing[/]")
        console.print(f"  Tests Run: {stats['tests_run']}")
        console.print(f"  Tests Passed: {stats['tests_passed']}")
        console.print(f"  Pass Rate: {stats['test_pass_rate']*100:.1f}%")
    
    # Models
    if stats['models_used']:
        console.print("\n[bold]AI Models Used[/]")
        for model, count in sorted(stats['models_used'].items(), key=lambda x: -x[1]):
            console.print(f"  {model}: {count}")


@provenance.command("verify")
@click.argument("entry_id")
@click.option("--accept", "-a", is_flag=True, help="Mark as accepted")
@click.option("--reject", "-r", is_flag=True, help="Mark as rejected")
@click.option("--reason", help="Rejection reason")
def verify_cmd(entry_id: str, accept: bool, reject: bool, reason: str):
    """Verify a provenance entry.
    
    Mark an entry as accepted or rejected after review.
    """
    cwd = Path.cwd()
    manager = get_provenance_manager(cwd)
    
    if not accept and not reject:
        console.print("[yellow]Specify --accept or --reject[/]")
        return
    
    entry = manager.get_entry(entry_id)
    if not entry:
        console.print(f"[red]Entry not found: {entry_id}[/]")
        return
    
    if accept:
        entry = manager.complete_operation(entry_id, status="accepted")
        console.print(f"[green]✓[/] Entry {entry_id} marked as accepted")
    elif reject:
        entry = manager.reject_operation(entry_id, reason=reason or "Manual rejection")
        console.print(f"[red]✗[/] Entry {entry_id} marked as rejected")
        if reason:
            console.print(f"  Reason: {reason}")


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
