"""up done - Mark tasks as completed.

When working manually in Cursor or another editor, use this command
to mark tasks as done so `up start` doesn't re-run them.
"""

import json
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from up.core.state import get_state_manager
from up.commands.start.helpers import find_task_source

console = Console()


@click.command("done")
@click.argument("task_ids", nargs=-1, required=False)
@click.option("--list", "list_tasks", is_flag=True, help="List pending tasks")
@click.option("--sync", "sync_mode", is_flag=True, help="Sync PRD with state (auto-mark completed)")
@click.option("--prd", "-p", type=click.Path(exists=True), help="Path to PRD file")
def done_cmd(task_ids: tuple, list_tasks: bool, sync_mode: bool, prd: str):
    """Mark tasks as completed.

    Use this when you implement tasks manually (e.g., in Cursor)
    so `up start --parallel` doesn't re-run them.

    \\b
    Examples:
      up done US-001 US-002        # Mark specific tasks as done
      up done --list               # Show pending tasks
      up done --sync               # Auto-sync PRD with state
    """
    cwd = Path.cwd()
    task_source = prd or find_task_source(cwd)

    if not task_source:
        console.print("[red]No PRD file found[/]")
        console.print("Specify with: [cyan]up done --prd path/to/prd.json[/]")
        return

    prd_path = cwd / task_source

    if not prd_path.exists():
        console.print(f"[red]PRD file not found:[/] {prd_path}")
        return

    try:
        data = json.loads(prd_path.read_text())
        stories = data.get("userStories", [])
    except json.JSONDecodeError:
        console.print("[red]Invalid PRD JSON[/]")
        return

    # List mode
    if list_tasks:
        _list_pending(stories, prd_path)
        return

    # Sync mode - cross-check state with PRD
    if sync_mode:
        _sync_state_with_prd(cwd, stories, data, prd_path)
        return

    # Mark specific tasks as done
    if not task_ids:
        console.print("[yellow]Specify task IDs to mark as done[/]")
        console.print("Usage: [cyan]up done US-001 US-002[/]")
        console.print("Or:    [cyan]up done --list[/] to see pending tasks")
        return

    sm = get_state_manager(cwd)
    marked = 0

    for task_id in task_ids:
        found = False
        for story in stories:
            if story.get("id") == task_id:
                found = True
                if story.get("passes", False):
                    console.print(f"  [dim]{task_id}: already done[/]")
                else:
                    story["passes"] = True
                    story["completedAt"] = time.strftime("%Y-%m-%d")
                    sm.record_task_complete(task_id)
                    console.print(f"  [green]✓[/] {task_id}: marked as done")
                    marked += 1
                break
        if not found:
            console.print(f"  [red]✗[/] {task_id}: not found in PRD")

    if marked > 0:
        prd_path.write_text(json.dumps(data, indent=2))
        console.print(f"\n[green]{marked} task(s) marked as done[/]")

    # Show remaining
    pending = [s for s in stories if not s.get("passes", False)]
    console.print(f"[dim]Remaining: {len(pending)} tasks[/]")


def _list_pending(stories: list, prd_path: Path):
    """List pending tasks."""
    pending = [s for s in stories if not s.get("passes", False)]
    completed = [s for s in stories if s.get("passes", False)]

    if not pending:
        console.print("[green]All tasks complete![/]")
        return

    table = Table(title=f"Pending Tasks ({len(pending)}/{len(stories)})")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Priority")
    table.add_column("Effort")

    for task in pending:
        table.add_row(
            task.get("id", "?"),
            (task.get("title", "")[:50] + "...") if len(task.get("title", "")) > 50 else task.get("title", ""),
            task.get("priority", "?"),
            task.get("effort", "?"),
        )

    console.print(table)
    console.print(f"\nMark done: [cyan]up done {pending[0].get('id')}[/]")


def _sync_state_with_prd(workspace: Path, stories: list, data: dict, prd_path: Path):
    """Sync state.tasks_completed with PRD passes field."""
    sm = get_state_manager(workspace)
    completed_in_state = set(sm.state.loop.tasks_completed)

    synced = 0
    for story in stories:
        task_id = story.get("id", "")
        prd_done = story.get("passes", False)
        state_done = task_id in completed_in_state

        if state_done and not prd_done:
            # State says done, PRD says not — update PRD
            story["passes"] = True
            story["completedAt"] = story.get("completedAt", time.strftime("%Y-%m-%d"))
            console.print(f"  [green]✓[/] {task_id}: synced (state -> PRD)")
            synced += 1
        elif prd_done and not state_done:
            # PRD says done, state doesn't know — update state
            sm.record_task_complete(task_id)
            console.print(f"  [green]✓[/] {task_id}: synced (PRD -> state)")
            synced += 1

    if synced > 0:
        prd_path.write_text(json.dumps(data, indent=2))
        console.print(f"\n[green]Synced {synced} task(s)[/]")
    else:
        console.print("[green]PRD and state are already in sync[/]")

    pending = [s for s in stories if not s.get("passes", False)]
    console.print(f"[dim]Pending: {len(pending)} tasks[/]")
