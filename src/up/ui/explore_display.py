"""Rich terminal UI for explore comparison results.

Displays a side-by-side comparison of exploration strategies
with key metrics and prompts the user to select an approach.
"""

from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class ExploreChoice(Enum):
    """User's selection after viewing the comparison."""

    STRATEGY_1 = "1"
    STRATEGY_2 = "2"
    STRATEGY_3 = "3"
    COMBINE = "combine"
    NONE = "none"


def _status(ok: bool) -> str:
    return "[green]pass[/]" if ok else "[red]fail[/]"


def display_comparison(comparison, results=None) -> ExploreChoice:
    """Display a Rich table comparing exploration results and prompt for selection.

    Args:
        comparison: ExploreComparison from ExploreAnalyzer.
        results: Optional list of ExploreResult for diff previews.

    Returns:
        ExploreChoice selected by the user.
    """
    table = Table(title="Exploration Results", show_lines=True)
    table.add_column("#", style="bold", width=3)
    table.add_column("Strategy", style="cyan")
    table.add_column("Files Changed", justify="right")
    table.add_column("Lines +/-", justify="right")
    table.add_column("Tests")
    table.add_column("Lint")

    for i, s in enumerate(comparison.strategies, 1):
        diff_str = f"+{s.lines_added}/-{s.lines_removed}"
        table.add_row(
            str(i),
            s.strategy_name,
            str(s.files_changed_count),
            diff_str,
            _status(s.tests_passed),
            _status(s.lint_passed),
        )

    console.print()
    console.print(table)

    if comparison.recommendation:
        console.print(
            f"\n[dim]Recommendation: [bold]{comparison.recommendation}[/bold] "
            f"(smallest passing diff)[/dim]"
        )

    # Diff previews
    if results:
        for r in results:
            if not r.success:
                continue
            preview = _get_diff_preview(r.worktree_path)
            if preview:
                console.print(Panel(
                    preview,
                    title=f"[cyan]{r.strategy_name}[/] diff preview",
                    border_style="dim",
                    expand=False,
                ))

    return _prompt_selection(len(comparison.strategies))


def _get_diff_preview(worktree: Path, max_lines: int = 20) -> str:
    """Return a truncated diff preview for a worktree."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1"],
            capture_output=True, text=True, cwd=worktree,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            if len(lines) > max_lines:
                lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines)"]
            return "\n".join(lines)
    except Exception:
        pass
    return ""


def _prompt_selection(count: int) -> ExploreChoice:
    """Prompt the user to select an approach."""
    valid = [str(i) for i in range(1, count + 1)] + ["combine", "none"]
    prompt_str = f"Which approach? [{'/'.join(str(i) for i in range(1, count + 1))}/combine/none]: "

    while True:
        choice = console.input(f"\n[bold]{prompt_str}[/]").strip().lower()
        if choice in valid:
            return ExploreChoice(choice)
        console.print(f"[yellow]Invalid choice. Options: {', '.join(valid)}[/]")
