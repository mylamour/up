"""Shared utilities for the learning system."""

import json
import re
from datetime import date
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()


def find_skill_dir(workspace: Path, skill_name: str) -> Path:
    """Find skill directory (Claude or Cursor)."""
    claude_skill = workspace / f".claude/skills/{skill_name}"
    cursor_skill = workspace / f".cursor/skills/{skill_name}"
    
    if claude_skill.exists():
        return claude_skill
    if cursor_skill.exists():
        return cursor_skill
    
    # Default to Claude
    return claude_skill


def check_vision_map_exists(workspace: Path) -> tuple[bool, Path]:
    """Check if vision map is set up (not just template).
    
    Returns:
        (exists_and_configured, vision_path)
    """
    vision_path = workspace / "docs/roadmap/vision/PRODUCT_VISION.md"
    
    if not vision_path.exists():
        return False, vision_path
    
    content = vision_path.read_text()
    template_indicators = [
        "One-line vision statement here",
        "Problem 1 | Description",
        "Metric 1 | Value",
    ]
    
    for indicator in template_indicators:
        if indicator in content:
            return False, vision_path
    
    return True, vision_path


def is_valid_path(s: str) -> bool:
    """Check if string looks like a path."""
    if Path(s).exists():
        return True
    
    path_indicators = ['/', '\\', './', '../', '~/', ':', 'C:\\']
    return any(s.startswith(ind) or ind in s for ind in path_indicators)


def safe_filename(name: str) -> str:
    """Convert string to safe filename."""
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_').lower()


def record_to_memory(workspace: Path, content: str, entry_type: str = "learning") -> None:
    """Record entry to memory system (optional, best-effort)."""
    import logging
    try:
        from up.memory import MemoryManager
        manager = MemoryManager(workspace, use_vectors=False)
        if entry_type == "learning":
            manager.record_learning(content)
        else:
            manager.record(content, entry_type=entry_type)
    except Exception as e:
        logging.getLogger(__name__).debug("Memory recording skipped: %s", e)


def display_profile(profile: dict) -> None:
    """Display profile in rich format."""
    table = Table(title="Project Profile")
    table.add_column("Aspect", style="cyan")
    table.add_column("Detected")
    
    table.add_row("Name", profile.get("name", "Unknown"))
    table.add_row("Languages", ", ".join(profile.get("languages", [])) or "None")
    table.add_row("Frameworks", ", ".join(profile.get("frameworks", [])) or "None")
    table.add_row("Patterns", ", ".join(profile.get("patterns_detected", [])) or "None")
    table.add_row("Improvements", ", ".join(profile.get("improvement_areas", [])) or "None")
    table.add_row("Research Topics", ", ".join(profile.get("research_topics", [])) or "None")
    
    console.print(table)


def save_profile(workspace: Path, profile: dict) -> Path:
    """Save profile to JSON file."""
    skill_dir = find_skill_dir(workspace, "learning-system")
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = skill_dir / "project_profile.json"
    filepath.write_text(json.dumps(profile, indent=2))
    return filepath


def load_profile(workspace: Path) -> dict:
    """Load profile from file if exists."""
    skill_dir = find_skill_dir(workspace, "learning-system")
    profile_file = skill_dir / "project_profile.json"
    
    if profile_file.exists():
        try:
            return json.loads(profile_file.read_text())
        except json.JSONDecodeError:
            pass
    return {}
