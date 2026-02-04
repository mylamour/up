"""up bisect - Automated bug hunting with git bisect.

Finds the commit that introduced a bug using binary search.
Runs in O(log n) steps regardless of history length.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _is_git_repo(path: Path) -> bool:
    """Check if path is a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=path,
        capture_output=True
    )
    return result.returncode == 0


def _get_last_tag(path: Path) -> Optional[str]:
    """Get most recent tag."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=path,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _get_commit_info(path: Path, commit: str) -> dict:
    """Get information about a commit."""
    format_str = "%H%n%an%n%ae%n%ad%n%s"
    result = subprocess.run(
        ["git", "log", "-1", f"--format={format_str}", commit],
        cwd=path,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        return {}
    
    lines = result.stdout.strip().split("\n")
    if len(lines) < 5:
        return {}
    
    return {
        "sha": lines[0],
        "author": lines[1],
        "email": lines[2],
        "date": lines[3],
        "message": lines[4],
    }


def _get_diff(path: Path, commit: str) -> str:
    """Get diff for a commit."""
    result = subprocess.run(
        ["git", "show", "--stat", commit],
        cwd=path,
        capture_output=True,
        text=True
    )
    return result.stdout if result.returncode == 0 else ""


@click.command("bisect")
@click.option("--test", "-t", "test_cmd", help="Test command to run (exit 0 = good, 1 = bad)")
@click.option("--good", "-g", help="Known good commit (default: last tag or HEAD~50)")
@click.option("--bad", "-b", default="HEAD", help="Known bad commit (default: HEAD)")
@click.option("--script", "-s", type=click.Path(exists=True), help="Path to test script")
@click.option("--start", is_flag=True, help="Start interactive bisect session")
@click.option("--reset", is_flag=True, help="Reset/abort current bisect")
def bisect_cmd(test_cmd: str, good: str, bad: str, script: str, start: bool, reset: bool):
    """Find the commit that introduced a bug.
    
    Uses binary search through Git history to find the exact commit
    that introduced a bug. Runs in O(log n) steps.
    
    \b
    Examples:
      up bisect --test "pytest tests/auth.py"
      up bisect --script ./test_regression.sh
      up bisect --good v1.0.0 --bad HEAD --test "npm test"
      up bisect --start              # Interactive mode
      up bisect --reset              # Abort bisect
    
    \b
    Test Script Requirements:
      - Exit 0: Bug NOT present (good commit)
      - Exit 1: Bug IS present (bad commit)
      - Exit 125: Skip this commit (can't test)
    """
    cwd = Path.cwd()
    
    if not _is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        sys.exit(1)
    
    # Reset mode
    if reset:
        result = subprocess.run(
            ["git", "bisect", "reset"],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            console.print("[green]✓[/] Bisect session reset")
        else:
            console.print("[yellow]No bisect session active[/]")
        return
    
    # Interactive start mode
    if start:
        _start_interactive_bisect(cwd, good, bad)
        return
    
    # Need test command or script
    if not test_cmd and not script:
        console.print("[yellow]Provide a test command or script[/]")
        console.print("\nUsage:")
        console.print('  up bisect --test "pytest tests/auth.py"')
        console.print("  up bisect --script ./test_regression.sh")
        console.print("  up bisect --start  # Interactive mode")
        return
    
    # Determine good commit
    if not good:
        # Try last tag
        good = _get_last_tag(cwd)
        if not good:
            # Fall back to N commits ago
            good = "HEAD~50"
        console.print(f"[dim]Using good commit: {good}[/]")
    
    # Build test script
    if script:
        test_script = Path(script).read_text()
    else:
        test_script = f"""#!/bin/bash
# Auto-generated bisect test script

# Run the test command
{test_cmd}
exit $?
"""
    
    # Write test script
    script_path = cwd / ".bisect_test.sh"
    script_path.write_text(test_script)
    script_path.chmod(0o755)
    
    console.print(Panel.fit(
        f"[bold]Git Bisect - Bug Hunter[/]\n\n"
        f"Good: {good}\n"
        f"Bad: {bad}\n"
        f"Test: {test_cmd or script}",
        border_style="blue"
    ))
    
    try:
        # Start bisect
        console.print("\n[dim]Starting bisect...[/]")
        
        subprocess.run(["git", "bisect", "start"], cwd=cwd, capture_output=True)
        subprocess.run(["git", "bisect", "bad", bad], cwd=cwd, capture_output=True)
        
        result = subprocess.run(
            ["git", "bisect", "good", good],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            console.print(f"[red]Error:[/] Failed to set good commit")
            console.print(f"[dim]{result.stderr}[/]")
            subprocess.run(["git", "bisect", "reset"], cwd=cwd, capture_output=True)
            return
        
        # Run automated bisect
        console.print("[dim]Running automated bisect (this may take a while)...[/]")
        console.print()
        
        result = subprocess.run(
            ["git", "bisect", "run", str(script_path)],
            cwd=cwd,
            capture_output=True,
            text=True
        )
        
        # Parse result to find culprit
        output = result.stdout + result.stderr
        
        # Look for the culprit commit
        culprit = None
        for line in output.split("\n"):
            if "is the first bad commit" in line:
                # Extract commit SHA
                parts = line.split()
                if parts:
                    culprit = parts[0]
                break
        
        if culprit:
            _display_culprit(cwd, culprit)
        else:
            console.print("[yellow]Could not determine culprit commit[/]")
            console.print("[dim]Bisect output:[/]")
            console.print(output[-500:] if len(output) > 500 else output)
        
        # Reset bisect
        subprocess.run(["git", "bisect", "reset"], cwd=cwd, capture_output=True)
        
    finally:
        # Cleanup
        if script_path.exists():
            script_path.unlink()


def _start_interactive_bisect(cwd: Path, good: str, bad: str):
    """Start an interactive bisect session."""
    
    if not good:
        good = _get_last_tag(cwd) or "HEAD~20"
    
    console.print(Panel.fit(
        "[bold]Interactive Bisect Session[/]\n\n"
        "You'll be guided through testing commits.\n"
        "For each commit, run your test and mark as good/bad.",
        border_style="blue"
    ))
    
    # Start bisect
    subprocess.run(["git", "bisect", "start"], cwd=cwd, capture_output=True)
    subprocess.run(["git", "bisect", "bad", bad], cwd=cwd, capture_output=True)
    result = subprocess.run(
        ["git", "bisect", "good", good],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    
    console.print(f"\n[dim]Bisect started: good={good}, bad={bad}[/]")
    console.print("\n[bold]Commands:[/]")
    console.print("  [cyan]git bisect good[/]  - Mark current commit as good")
    console.print("  [cyan]git bisect bad[/]   - Mark current commit as bad")
    console.print("  [cyan]git bisect skip[/]  - Skip current commit")
    console.print("  [cyan]up bisect --reset[/] - Abort bisect")
    console.print("\n[dim]Run your test, then mark the commit.[/]")


def _display_culprit(cwd: Path, commit: str):
    """Display information about the culprit commit."""
    info = _get_commit_info(cwd, commit)
    
    console.print(Panel.fit(
        f"[bold red]🐛 Bug-Introducing Commit Found![/]",
        border_style="red"
    ))
    console.print()
    
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")
    
    table.add_row("Commit", f"[cyan]{info.get('sha', commit)[:12]}[/]")
    table.add_row("Author", info.get('author', 'Unknown'))
    table.add_row("Date", info.get('date', 'Unknown'))
    table.add_row("Message", info.get('message', 'No message'))
    
    console.print(table)
    
    # Show diff stats
    diff = _get_diff(cwd, commit)
    if diff:
        console.print("\n[bold]Changes in this commit:[/]")
        # Only show the stat part
        lines = diff.split("\n")
        for line in lines:
            if line.startswith(" ") and ("|" in line or "changed" in line):
                console.print(f"  {line}")
    
    console.print("\n[bold]Next steps:[/]")
    console.print(f"  1. View full diff: [cyan]git show {commit[:8]}[/]")
    console.print(f"  2. Check this commit: [cyan]git checkout {commit[:8]}[/]")
    console.print(f"  3. Revert if needed: [cyan]git revert {commit[:8]}[/]")


# Also add a 'history' command for viewing commit history with context

@click.command("history")
@click.option("--limit", "-n", default=20, help="Number of commits to show")
@click.option("--since", help="Show commits since date/ref")
@click.option("--author", help="Filter by author")
@click.option("--grep", "grep_pattern", help="Filter by message pattern")
def history_cmd(limit: int, since: str, author: str, grep_pattern: str):
    """Show commit history with context.
    
    Displays recent commits with author, date, and message.
    Useful for finding commits to bisect from.
    """
    cwd = Path.cwd()
    
    if not _is_git_repo(cwd):
        console.print("[red]Error:[/] Not a git repository")
        return
    
    # Build git log command
    cmd = ["git", "log", f"-{limit}", "--pretty=format:%h|%an|%ar|%s"]
    
    if since:
        cmd.append(f"--since={since}")
    if author:
        cmd.append(f"--author={author}")
    if grep_pattern:
        cmd.append(f"--grep={grep_pattern}")
    
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if result.returncode != 0:
        console.print("[red]Error:[/] Failed to get history")
        return
    
    table = Table(title=f"Recent Commits (last {limit})")
    table.add_column("SHA", style="cyan")
    table.add_column("Author")
    table.add_column("When")
    table.add_column("Message")
    
    for line in result.stdout.strip().split("\n"):
        if "|" in line:
            parts = line.split("|", 3)
            if len(parts) >= 4:
                table.add_row(parts[0], parts[1], parts[2], parts[3][:50])
    
    console.print(table)
