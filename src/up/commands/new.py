"""up new - Create a new project with up systems."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from up.templates import scaffold_project
from up.templates.projects import get_available_templates, create_project_from_template

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
    type=click.Choice(["minimal", "standard", "full", "fastapi", "nextjs", "python-lib"]),
    default="standard",
    help="Project template",
)
@click.option(
    "--list-templates",
    is_flag=True,
    help="List available templates",
)
def new_cmd(name: str, ai: str, template: str, list_templates: bool):
    """Create a new project with up systems.

    NAME is the project directory name.
    
    \b
    Templates:
      minimal      Basic structure with docs only
      standard     Full up systems (docs, learn, loop)
      full         Everything including MCP
      fastapi      FastAPI backend template
      nextjs       Next.js frontend template
      python-lib   Python library template
    """
    if list_templates:
        _show_templates()
        return
    
    target = Path.cwd() / name

    if target.exists():
        console.print(f"[red]Error:[/] Directory '{name}' already exists")
        raise SystemExit(1)

    console.print(Panel.fit(
        f"[bold blue]up new[/] - Creating [cyan]{name}[/] ({template})",
        border_style="blue"
    ))

    # Create directory
    target.mkdir(parents=True)

    # Check if it's a project-type template
    project_templates = ["fastapi", "nextjs", "python-lib"]
    
    if template in project_templates:
        # Create project from template first
        console.print(f"  [dim]Creating {template} project structure...[/]")
        create_project_from_template(target, template, name, force=True)
        
        # Then add up systems
        systems = ["docs", "learn", "loop"]
        console.print("  [dim]Adding up systems...[/]")
    else:
        # Determine systems based on template
        systems = _get_systems_for_template(template)

    # Scaffold up systems
    scaffold_project(
        target_dir=target,
        ai_target=ai,
        systems=systems,
        force=True,
    )

    console.print(f"\n[green]✓[/] Project created at [cyan]{target}[/]")
    _print_next_steps(name, template)


def _get_systems_for_template(template: str) -> list:
    """Get systems list based on template."""
    templates = {
        "minimal": ["docs"],
        "standard": ["docs", "learn", "loop"],
        "full": ["docs", "learn", "loop", "mcp"],
    }
    return templates.get(template, ["docs"])


def _show_templates():
    """Show available templates."""
    console.print("\n[bold]Available Templates[/]\n")
    
    table = Table()
    table.add_column("Template", style="cyan")
    table.add_column("Description")
    table.add_column("Systems")
    
    table.add_row(
        "minimal",
        "Basic structure with documentation",
        "docs"
    )
    table.add_row(
        "standard",
        "Full up systems (default)",
        "docs, learn, loop"
    )
    table.add_row(
        "full",
        "Everything including MCP server",
        "docs, learn, loop, mcp"
    )
    table.add_row(
        "fastapi",
        "FastAPI backend with SQLAlchemy",
        "fastapi + all systems"
    )
    table.add_row(
        "nextjs",
        "Next.js frontend with TypeScript",
        "nextjs + all systems"
    )
    table.add_row(
        "python-lib",
        "Python library with packaging",
        "lib + all systems"
    )
    
    console.print(table)
    
    console.print("\n[bold]Usage:[/]")
    console.print("  up new my-project --template fastapi")
    console.print("  up new my-app -t nextjs")


def _print_next_steps(name: str, template: str):
    """Print next steps after creation."""
    console.print(f"\n  cd {name}")
    
    if template == "fastapi":
        console.print("  pip install -e .[dev]")
        console.print("  uvicorn src.{name}.main:app --reload".replace("{name}", name.replace("-", "_")))
    elif template == "nextjs":
        console.print("  npm install")
        console.print("  npm run dev")
    elif template == "python-lib":
        console.print("  pip install -e .[dev]")
        console.print("  pytest")
    else:
        console.print("  up status")
    
    console.print("\n[bold]Available commands:[/]")
    console.print("  up status       Show system health")
    console.print("  up learn auto   Analyze project")
