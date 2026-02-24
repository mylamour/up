"""up plugin - Plugin management commands.

Commands:
- up plugin list: Show all plugins and their status
- up plugin enable <name>: Enable a plugin
- up plugin disable <name>: Disable a plugin
"""

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
