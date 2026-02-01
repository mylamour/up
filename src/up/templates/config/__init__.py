"""Config file templates for Claude and Cursor."""

from pathlib import Path


def create_config_files(target_dir: Path, ai_target: str, force: bool = False) -> None:
    """Create config files for AI assistants."""
    if ai_target in ("claude", "both"):
        _create_claude_md(target_dir, force)
    if ai_target in ("cursor", "both"):
        _create_cursorrules(target_dir, force)


def _write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.write_text(content)


def _create_claude_md(target_dir: Path, force: bool) -> None:
    """Create CLAUDE.md for Claude Code."""
    content = """# Project Guide

## On Session Start

1. Read `docs/CONTEXT.md` for current state
2. Check `docs/handoff/LATEST.md` for recent work
3. Use `docs/INDEX.md` to find relevant docs
4. Apply rules below

## AI Vibing Coding Rules

### Golden Rules
1. **Vision before code** - Understand architecture first
2. **One thing at a time** - Numbered, atomic requests
3. **Verify immediately** - Test after each change
4. **Context is king** - Use @file references
5. **Frustration = signal** - Change approach when stuck

### Request Format
```
1. [ACTION] [TARGET] [CONTEXT]
2. [ACTION] [TARGET] [CONTEXT]
```

### 2-Failure Rule
If something fails twice:
1. Provide more context
2. Reference specific files
3. Break into smaller steps

## Skills

| Skill | When to Use |
|-------|-------------|
| `/docs` | Create/manage documentation |
| `/learn` | Research and create PRD |
| `/product-loop` | Development with SESRC |

## Auto-Triggers

- New feature → `/learn auto`
- Start coding → `/product-loop`
- Need docs → `/docs new [type]`
- Session end → Update `docs/handoff/LATEST.md`
"""
    _write_file(target_dir / "CLAUDE.md", content, force)


def _create_cursorrules(target_dir: Path, force: bool) -> None:
    """Create .cursorrules for Cursor AI."""
    content = """# Cursor Rules

## Skills Available

- /docs - Documentation management
- /learn - Research and PRD
- /product-loop - SESRC development

## Workflow

1. Research: /learn auto
2. Build: /product-loop
3. Document: /docs new
"""
    _write_file(target_dir / ".cursorrules", content, force)
