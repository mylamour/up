"""Product-loop system templates."""

from pathlib import Path


def create_loop_system(target_dir: Path, ai_target: str, force: bool = False) -> None:
    """Create the product-loop system structure."""
    # Determine skill directory based on AI target
    if ai_target in ("claude", "both"):
        skill_dir = target_dir / ".claude/skills/product-loop"
    else:
        skill_dir = target_dir / ".cursor/skills/product-loop"

    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create files
    _create_skill_md(skill_dir, force)
    _create_loop_state(target_dir, force)


def _write_file(path: Path, content: str, force: bool) -> None:
    """Write file if it doesn't exist or force is True."""
    if path.exists() and not force:
        return
    path.write_text(content)


def _create_skill_md(skill_dir: Path, force: bool) -> None:
    """Create SKILL.md for product-loop."""
    content = """---
name: product-loop
description: Resilient development with SESRC principles
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, TodoWrite
---

# Resilient Product Loop

## SESRC Principles

| Principle | Implementation |
|-----------|----------------|
| **Stable** | Graceful degradation |
| **Efficient** | Token budgets |
| **Safe** | Input validation |
| **Reliable** | Timeouts, rollback |
| **Cost-effective** | Early termination |

## Loop

```
OBSERVE → CHECKPOINT → EXECUTE → VERIFY → COMMIT
```

## Commands

- `/product-loop` - Start loop
- `/product-loop resume` - Resume from checkpoint
- `/product-loop status` - Show state
- `/product-loop rollback` - Rollback last change

## Circuit Breaker

Max 3 failures before circuit opens.

## State File

`.loop_state.json` tracks progress.
"""
    _write_file(skill_dir / "SKILL.md", content, force)


def _create_loop_state(target_dir: Path, force: bool) -> None:
    """Create initial loop state file."""
    content = """{
  "version": "1.0",
  "iteration": 0,
  "phase": "INIT",
  "circuit_breaker": {
    "test": {"failures": 0, "state": "CLOSED"},
    "build": {"failures": 0, "state": "CLOSED"}
  },
  "checkpoints": [],
  "metrics": {
    "total_edits": 0,
    "total_rollbacks": 0,
    "success_rate": 1.0
  }
}
"""
    _write_file(target_dir / ".loop_state.json", content, force)
