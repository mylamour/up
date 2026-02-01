"""Docs skill templates."""

from pathlib import Path


def create_docs_skill(target_dir: Path, ai_target: str, force: bool = False) -> None:
    """Create the docs-system skill."""
    if ai_target in ("claude", "both"):
        skill_dir = target_dir / ".claude/skills/docs-system"
    else:
        skill_dir = target_dir / ".cursor/skills/docs-system"

    skill_dir.mkdir(parents=True, exist_ok=True)
    _create_skill_md(skill_dir, force)


def _write_file(path: Path, content: str, force: bool) -> None:
    """Write file if it doesn't exist or force is True."""
    if path.exists() and not force:
        return
    path.write_text(content)


def _create_skill_md(skill_dir: Path, force: bool) -> None:
    """Create SKILL.md for docs system."""
    content = """---
name: docs
description: Documentation system with standards
user-invocable: true
allowed-tools: Read, Write, Edit, Glob
---

# Docs Skill

## Commands

- `/docs new [type]` - Create document
- `/docs status` - Show status

## Types

| Type | Folder |
|------|--------|
| feature | features/ |
| arch | architecture/ |
| changelog | changelog/ |
| guide | guides/ |
"""
    _write_file(skill_dir / "SKILL.md", content, force)
