"""up summarize - Summarize AI conversation history."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command()
@click.option(
    "--format", "-f",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output file path",
)
@click.option(
    "--project", "-p",
    help="Filter by project path",
)
@click.option(
    "--source",
    type=click.Choice(["cursor", "claude", "all"]),
    default="cursor",
    help="Conversation source to analyze",
)
def summarize_cmd(format: str, output: str, project: str, source: str):
    """Summarize AI conversation history.
    
    Analyzes your Cursor or Claude chat history to extract:
    - Common topics and patterns
    - Frequent errors encountered
    - Actionable insights
    - Code snippets
    
    \b
    Examples:
      up summarize                     # Markdown to stdout
      up summarize -f json -o out.json # JSON to file
      up summarize -p myproject        # Filter by project
    """
    console.print(Panel.fit(
        "[bold blue]Conversation Summarizer[/]",
        border_style="blue"
    ))
    
    try:
        if source in ("cursor", "all"):
            result = _summarize_cursor(format, project)
            _output_result(result, output, format)
        
        if source == "claude":
            console.print("[yellow]Claude history summarization not yet implemented.[/]")
            console.print("Use [cyan]--source cursor[/] for Cursor history.")
            
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/] {e}")
        console.print("\nMake sure Cursor is installed and has chat history.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)


def _summarize_cursor(format: str, project_filter: str = None) -> str:
    """Summarize Cursor conversation history."""
    # Add scripts to path
    scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
    if scripts_path.exists():
        sys.path.insert(0, str(scripts_path))
    
    try:
        from export_cursor_history import load_all_data
    except ImportError:
        raise FileNotFoundError(
            "Could not import export_cursor_history. "
            "Make sure scripts/export_cursor_history.py exists."
        )
    
    from up.summarizer import ConversationSummarizer
    
    console.print("Loading Cursor history...", style="dim")
    conversations = load_all_data(project_filter=project_filter)
    
    if not conversations:
        raise ValueError("No conversations found in Cursor history.")
    
    console.print(f"Found [cyan]{len(conversations)}[/] conversations")
    console.print("Analyzing...", style="dim")
    
    summarizer = ConversationSummarizer(conversations)
    
    if format == "json":
        return summarizer.to_json()
    return summarizer.to_markdown()


def _output_result(result: str, output_path: str, format: str) -> None:
    """Output result to file or stdout."""
    if output_path:
        Path(output_path).write_text(result)
        console.print(f"\n[green]✓[/] Summary saved to [cyan]{output_path}[/]")
    else:
        console.print("\n")
        if format == "markdown":
            # Use rich markdown rendering
            from rich.markdown import Markdown
            console.print(Markdown(result))
        else:
            console.print(result)


if __name__ == "__main__":
    summarize_cmd()
