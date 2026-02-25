"""up sync config - Generate AI assistant config files from plugins.

Runs all renderers and writes CLAUDE.md, .cursorrules, .claude/settings.json.
Shows diff of changes before writing.
"""

import json
from pathlib import Path

import click
from rich.console import Console

from up.plugins.registry import PluginRegistry
from up.sync.renderer import build_context, ConfigRenderer
from up.sync.claude_md import ClaudeMdRenderer
from up.sync.cursorrules import CursorrulesRenderer
from up.sync.claude_settings import ClaudeSettingsRenderer

console = Console()

# Target name -> renderer mapping
TARGET_MAP = {
    "claude-md": ClaudeMdRenderer,
    "cursorrules": CursorrulesRenderer,
    "claude-settings": ClaudeSettingsRenderer,
}


def _resolve_path(workspace: Path, renderer: ConfigRenderer) -> Path:
    """Resolve the output path for a renderer."""
    return workspace / renderer.filename


def _show_diff(old: str, new: str, filename: str) -> None:
    """Show a Rich-formatted diff between old and new content."""
    import difflib

    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile=filename, tofile=filename)

    for line in diff:
        line = line.rstrip("\n")
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"[red]{line}[/red]")
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/cyan]")
        else:
            console.print(f"[dim]{line}[/dim]")


def run_sync(
    workspace: Path,
    dry_run: bool = False,
    targets: list[str] | None = None,
) -> dict:
    """Run config sync and return results.

    Args:
        workspace: Project root directory.
        dry_run: If True, preview without writing.
        targets: Optional list of target names to generate.

    Returns:
        Dict with 'written', 'skipped', 'plugins' counts.
    """
    # Load config
    config_path = workspace / ".up" / "config.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    # Load plugins
    reg = PluginRegistry(workspace)
    reg.load()
    plugins = reg.get_enabled()

    # Build context
    if not config.get("project", {}).get("name"):
        config.setdefault("project", {})["name"] = workspace.name
    ctx = build_context(config, plugins)

    # Select renderers
    if targets:
        renderer_classes = [
            TARGET_MAP[t] for t in targets if t in TARGET_MAP
        ]
    else:
        renderer_classes = list(TARGET_MAP.values())

    written = 0
    skipped = 0

    for cls in renderer_classes:
        renderer = cls()
        out_path = _resolve_path(workspace, renderer)

        # For claude settings, use merge mode
        if isinstance(renderer, ClaudeSettingsRenderer) and out_path.exists():
            new_content = renderer.render_merged(ctx, out_path)
        else:
            new_content = renderer.render(ctx)

        # Read existing
        old_content = ""
        if out_path.exists():
            old_content = out_path.read_text()

        # Skip unchanged
        if old_content == new_content:
            skipped += 1
            continue

        # Show diff
        _show_diff(old_content, new_content, renderer.filename)

        # Write unless dry run
        if not dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(new_content)
            written += 1
        else:
            written += 1  # count as "would write"

    return {"written": written, "skipped": skipped, "plugins": len(plugins)}


@click.command("sync-config")
@click.option("--dry-run", is_flag=True, help="Preview changes without writing")
@click.option(
    "--target", "targets",
    multiple=True,
    type=click.Choice(list(TARGET_MAP.keys())),
    help="Generate only specific files",
)
def sync_config_cmd(dry_run: bool, targets: tuple):
    """Generate AI config files from plugins.

    Renders CLAUDE.md, .cursorrules, and .claude/settings.json
    from .up/config.json and installed plugins.

    \b
    Examples:
      up sync-config                    # Generate all config files
      up sync-config --dry-run          # Preview without writing
      up sync-config --target claude-md # Only generate CLAUDE.md
    """
    workspace = Path.cwd()

    if dry_run:
        console.print("[dim]Dry run — no files will be written[/dim]\n")

    target_list = list(targets) if targets else None
    result = run_sync(workspace, dry_run=dry_run, targets=target_list)

    console.print()
    if dry_run:
        console.print(
            f"[yellow]Would sync {result['written']} file(s) "
            f"from {result['plugins']} plugin(s)[/yellow]"
        )
    else:
        console.print(
            f"[green]Synced {result['written']} file(s) "
            f"from {result['plugins']} plugin(s)[/green]"
        )
    if result["skipped"]:
        console.print(f"[dim]{result['skipped']} file(s) unchanged[/dim]")
