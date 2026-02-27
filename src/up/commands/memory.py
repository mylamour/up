"""up memory - Long-term memory management (v1.0 surface: 3 commands)."""


import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def memory_cmd():
    """Long-term memory for context retention across sessions.

    Retains decisions, learnings, errors, and commits using semantic search.
    Auto-indexes via git hooks installed by 'up init'.
    """
    pass


@memory_cmd.command("search")
@click.argument("query")
@click.option("--limit", "-n", default=5, help="Number of results")
@click.option("--type", "-t", "entry_type", help="Filter: session, learning, decision, error, commit")
@click.option("--branch", "-b", help="Filter by branch (use 'current' for current)")
def memory_search(query: str, limit: int, entry_type: str, branch: str):
    """Search memory for relevant information.

    \b
    Examples:
      up memory search "authentication"
      up memory search "database error" --type error
      up memory search "api design" --branch current
    """
    from up.memory import MemoryManager

    manager = MemoryManager()

    if branch == "current":
        branch = manager._get_git_context()["branch"]
        console.print(f"[dim]Searching on branch: {branch}[/]\n")

    results = manager.search(query, limit=limit, entry_type=entry_type, branch=branch)

    if not results:
        branch_info = f" on branch '{branch}'" if branch else ""
        console.print(f"[dim]No memories found for '{query}'{branch_info}[/]")
        return

    console.print(f"\n[bold]Found {len(results)} memories:[/]\n")

    type_colors = {
        "session": "blue", "learning": "green", "decision": "yellow",
        "error": "red", "commit": "cyan", "code": "magenta",
    }

    for entry in results:
        color = type_colors.get(entry.type, "white")
        branch_info = f" @{entry.branch}" if entry.branch else ""
        console.print(Panel(
            entry.content[:500] + ("..." if len(entry.content) > 500 else ""),
            title=f"[{color}]{entry.type}[/]{branch_info} | {entry.timestamp[:10]}",
            border_style=color
        ))


@memory_cmd.command("record")
@click.option("--learning", "-l", help="Record a learning")
@click.option("--decision", "-d", help="Record a decision")
@click.option("--error", "-e", help="Record an error")
@click.option("--solution", "-s", help="Solution for error (use with --error)")
def memory_record(learning: str, decision: str, error: str, solution: str):
    """Record information to memory.

    \b
    Examples:
      up memory record --learning "Use dataclasses for config"
      up memory record --decision "Use PostgreSQL for persistence"
      up memory record --error "ImportError" --solution "pip install package"
    """
    from up.events import emit_learning, emit_decision, emit_error

    if learning:
        emit_learning(learning, source="cli")
        console.print(f"[green]✓[/] Recorded learning: {learning}")

    if decision:
        emit_decision(decision, source="cli")
        console.print(f"[green]✓[/] Recorded decision: {decision}")

    if error:
        emit_error(error, solution, source="cli")
        console.print(f"[green]✓[/] Recorded error: {error}")
        if solution:
            console.print(f"  Solution: {solution}")

    if not any([learning, decision, error]):
        console.print("[yellow]No input provided. Use --learning, --decision, or --error[/]")


@memory_cmd.command("status")
def memory_status():
    """Show memory statistics and health."""
    from up.memory import MemoryManager, _check_chromadb

    manager = MemoryManager()
    stats = manager.get_stats()

    backend = stats.get("backend", "json")
    backend_desc = "ChromaDB (semantic search)" if backend == "chromadb" else "JSON (keyword search)"

    console.print(Panel.fit("[bold blue]Memory Status[/]", border_style="blue"))
    console.print(f"\nBackend: [cyan]{backend_desc}[/]")
    console.print(f"Branch:  [cyan]{stats.get('current_branch', 'unknown')}[/] @ [dim]{stats.get('current_commit', 'unknown')}[/]")

    if backend == "json" and not _check_chromadb():
        console.print("[dim]Install chromadb for semantic search: pip install up-cli[all][/]")

    table = Table(show_header=True)
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right")

    for entry_type in ["Sessions", "Learnings", "Decisions", "Errors", "Commits", "Code Files"]:
        table.add_row(entry_type, str(stats.get(entry_type.lower().replace(" ", "_"), 0)))

    table.add_row("─" * 10, "─" * 5)
    table.add_row("[bold]Total[/]", f"[bold]{stats.get('total', 0)}[/]")
    console.print(table)

    branches = stats.get("branches", {})
    if branches and len(branches) > 1:
        console.print("\n[bold]Knowledge by Branch:[/]")
        for branch, count in sorted(branches.items(), key=lambda x: x[1], reverse=True):
            marker = " ←" if branch == stats.get("current_branch") else ""
            console.print(f"  [cyan]{branch}{marker}[/]: {count}")
