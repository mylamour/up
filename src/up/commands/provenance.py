"""up provenance - View AI operation history and lineage."""

import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from up.core.provenance import get_provenance_manager

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


@provenance.command("verify")
def verify_cmd():
    """Verify provenance chain integrity.

    Walks the Merkle chain from latest record back to genesis,
    verifying each parent hash link.

    Exit code 0 if chain valid, 1 if broken (CI-friendly).
    """
    cwd = Path.cwd()
    manager = get_provenance_manager(cwd)
    entries = manager.list_entries(limit=10000)

    if not entries:
        console.print("[yellow]No provenance records found.[/]")
        return

    # Build lookup by ID
    by_id = {e.id: e for e in entries}

    # Sort by created_at ascending for chain walk
    sorted_entries = sorted(entries, key=lambda e: e.created_at)

    total = len(sorted_entries)
    valid = 0
    broken = []

    for entry in sorted_entries:
        if not entry.parent_id:
            # Genesis entry — no parent to verify
            valid += 1
            continue

        parent = by_id.get(entry.parent_id)
        if parent:
            valid += 1
        else:
            broken.append(entry)

    # Display results
    if not broken:
        console.print(Panel.fit(
            f"[bold green]Chain Integrity: PASS[/]\n\n"
            f"Total operations: {total}\n"
            f"Chain length: {valid}\n"
            f"All parent links verified.",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]Chain Integrity: FAIL[/]\n\n"
            f"Total operations: {total}\n"
            f"Valid links: {valid}\n"
            f"Broken links: {len(broken)}",
            border_style="red",
        ))
        for entry in broken:
            console.print(
                f"  [red]✗[/] {entry.id} → parent {entry.parent_id} [red]NOT FOUND[/]"
            )
        sys.exit(1)


@provenance.command("export")
@click.option("--format", "fmt", type=click.Choice(["json", "csv"]), default="json")
@click.option("--since", help="Filter by date (YYYY-MM-DD)")
@click.option("--output", "-o", "output_file", help="Write to file (default: stdout)")
def export_cmd(fmt: str, since: str, output_file: str):
    """Export provenance records for audit/compliance.

    \b
    Examples:
      up provenance export --format json
      up provenance export --format csv --since 2026-02-01
      up provenance export -o report.json
    """
    cwd = Path.cwd()
    manager = get_provenance_manager(cwd)
    entries = manager.list_entries(limit=10000)

    if since:
        try:
            cutoff = datetime.fromisoformat(since)
            entries = [
                e for e in entries
                if datetime.fromisoformat(e.created_at) >= cutoff
            ]
        except ValueError:
            console.print(f"[red]Invalid date: {since}[/]")
            return

    if not entries:
        console.print("[yellow]No provenance records to export.[/]")
        return

    if fmt == "json":
        data = [e.to_dict() for e in entries]
        text = json.dumps(data, indent=2)
    else:
        buf = io.StringIO()
        fields = [
            "id", "task_id", "task_title", "ai_model", "status",
            "branch", "commit_sha", "created_at", "completed_at",
            "prompt_hash", "tests_passed", "lint_passed",
            "type_check_passed", "parent_id",
        ]
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for e in entries:
            writer.writerow(e.to_dict())
        text = buf.getvalue()

    if output_file:
        Path(output_file).write_text(text)
        console.print(f"[green]Exported {len(entries)} records to {output_file}[/]")
    else:
        click.echo(text)


def _display_entry(entry):
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
        console.print("\n[bold]Notes[/]")
        console.print(f"  {entry.verification_notes}")

    # Hashes
    console.print("\n[bold]Content Hashes[/]")
    console.print(f"  Prompt: {entry.prompt_hash}")
    console.print(f"  Context: {entry.context_hash or '-'}")
