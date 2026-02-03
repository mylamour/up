# Multi-Agent & Skills Design Analysis

**Created**: 2026-02-01
**Status**: 🔄 Active Design

---

## Question 2: Multi-Agent Collaboration

### Current /sync-context Skill

The `/sync-context` is a **built-in Claude Code skill** that generates handoff artifacts. It's designed for:
- Switching between frontend/backend contexts
- Handing off to another agent

### Multi-Agent Design Recommendations

For multiple agents working on the same project:

| Approach | How It Works | Best For |
|----------|--------------|----------|
| **Handoff Files** | `docs/handoff/LATEST.md` | Sequential work |
| **Context Files** | `docs/CONTEXT.md` | Shared state |
| **Lock Files** | `.claude/WORKING_ON.md` | Prevent conflicts |

### Recommended Multi-Agent Structure

```
.claude/
├── WORKING_ON.md        # Current agent's focus
├── AGENT_LOG.md         # Who did what
└── skills/

docs/
├── CONTEXT.md           # Shared project state
├── handoff/
│   ├── LATEST.md        # Most recent handoff
│   └── [agent]-[date].md
```

---

## Question 3: Script-Based Skills

### Your Concern

> "Skills are just markdown - should they be script-based?"

**You're right.** Markdown-only skills have limitations:

| Limitation | Impact |
|------------|--------|
| No execution | Can't run real commands |
| No validation | Can't verify results |
| AI-dependent | Output varies |

### Recommended Hybrid Approach

**Combine markdown + scripts**:

```
skills/
├── docs-system/
│   ├── SKILL.md          # Instructions for AI
│   ├── scripts/          # Executable scripts
│   │   ├── init.py       # Create folder structure
│   │   ├── validate.py   # Validate headers
│   │   └── status.py     # Show doc status
│   └── templates/
```

### Example Script: docs-init.py

```python
#!/usr/bin/env python3
"""Initialize docs structure."""
from pathlib import Path

FOLDERS = [
    "architecture", "features", "changelog",
    "decisions", "handoff", "learnings"
]

def init_docs(target: Path):
    for folder in FOLDERS:
        (target / "docs" / folder).mkdir(parents=True, exist_ok=True)
    print(f"Created {len(FOLDERS)} folders")

if __name__ == "__main__":
    init_docs(Path.cwd())
```

---

## Question 4: How UP Creates CLAUDE.md

### Current Flow

```
up init / up new
    │
    ├── scaffold_project()
    │       │
    │       └── create_config_files()
    │               │
    │               ├── _create_claude_md()  → CLAUDE.md
    │               └── _create_cursorrules() → .cursorrules
```

### Current Behavior

| Command | Creates CLAUDE.md? | Updates? |
|---------|-------------------|----------|
| `up init` | ✅ Yes | ❌ No (skips if exists) |
| `up new` | ✅ Yes | ❌ No (skips if exists) |
| `up new --force` | ✅ Yes | ✅ Overwrites |

### Improvement: Add `up update` Command

```python
# New command to add
@click.command()
def update():
    """Update CLAUDE.md with latest template."""
    # Merge existing + new content
```

---

*This document guides the enhancement of UP project skills.*
