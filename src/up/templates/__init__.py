"""Templates module for up scaffolding."""

from pathlib import Path
from rich.console import Console

console = Console()


def scaffold_project(
    target_dir: Path,
    ai_target: str,
    systems: list,
    force: bool = False,
) -> None:
    """Scaffold a project with selected systems."""
    from up.templates.docs import create_docs_system
    from up.templates.learn import create_learn_system
    from up.templates.loop import create_loop_system
    from up.templates.docs_skill import create_docs_skill
    from up.templates.config import create_config_files
    from up.templates.mcp import create_mcp_config
    from up.context import create_context_budget_file

    # Create base structure
    _create_base_structure(target_dir, ai_target)

    # Create config files (CLAUDE.md, .cursor/rules/, etc.)
    create_config_files(target_dir, ai_target, force)

    # Create context budget tracking
    if ai_target in ("claude", "both"):
        console.print("  [dim]Creating context budget tracking...[/]")
        create_context_budget_file(target_dir)

    # Create selected systems
    if "docs" in systems:
        console.print("  [dim]Creating docs system...[/]")
        create_docs_system(target_dir, force)
        create_docs_skill(target_dir, ai_target, force)

    if "learn" in systems:
        console.print("  [dim]Creating learn system...[/]")
        create_learn_system(target_dir, ai_target, force)

    if "loop" in systems:
        console.print("  [dim]Creating product-loop system...[/]")
        create_loop_system(target_dir, ai_target, force)

    if "mcp" in systems:
        console.print("  [dim]Creating MCP configuration...[/]")
        create_mcp_config(target_dir, ai_target, force)

    # Create handoff file
    _create_handoff_file(target_dir, force)


def _create_base_structure(target_dir: Path, ai_target: str) -> None:
    """Create base directory structure."""
    dirs = ["src", "tests", "docs"]

    # AI-specific directories
    if ai_target in ("claude", "both"):
        dirs.append(".claude/skills")
    if ai_target in ("cursor", "both"):
        dirs.append(".cursor/rules")

    for d in dirs:
        (target_dir / d).mkdir(parents=True, exist_ok=True)


def _create_handoff_file(target_dir: Path, force: bool) -> None:
    """Create initial handoff file for session continuity."""
    from datetime import date
    
    handoff_dir = target_dir / "docs/handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    
    content = f"""# Latest Session Handoff

**Date**: {date.today().isoformat()}
**Status**: 🟢 Ready

---

## Session Summary

Project initialized with up-cli.

## What Was Done

- Initialized project structure
- Set up documentation system
- Configured AI assistant integration

## Current State

- All systems initialized and ready
- No blockers

## Next Steps

1. Define project vision in `docs/roadmap/vision/PRODUCT_VISION.md`
2. Run `/learn auto` to analyze project
3. Begin development with `/product-loop`

## Files Modified

- CLAUDE.md
- .cursorrules
- docs/* (initial structure)

## Notes

Ready for development.

---

*Update this file at the end of each session*
"""
    filepath = handoff_dir / "LATEST.md"
    if not filepath.exists() or force:
        filepath.write_text(content)
