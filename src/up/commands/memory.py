"""up memory - Long-term memory management."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def memory_cmd():
    """Long-term memory management.
    
    Store and recall information across sessions using semantic search.
    Automatically indexes git commits and file changes.
    """
    pass


@memory_cmd.command("search")
@click.argument("query")
@click.option("--limit", "-n", default=5, help="Number of results")
@click.option("--type", "-t", "entry_type", help="Filter by type (session, learning, decision, error, commit)")
@click.option("--branch", "-b", help="Filter by branch (use 'current' for current branch)")
def memory_search(query: str, limit: int, entry_type: str, branch: str):
    """Search memory for relevant information.
    
    Uses semantic search (with ChromaDB) or keyword search (fallback).
    Filter by branch to see knowledge from specific versions.
    
    \b
    Examples:
      up memory search "authentication"
      up memory search "database error" --type error
      up memory search "api design" --branch main
      up memory search "bug fix" --branch current
    """
    from up.memory import MemoryManager
    
    manager = MemoryManager()
    
    # Handle 'current' branch shorthand
    if branch == "current":
        branch = manager._get_git_context()["branch"]
        console.print(f"[dim]Searching on branch: {branch}[/]\n")
    
    results = manager.search(query, limit=limit, entry_type=entry_type, branch=branch)
    
    if not results:
        branch_info = f" on branch '{branch}'" if branch else ""
        console.print(f"[dim]No memories found for '{query}'{branch_info}[/]")
        return
    
    console.print(f"\n[bold]Found {len(results)} memories:[/]\n")
    
    for entry in results:
        # Color by type
        type_colors = {
            "session": "blue",
            "learning": "green",
            "decision": "yellow",
            "error": "red",
            "commit": "cyan",
            "code": "magenta",
        }
        color = type_colors.get(entry.type, "white")
        
        # Add branch info to title
        branch_info = f" @{entry.branch}" if entry.branch else ""
        
        console.print(Panel(
            entry.content[:500] + ("..." if len(entry.content) > 500 else ""),
            title=f"[{color}]{entry.type}[/]{branch_info} | {entry.timestamp[:10]}",
            border_style=color
        ))


@memory_cmd.command("recall")
@click.argument("topic")
def memory_recall(topic: str):
    """Recall information about a topic.
    
    Returns a formatted summary of relevant memories.
    """
    from up.memory import MemoryManager
    
    manager = MemoryManager()
    result = manager.recall(topic)
    console.print(result)


@memory_cmd.command("stats")
def memory_stats():
    """Show memory statistics including branch info."""
    from up.memory import MemoryManager, _check_chromadb
    
    manager = MemoryManager()
    stats = manager.get_stats()
    
    console.print(Panel.fit(
        "[bold blue]Memory Statistics[/]",
        border_style="blue"
    ))
    
    # Backend info
    backend = stats.get("backend", "json")
    if backend == "chromadb":
        backend_desc = "ChromaDB (semantic search)"
    else:
        backend_desc = "JSON (keyword search)"
    
    console.print(f"\nBackend: [cyan]{backend_desc}[/]")
    console.print(f"Current: [cyan]{stats.get('current_branch', 'unknown')}[/] @ [dim]{stats.get('current_commit', 'unknown')}[/]")
    
    if backend == "json" and not _check_chromadb():
        console.print("[dim]Install chromadb for semantic search: pip install chromadb[/]")
    
    # Stats table
    table = Table(show_header=True)
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right")
    
    table.add_row("Sessions", str(stats.get("sessions", 0)))
    table.add_row("Learnings", str(stats.get("learnings", 0)))
    table.add_row("Decisions", str(stats.get("decisions", 0)))
    table.add_row("Errors", str(stats.get("errors", 0)))
    table.add_row("Commits", str(stats.get("commits", 0)))
    table.add_row("Code Files", str(stats.get("code_files", 0)))
    table.add_row("─" * 10, "─" * 5)
    table.add_row("[bold]Total[/]", f"[bold]{stats.get('total', 0)}[/]")
    
    console.print(table)
    
    # Branch breakdown
    branches = stats.get("branches", {})
    if branches and len(branches) > 1:
        console.print("\n[bold]Knowledge by Branch:[/]")
        branch_table = Table(show_header=True)
        branch_table.add_column("Branch", style="cyan")
        branch_table.add_column("Entries", justify="right")
        
        for branch, count in sorted(branches.items(), key=lambda x: x[1], reverse=True):
            marker = " ←" if branch == stats.get("current_branch") else ""
            branch_table.add_row(f"{branch}{marker}", str(count))
        
        console.print(branch_table)


@memory_cmd.command("branch")
@click.argument("branch_name", required=False)
@click.option("--compare", "-c", help="Compare with another branch")
def memory_branch(branch_name: str, compare: str):
    """Show or compare knowledge by branch.
    
    Shows what learnings, decisions, and errors were recorded on each branch.
    Useful for reviewing what was learned during feature development.
    
    \b
    Examples:
      up memory branch                    # Show current branch knowledge
      up memory branch main               # Show main branch knowledge
      up memory branch feature-x --compare main  # Compare branches
    """
    from up.memory import MemoryManager
    
    manager = MemoryManager()
    git_ctx = manager._get_git_context()
    
    # Default to current branch
    if not branch_name:
        branch_name = git_ctx["branch"]
    
    if compare:
        # Compare two branches
        comparison = manager.compare_branches(branch_name, compare)
        
        console.print(Panel.fit(
            f"[bold]Comparing: {branch_name} vs {compare}[/]",
            border_style="blue"
        ))
        
        # Summary table
        table = Table(show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column(branch_name, justify="right")
        table.add_column(compare, justify="right")
        
        b1 = comparison["branch1"]
        b2 = comparison["branch2"]
        
        table.add_row("Total Entries", str(b1["total"]), str(b2["total"]))
        table.add_row("Learnings", str(b1["learnings"]), str(b2["learnings"]))
        table.add_row("Decisions", str(b1["decisions"]), str(b2["decisions"]))
        
        console.print(table)
        
        # Unique knowledge
        unique_b1 = comparison["unique_to_branch1"]
        unique_b2 = comparison["unique_to_branch2"]
        
        if unique_b1["learnings"] or unique_b1["decisions"]:
            console.print(f"\n[bold green]Unique to {branch_name}:[/]")
            for learning in unique_b1["learnings"][:3]:
                console.print(f"  💡 {learning.content[:60]}...")
            for decision in unique_b1["decisions"][:3]:
                console.print(f"  🎯 {decision.content[:60]}...")
        
        if unique_b2["learnings"] or unique_b2["decisions"]:
            console.print(f"\n[bold yellow]Unique to {compare}:[/]")
            for learning in unique_b2["learnings"][:3]:
                console.print(f"  💡 {learning.content[:60]}...")
            for decision in unique_b2["decisions"][:3]:
                console.print(f"  🎯 {decision.content[:60]}...")
    
    else:
        # Show single branch knowledge
        knowledge = manager.get_branch_knowledge(branch_name)
        
        total = sum(len(v) for v in knowledge.values())
        current_marker = " (current)" if branch_name == git_ctx["branch"] else ""
        
        console.print(Panel.fit(
            f"[bold]Knowledge on branch: {branch_name}{current_marker}[/]",
            border_style="blue"
        ))
        
        if total == 0:
            console.print("[dim]No knowledge recorded on this branch yet.[/]")
            console.print("\n[dim]Knowledge is recorded when you:[/]")
            console.print("  • Use [cyan]up memory record --learning[/]")
            console.print("  • Use [cyan]up memory record --decision[/]")
            console.print("  • Errors occur during [cyan]up start[/]")
            return
        
        console.print(f"\n[bold]Total: {total} entries[/]\n")
        
        for entry_type, entries in knowledge.items():
            if entries:
                icon = {"learnings": "💡", "decisions": "🎯", "errors": "❌", "commits": "📝"}.get(entry_type, "•")
                console.print(f"[bold]{icon} {entry_type.title()} ({len(entries)}):[/]")
                for entry in entries[:3]:
                    preview = entry.content[:70].replace("\n", " ")
                    console.print(f"  • {preview}...")
                if len(entries) > 3:
                    console.print(f"  [dim]...and {len(entries) - 3} more[/]")
                console.print()


@memory_cmd.command("sync")
def memory_sync():
    """Sync memory with current state.
    
    Indexes recent git commits and file changes into memory.
    All entries are tagged with the current branch for version tracking.
    """
    import os
    import warnings
    from up.memory import MemoryManager
    from tqdm import tqdm
    
    # Suppress noisy warnings from tokenizers
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    warnings.filterwarnings("ignore", category=UserWarning)
    
    manager = MemoryManager()
    git_ctx = manager._get_git_context()
    
    console.print(f"[bold]Syncing memory...[/]")
    console.print(f"[dim]Branch: {git_ctx['branch']} @ {git_ctx['commit']}[/]\n")
    
    with tqdm(total=2, desc="Syncing", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}") as pbar:
        pbar.set_description("Indexing commits")
        commits = manager.index_recent_commits(count=20)
        pbar.update(1)
        
        pbar.set_description("Indexing files")
        files = manager.index_file_changes()
        pbar.update(1)
    
    console.print(f"\n[green]✓[/] Indexed [cyan]{commits}[/] commits on [cyan]{git_ctx['branch']}[/]")
    console.print(f"[green]✓[/] Indexed [cyan]{files}[/] files")


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
    from up.memory import MemoryManager
    
    manager = MemoryManager()
    
    if learning:
        manager.record_learning(learning)
        console.print(f"[green]✓[/] Recorded learning: {learning}")
    
    if decision:
        manager.record_decision(decision)
        console.print(f"[green]✓[/] Recorded decision: {decision}")
    
    if error:
        manager.record_error(error, solution)
        console.print(f"[green]✓[/] Recorded error: {error}")
        if solution:
            console.print(f"  Solution: {solution}")
    
    if not any([learning, decision, error]):
        console.print("[yellow]No input provided. Use --learning, --decision, or --error[/]")


@memory_cmd.command("session")
@click.option("--start", is_flag=True, help="Start a new session")
@click.option("--end", is_flag=True, help="End current session")
@click.option("--summary", "-s", help="Summary for session end")
def memory_session(start: bool, end: bool, summary: str):
    """Manage memory sessions.
    
    \b
    Examples:
      up memory session --start
      up memory session --end --summary "Implemented auth feature"
    """
    from up.memory import MemoryManager
    
    manager = MemoryManager()
    
    if start:
        session_id = manager.start_session()
        console.print(f"[green]✓[/] Started session: [cyan]{session_id}[/]")
    
    elif end:
        manager.end_session(summary)
        console.print("[green]✓[/] Session ended and saved to memory")
    
    else:
        # Show current session status
        session_file = manager.workspace / ".up" / "current_session.json"
        if session_file.exists():
            data = json.loads(session_file.read_text())
            console.print(f"Current session: [cyan]{data.get('session_id')}[/]")
            console.print(f"Started: {data.get('started_at')}")
            console.print(f"Tasks: {len(data.get('tasks', []))}")
            console.print(f"Files: {len(data.get('files_modified', []))}")
        else:
            console.print("[dim]No active session. Use --start to begin.[/]")


@memory_cmd.command("list")
@click.option("--type", "-t", "entry_type", 
              type=click.Choice(["session", "learning", "decision", "error", "commit"]),
              help="Filter by type")
@click.option("--limit", "-n", default=10, help="Number of entries")
def memory_list(entry_type: str, limit: int):
    """List recent memory entries.
    
    \b
    Examples:
      up memory list --type learning
      up memory list --type session --limit 5
    """
    from up.memory import MemoryManager
    
    manager = MemoryManager()
    
    if entry_type:
        if entry_type == "session":
            entries = manager.get_recent_sessions(limit)
        elif entry_type == "learning":
            entries = manager.get_learnings(limit)
        elif entry_type == "decision":
            entries = manager.get_decisions(limit)
        elif entry_type == "error":
            entries = manager.get_errors(limit)
        else:
            entries = manager.store.get_by_type(entry_type, limit)
    else:
        # Get all types
        entries = []
        for t in ["session", "learning", "decision", "error", "commit"]:
            entries.extend(manager.store.get_by_type(t, limit // 5 or 2))
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        entries = entries[:limit]
    
    if not entries:
        console.print("[dim]No entries found[/]")
        return
    
    console.print(f"\n[bold]Memory Entries ({len(entries)}):[/]\n")
    
    for entry in entries:
        type_icons = {
            "session": "📅",
            "learning": "💡",
            "decision": "🎯",
            "error": "❌",
            "commit": "📝",
            "code": "💻",
        }
        icon = type_icons.get(entry.type, "•")
        
        content_preview = entry.content[:80].replace("\n", " ")
        if len(entry.content) > 80:
            content_preview += "..."
        
        console.print(f"{icon} [{entry.type}] {content_preview}")
        console.print(f"   [dim]{entry.timestamp[:16]}[/]")
        console.print()


@memory_cmd.command("clear")
@click.confirmation_option(prompt="Are you sure you want to clear all memory?")
def memory_clear():
    """Clear all memory entries."""
    from up.memory import MemoryManager
    
    manager = MemoryManager()
    manager.clear()
    console.print("[green]✓[/] Memory cleared")


@memory_cmd.command("reset")
@click.confirmation_option(prompt="This will delete ALL memory data and re-initialize. Continue?")
def memory_reset():
    """Reset memory database completely.
    
    Use this if you encounter database corruption errors like:
    - "mismatched types" 
    - "InternalError"
    - "Error reading from metadata segment"
    
    This deletes the ChromaDB files and creates a fresh database.
    """
    import shutil
    
    cwd = Path.cwd()
    chroma_dir = cwd / ".up" / "memory" / "chroma"
    json_file = cwd / ".up" / "memory" / "index.json"
    
    deleted = []
    
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        deleted.append("ChromaDB")
    
    if json_file.exists():
        json_file.unlink()
        deleted.append("JSON index")
    
    if deleted:
        console.print(f"[green]✓[/] Deleted: {', '.join(deleted)}")
        console.print("\n[dim]Run 'up memory sync' to rebuild from git history[/]")
    else:
        console.print("[yellow]No memory files found to delete[/]")


@memory_cmd.command("migrate")
def memory_migrate():
    """Migrate JSON memory to ChromaDB.
    
    If you have existing data in .up/memory/index.json from before
    ChromaDB was enabled, this command migrates it to ChromaDB.
    """
    from up.memory import MemoryManager, JSONMemoryStore, MemoryEntry, _check_chromadb
    
    cwd = Path.cwd()
    json_file = cwd / ".up" / "memory" / "index.json"
    
    if not json_file.exists():
        console.print("[yellow]No JSON memory file found. Nothing to migrate.[/]")
        return
    
    if not _check_chromadb():
        console.print("[red]ChromaDB not installed. Install with: pip install chromadb[/]")
        return
    
    # Load JSON data
    console.print("[dim]Loading JSON memory...[/]")
    json_store = JSONMemoryStore(cwd)
    entries = list(json_store.entries.values())
    
    if not entries:
        console.print("[yellow]No entries in JSON memory. Nothing to migrate.[/]")
        return
    
    console.print(f"Found [cyan]{len(entries)}[/] entries to migrate")
    
    # Create ChromaDB manager and migrate
    console.print("[dim]Migrating to ChromaDB (this may take a moment)...[/]")
    manager = MemoryManager(cwd, use_vectors=True)
    
    if manager._backend != "chromadb":
        console.print("[red]Failed to initialize ChromaDB backend[/]")
        return
    
    migrated = 0
    skipped = 0
    for entry in entries:
        try:
            # Clean metadata - convert lists to strings for ChromaDB compatibility
            clean_metadata = {}
            for k, v in entry.metadata.items():
                if isinstance(v, list):
                    clean_metadata[k] = ", ".join(str(x) for x in v) if v else ""
                elif v is not None:
                    clean_metadata[k] = v
            
            # Create clean entry
            clean_entry = MemoryEntry(
                id=entry.id,
                type=entry.type,
                content=entry.content,
                metadata=clean_metadata,
                timestamp=entry.timestamp,
                branch=entry.branch,
                commit=entry.commit,
            )
            
            manager.store.add(clean_entry)
            migrated += 1
        except Exception as e:
            console.print(f"[yellow]Skip {entry.id}: {e}[/]")
            skipped += 1
    
    console.print(f"\n[green]✓[/] Migrated [cyan]{migrated}/{len(entries)}[/] entries to ChromaDB")
    if skipped:
        console.print(f"[yellow]Skipped {skipped} entries (see warnings above)[/]")
    console.print(f"\n[dim]Old JSON file kept at: {json_file}[/]")
    console.print("[dim]You can delete it manually if migration looks good.[/]")


if __name__ == "__main__":
    memory_cmd()
