"""up plugin - Plugin management commands.

Commands:
- up plugin list: Show all plugins and their status
- up plugin enable <name>: Enable a plugin
- up plugin disable <name>: Disable a plugin
- up plugin create <name>: Scaffold a new plugin
"""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from up.plugins.registry import PluginRegistry

console = Console()


def _get_registry() -> PluginRegistry:
    """Load the plugin registry for the current workspace."""
    reg = PluginRegistry(Path.cwd())
    reg.load()
    return reg


@click.group("plugin")
def plugin_group():
    """Manage plugins."""
    pass


@plugin_group.command("list")
def list_cmd():
    """Show all plugins and their status."""
    reg = _get_registry()
    entries = reg.get_all_entries()

    if not entries:
        console.print("[dim]No plugins found.[/dim]")
        return

    table = Table(title="Plugins")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Category")
    table.add_column("Components")

    for entry in entries:
        plugin = reg.get_plugin(entry.name)
        status = "[green]enabled[/green]" if entry.enabled else "[dim]disabled[/dim]"
        category = ""
        components = ""

        if plugin:
            category = plugin.manifest.category.value
            c = plugin.components
            parts = []
            if c.commands:
                parts.append(f"cmd:{len(c.commands)}")
            if c.hooks:
                parts.append(f"hook:{len(c.hooks)}")
            if c.rules:
                parts.append(f"rule:{len(c.rules)}")
            components = " ".join(parts)

        table.add_row(
            entry.name,
            entry.version,
            status,
            category,
            components,
        )

    console.print(table)


@plugin_group.command("enable")
@click.argument("name")
def enable_cmd(name: str):
    """Enable a disabled plugin."""
    reg = _get_registry()
    if reg.enable(name):
        reg.save()
        console.print(f"[green]Enabled plugin '{name}'[/green]")
    else:
        console.print(f"[red]Plugin '{name}' not found.[/red]")
        console.print("[dim]Run 'up plugin list' to see available plugins.[/dim]")


@plugin_group.command("disable")
@click.argument("name")
def disable_cmd(name: str):
    """Disable an enabled plugin."""
    reg = _get_registry()
    if reg.disable(name):
        reg.save()
        console.print(f"[yellow]Disabled plugin '{name}'[/yellow]")
    else:
        console.print(f"[red]Plugin '{name}' not found.[/red]")
        console.print("[dim]Run 'up plugin list' to see available plugins.[/dim]")


@plugin_group.command("create")
@click.argument("name")
def create_cmd(name: str):
    """Scaffold a new plugin directory."""
    from up.plugins.manifest import KEBAB_CASE_RE

    if not KEBAB_CASE_RE.match(name):
        console.print(f"[red]Invalid plugin name '{name}'. Must be kebab-case.[/red]")
        return

    workspace = Path.cwd()
    plugin_dir = workspace / ".up" / "plugins" / "installed" / name

    if plugin_dir.exists():
        console.print(f"[red]Plugin '{name}' already exists.[/red]")
        return

    # Create directory structure
    plugin_dir.mkdir(parents=True)
    for subdir in ("commands", "hooks", "rules"):
        (plugin_dir / subdir).mkdir()

    # Write plugin.json
    manifest = {
        "name": name,
        "version": "0.1.0",
        "description": "",
        "author": "",
        "category": "productivity",
    }
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )

    # Write README
    readme = f"# {name}\n\nA custom UP plugin.\n\n"
    readme += "## Directories\n\n"
    readme += "- `commands/` — Markdown command definitions\n"
    readme += "- `hooks/` — Hook scripts and hooks.json\n"
    readme += "- `rules/` — Markdown rule definitions\n"
    (plugin_dir / "README.md").write_text(readme)

    # Auto-register in registry
    reg = _get_registry()
    reg.save()

    console.print(f"[green]Created plugin '{name}'[/green]")
    console.print(f"[dim]  {plugin_dir}[/dim]")


@plugin_group.command("install")
@click.argument("path", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="Overwrite existing plugin")
def install_cmd(path: str, force: bool):
    """Install a plugin from a local path."""
    import shutil

    source = Path(path).resolve()
    manifest_path = source / "plugin.json"

    if not manifest_path.exists():
        console.print(f"[red]No plugin.json found in {source}[/red]")
        return

    # Validate manifest
    from up.plugins.manifest import PluginManifest, ManifestValidationError
    try:
        manifest = PluginManifest.from_json(manifest_path)
    except ManifestValidationError as e:
        console.print(f"[red]Invalid plugin manifest: {e}[/red]")
        return

    workspace = Path.cwd()
    dest = workspace / ".up" / "plugins" / "installed" / manifest.name

    if dest.exists() and not force:
        console.print(f"[red]Plugin '{manifest.name}' already installed.[/red]")
        console.print("[dim]Use --force to overwrite.[/dim]")
        return

    # Copy plugin directory
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)

    # Register
    reg = _get_registry()
    reg.save()

    # Show summary
    from up.plugins.loader import _discover_components
    components = _discover_components(dest)
    parts = []
    if components.hooks:
        parts.append(f"{len(components.hooks)} hooks")
    if components.rules:
        parts.append(f"{len(components.rules)} rules")
    if components.commands:
        parts.append(f"{len(components.commands)} commands")

    console.print(f"[green]Installed plugin '{manifest.name}' v{manifest.version}[/green]")
    if parts:
        console.print(f"[dim]  Components: {', '.join(parts)}[/dim]")
