"""up init - Initialize up systems in existing project."""

import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from up.templates import scaffold_project

console = Console()


@click.command()
@click.option(
    "--ai",
    type=click.Choice(["claude", "cursor", "both"]),
    default="both",
    help="Target AI assistant (claude, cursor, or both)",
)
@click.option(
    "--systems",
    "-s",
    multiple=True,
    type=click.Choice(["docs", "learn", "loop", "all"]),
    default=["all"],
    help="Systems to initialize",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files",
)
def init_cmd(ai: str, systems: tuple, force: bool):
    """Initialize up systems in the current directory."""
    cwd = Path.cwd()

    console.print(Panel.fit(
        f"[bold blue]up init[/] - Initializing in [cyan]{cwd.name}[/]",
        border_style="blue"
    ))

    # Determine which systems to install
    if "all" in systems:
        systems = ("docs", "learn", "loop")

    # Run scaffolding
    scaffold_project(
        target_dir=cwd,
        ai_target=ai,
        systems=list(systems),
        force=force,
    )

    console.print("\n[green]✓[/] Initialization complete!")
    _print_next_steps(systems)


def _print_next_steps(systems: tuple):
    """Print next steps after initialization."""
    console.print("\n[bold]Next steps:[/]")

    if "docs" in systems:
        console.print("  • Edit [cyan]docs/roadmap/vision/PRODUCT_VISION.md[/]")

    if "learn" in systems:
        console.print("  • Run [cyan]/learn auto[/] to analyze your project")

    if "loop" in systems:
        console.print("  • Run [cyan]/product-loop[/] to start development")
