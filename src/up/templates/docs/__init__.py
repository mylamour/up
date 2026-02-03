"""Docs system templates."""

from pathlib import Path

def create_docs_system(target_dir: Path, force: bool = False) -> None:
    """Create the documentation system structure."""
    docs = target_dir / "docs"

    # Create directory structure
    dirs = [
        "roadmap/vision",
        "roadmap/phases",
        "roadmap/sales",
        "roadmap/implementation",
        "changelog",
        "architecture",
        "features",
        "guides",
        "operations",
        "development",
        "research",
        "todo",
        # New SDLC folders
        "decisions",
        "handoff",
        "learnings",
        "tests",
        "reviews",
        "releases",
    ]
    for d in dirs:
        (docs / d).mkdir(parents=True, exist_ok=True)

    # Create template files
    _create_main_readme(docs, force)
    _create_context_file(docs, force)
    _create_index_file(docs, force)
    _create_roadmap_readme(docs, force)
    _create_vision_template(docs, force)
    _create_phase_templates(docs, force)
    _create_changelog_readme(docs, force)
    _create_folder_readmes(docs, force)
    _create_sdlc_readmes(docs, force)


def _create_main_readme(docs: Path, force: bool) -> None:
    """Create main docs README."""
    from datetime import date
    content = f"""# Documentation

**Updated**: {date.today().isoformat()}

## Structure

| Folder | Purpose |
|--------|---------|
| roadmap/ | Strategic planning |
| architecture/ | System design |
| features/ | Feature specs |
| changelog/ | Progress tracking |
| guides/ | User how-to |
| todo/ | Future work |
| decisions/ | ADRs |
| handoff/ | Session continuity |
| learnings/ | Patterns discovered |
| tests/ | Test documentation |
| reviews/ | Code reviews |
| releases/ | Release notes |

## Key Files

- `CONTEXT.md` - AI reads first (current state)
- `INDEX.md` - Quick reference to find docs
- `handoff/LATEST.md` - Most recent session handoff
"""
    _write_file(docs / "README.md", content, force)


def _write_file(path: Path, content: str, force: bool) -> None:
    """Write file if it doesn't exist or force is True."""
    if path.exists() and not force:
        return
    path.write_text(content)


def _create_roadmap_readme(docs: Path, force: bool) -> None:
    """Create roadmap README."""
    content = """# Project Roadmap

**Created**: {date}
**Status**: 🔄 Active

---

## Overview

This roadmap defines the evolution of the project.

## Current Status

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | 📋 Planned | 0% |
| Phase 2: Intelligence | 📋 Planned | 0% |
| Phase 3: Scale | 📋 Planned | 0% |

## Folder Structure

```
docs/roadmap/
├── README.md              (this file)
├── vision/                (Product Vision)
├── phases/                (Phase Roadmaps)
├── sales/                 (Sales Materials)
└── implementation/        (Implementation Plans)
```

## Quick Links

- [Product Vision](./vision/PRODUCT_VISION.md)
- [Phase 1](./phases/PHASE_1_FOUNDATION.md)
- [Implementation Status](./implementation/STATUS.md)
"""
    from datetime import date
    content = content.replace("{date}", date.today().isoformat())
    _write_file(docs / "roadmap/README.md", content, force)


def _create_vision_template(docs: Path, force: bool) -> None:
    """Create product vision template."""
    content = """# Product Vision

**Created**: {date}
**Status**: 📋 Draft

---

## The Vision

> **One-line vision statement here**

## Problem Statement

| Pain Point | Impact |
|------------|--------|
| Problem 1 | Description |
| Problem 2 | Description |

## Solution

Brief description of the solution.

## Success Metrics

| Metric | Target |
|--------|--------|
| Metric 1 | Value |
| Metric 2 | Value |
"""
    from datetime import date
    content = content.replace("{date}", date.today().isoformat())
    _write_file(docs / "roadmap/vision/PRODUCT_VISION.md", content, force)


def _create_phase_templates(docs: Path, force: bool) -> None:
    """Create phase template files."""
    from datetime import date
    today = date.today().isoformat()

    phase1 = f"""# Phase 1: Foundation

**Timeline**: Q1
**Status**: 📋 Planned

---

## Objectives

1. Objective 1
2. Objective 2

## Deliverables

| Task | Priority | Status |
|------|----------|--------|
| Task 1 | 🔴 Critical | 📋 Planned |
| Task 2 | 🟠 High | 📋 Planned |

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2
"""
    _write_file(docs / "roadmap/phases/PHASE_1_FOUNDATION.md", phase1, force)


def _create_changelog_readme(docs: Path, force: bool) -> None:
    """Create changelog README."""
    content = """# Changelog

**Purpose**: Track progress and changes.

## Format

Each entry: `YYYY-MM-DD-topic.md`

## Template

```markdown
# Change Title

**Date**: YYYY-MM-DD
**Status**: ✅ Completed

## Summary
Brief overview

## Changes
- Change 1
- Change 2
```
"""
    _write_file(docs / "changelog/README.md", content, force)


def _create_folder_readmes(docs: Path, force: bool) -> None:
    """Create README for each folder."""
    folders = {
        "architecture": "System design docs",
        "features": "Feature specifications",
        "operations": "Deployment guides",
        "development": "Developer guides",
        "guides": "User how-to guides",
        "research": "Research notes",
        "todo": "Future work tracking",
    }
    for folder, purpose in folders.items():
        content = f"# {folder.title()}\n\n**Purpose**: {purpose}\n"
        _write_file(docs / folder / "README.md", content, force)


def _create_context_file(docs: Path, force: bool) -> None:
    """Create CONTEXT.md - AI reads this first."""
    from datetime import date
    content = f"""# Project Context

**Updated**: {date.today().isoformat()}
**Status**: 🔄 Active

---

## Current State

| Aspect | Status |
|--------|--------|
| Phase | Planning |
| Focus | Initial setup |
| Blockers | None |

## Recent Changes

- Project initialized

## Next Steps

1. Define project vision
2. Set up development environment
3. Begin implementation

## Key Files

| File | Purpose |
|------|---------|
| CLAUDE.md | AI instructions |
| docs/handoff/LATEST.md | Session continuity |
"""
    _write_file(docs / "CONTEXT.md", content, force)


def _create_sdlc_readmes(docs: Path, force: bool) -> None:
    """Create README files for SDLC folders."""
    sdlc_folders = {
        "decisions": ("Architecture Decision Records", "ADR-NNN-title.md"),
        "handoff": ("Session continuity for AI agents", "LATEST.md"),
        "learnings": ("Patterns and anti-patterns discovered", "YYYY-MM-DD-topic.md"),
        "tests": ("Test documentation and coverage", "component-tests.md"),
        "reviews": ("Code and design reviews", "YYYY-MM-DD-review.md"),
        "releases": ("Release notes and versioning", "vX.Y.Z-YYYY-MM-DD.md"),
    }
    for folder, (purpose, fmt) in sdlc_folders.items():
        content = f"# {folder.title()}\n\n**Purpose**: {purpose}\n\n**Format**: `{fmt}`\n"
        _write_file(docs / folder / "README.md", content, force)


def _create_index_file(docs: Path, force: bool) -> None:
    """Create INDEX.md - Quick reference for AI to find docs."""
    from datetime import date
    content = f"""# Documentation Index

**Updated**: {date.today().isoformat()}

> AI: Use this index to quickly find relevant documentation.

---

## Quick Reference

| Topic | File | Description |
|-------|------|-------------|
| Project State | CONTEXT.md | Current status, blockers, next steps |
| Recent Work | handoff/LATEST.md | Last session summary |
| Vision | roadmap/vision/PRODUCT_VISION.md | Product goals |
| Phase 1 | roadmap/phases/PHASE_1_FOUNDATION.md | Current phase |

## By Category

### Architecture
| Topic | File |
|-------|------|
| *Add architecture docs here* | architecture/*.md |

### Features
| Topic | File |
|-------|------|
| *Add feature specs here* | features/*.md |

### Decisions
| Topic | File |
|-------|------|
| *Add ADRs here* | decisions/ADR-*.md |

---

## How to Update

When adding new docs, update this index:
1. Add entry to relevant category table
2. Keep descriptions brief (5-10 words)
3. Use relative paths
"""
    _write_file(docs / "INDEX.md", content, force)
