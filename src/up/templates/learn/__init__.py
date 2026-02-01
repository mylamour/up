"""Learn system templates."""

from pathlib import Path


def create_learn_system(target_dir: Path, ai_target: str, force: bool = False) -> None:
    """Create the learn system structure."""
    # Determine skill directory based on AI target
    if ai_target in ("claude", "both"):
        skill_dir = target_dir / ".claude/skills/learning-system"
    else:
        skill_dir = target_dir / ".cursor/skills/learning-system"

    # Create directories
    dirs = ["research", "insights"]
    for d in dirs:
        (skill_dir / d).mkdir(parents=True, exist_ok=True)

    # Create files
    _create_skill_md(skill_dir, force)
    _create_sources_json(skill_dir, force)
    _create_patterns_md(skill_dir, force)


def _write_file(path: Path, content: str, force: bool) -> None:
    """Write file if it doesn't exist or force is True."""
    if path.exists() and not force:
        return
    path.write_text(content)


def _create_skill_md(skill_dir: Path, force: bool) -> None:
    """Create SKILL.md for learn system."""
    content = """---
name: learn
description: Research and create improvement plans
user-invocable: true
allowed-tools: Read, Write, Bash, WebFetch, WebSearch
---

# Learning System

Research best practices and create actionable plans.

## Workflow

```
RESEARCH → ANALYZE → COMPARE → PLAN
```

## Commands

- `/learn auto` - Auto-analyze project
- `/learn research [topic]` - Research topic
- `/learn plan` - Generate improvement PRD

## Output Files

| File | Purpose |
|------|---------|
| `research/*.md` | Research notes |
| `insights/patterns.md` | Extracted patterns |
| `prd.json` | Improvement plan |
"""
    _write_file(skill_dir / "SKILL.md", content, force)


def _create_sources_json(skill_dir: Path, force: bool) -> None:
    """Create sources.json config."""
    content = """{
  "projects": [],
  "blogs": [],
  "topics": []
}
"""
    _write_file(skill_dir / "sources.json", content, force)


def _create_patterns_md(skill_dir: Path, force: bool) -> None:
    """Create patterns template."""
    content = """# Extracted Patterns

**Status**: 🔄 Active

---

## Pattern Template

- **Source**: Project/Blog
- **Description**: What it does
- **Applicability**: How to use it
"""
    _write_file(skill_dir / "insights/patterns.md", content, force)
