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

    # Create base structure
    _create_base_structure(target_dir, ai_target)

    # Create config files
    create_config_files(target_dir, ai_target, force)

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


def _create_base_structure(target_dir: Path, ai_target: str) -> None:
    """Create base directory structure."""
    dirs = ["src", "tests", "docs"]

    # AI-specific directories
    if ai_target in ("claude", "both"):
        dirs.append(".claude/skills")
    if ai_target in ("cursor", "both"):
        dirs.append(".cursor")

    for d in dirs:
        (target_dir / d).mkdir(parents=True, exist_ok=True)
