"""up new - Create a new project with up systems."""

import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from up.templates import scaffold_project

console = Console()


@click.command()
@click.argument("name")
@click.option(
    "--ai",
    type=click.Choice(["claude", "cursor", "both"]),
    default="both",
    help="Target AI assistant",
)
@click.option(
    "--template",
    "-t",
    type=click.Choice(["minimal", "standard", "full"]),
    default="standard",
    help="Project template",
)
def new_cmd(name: str, ai: str, template: str):
    """Create a new project with up systems.

    NAME is the project directory name.
    """
    target = Path.cwd() / name

    if target.exists():
        console.print(f"[red]Error:[/] Directory '{name}' already exists")
        raise SystemExit(1)

    console.print(Panel.fit(
        f"[bold blue]up new[/] - Creating [cyan]{name}[/]",
        border_style="blue"
    ))

    # Create directory
    target.mkdir(parents=True)

    # Determine systems based on template
    systems = _get_systems_for_template(template)

    # Scaffold
    scaffold_project(
        target_dir=target,
        ai_target=ai,
        systems=systems,
        force=True,
    )

    console.print(f"\n[green]✓[/] Project created at [cyan]{target}[/]")
    console.print(f"\n  cd {name}")
    console.print("  up init --help")


def _get_systems_for_template(template: str) -> list:
    """Get systems list based on template."""
    templates = {
        "minimal": ["docs"],
        "standard": ["docs", "learn", "loop"],
        "full": ["docs", "learn", "loop"],
    }
    return templates.get(template, ["docs"])
