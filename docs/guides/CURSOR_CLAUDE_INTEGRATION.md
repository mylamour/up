# Using up-cli with Cursor IDE and Claude CLI

**Created**: 2026-02-03  
**Status**: 📋 Reference

---

## Overview

The `up` system can work with your existing Cursor IDE and Claude CLI workflows without requiring you to use `up start`. Here's how memory tracking works in different scenarios:

## Automatic Tracking (What Works Without `up start`)

### With Git Hooks Installed

If you've run `up init` or `up hooks`, these are automatically tracked:

| Action | Auto-Tracked? | How |
|--------|---------------|-----|
| Git commits | ✅ Yes | `post-commit` hook indexes to memory |
| Branch switches | ✅ Yes | `post-checkout` hook updates context |
| File changes | ❌ No | Only tracked on commit |
| Learnings/decisions | ❌ No | Must record manually |
| Errors encountered | ❌ No | Must record manually |

### Without Git Hooks

Nothing is automatically tracked. You need to run `up memory sync` manually.

---

## How to Enable Auto-Tracking

### Step 1: Install Hooks (One Time)

```bash
# If you already have up initialized
up hooks

# Or include with initialization
up init --hooks  # (default behavior)
```

### Step 2: Verify Installation

```bash
up status
# Look for:
# Auto-Sync (Git Hooks)
#   ✓ Enabled - commits auto-indexed to memory
```

---

## Recommended Workflow with Cursor/Claude

### Option 1: Let Git Hooks Handle It (Recommended)

1. Work normally in Cursor or Claude CLI
2. Commits are auto-indexed when you `git commit`
3. Periodically run `up memory sync` for file changes

```bash
# After a session of work
up memory sync

# Record any learnings
up memory record --learning "Found that X pattern works better than Y"
up memory record --decision "Using Z approach for authentication"
```

### Option 2: Start Each Session with Sync

Add to your workflow:

```bash
# At start of session
up memory sync

# ... work with Cursor/Claude ...

# At end of session
up memory sync
up memory record --learning "Today I learned..."
```

### Option 3: Use Shell Alias (Power Users)

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# Quick sync alias
alias us="up memory sync"

# Start coding session (sync + show status)
alias uc="up memory sync && up status"

# End coding session (sync + record)
function done() {
    up memory sync
    if [ -n "$1" ]; then
        up memory record --learning "$1"
    fi
    echo "Session complete. Memory updated."
}
```

Usage:
```bash
uc          # Start session
# ... work ...
done "Learned how to optimize database queries"
```

---

## What Gets Remembered

### From Git Commits (Automatic)

- Commit messages and descriptions
- Which files were modified
- Which branch it was on
- Commit hash (for version tracking)

### From Manual Recording

```bash
# Learnings - patterns, techniques, insights
up memory record --learning "Use dataclasses for configs, not dicts"

# Decisions - architectural choices
up memory record --decision "Chose PostgreSQL for ACID compliance"

# Errors - problems and solutions
up memory record --error "ImportError with module X" --solution "pip install x[extra]"
```

### From Manual Sync

```bash
up memory sync
# Indexes:
# - Recent commits (last 20)
# - Changed files (last 5 commits)
```

---

## Cursor-Specific Integration

### Using Cursor Rules

If you have `.cursor/rules/` set up (via `up init`), add this rule:

```markdown
# .cursor/rules/memory.md

When working on this project:

1. After completing a significant change, suggest running:
   `up memory record --learning "description"`

2. After encountering and fixing an error, suggest running:
   `up memory record --error "..." --solution "..."`

3. Before starting work, check memory for relevant context:
   `up memory search "topic"`
```

### Cursor Task Integration

Add to your VS Code tasks:

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "up: sync memory",
      "type": "shell",
      "command": "up memory sync",
      "problemMatcher": []
    },
    {
      "label": "up: show status",
      "type": "shell", 
      "command": "up status",
      "problemMatcher": []
    }
  ]
}
```

---

## Claude CLI Integration

### Pre-Session Context

Before starting a Claude CLI session, get relevant context:

```bash
# Search for relevant memories
up memory search "authentication"
up memory recall "database"

# Get branch-specific knowledge
up memory branch

# Copy to clipboard for Claude (macOS)
up memory search "topic" | pbcopy
```

### Post-Session Recording

After a productive Claude CLI session:

```bash
# Record what you learned
up memory record --learning "Claude suggested using async/await for I/O bound operations"

# If you made important decisions
up memory record --decision "Using Claude's suggestion for error handling pattern"

# Sync any commits made
up memory sync
```

---

## Checking What's Remembered

```bash
# Overall stats
up memory stats

# Recent learnings
up memory list --type learning

# Search for specific topics
up memory search "your topic"

# Branch-specific knowledge
up memory branch
up memory branch feature-x --compare main
```

---

## Summary: Quick Reference

```bash
# One-time setup
up init                     # Initialize with hooks
up hooks                    # Or install hooks separately

# Daily workflow
up memory sync              # Sync changes
up memory record --learning "..."  # Record insights

# Searching
up memory search "topic"    # Find relevant memories
up memory branch            # See branch knowledge

# Status
up status                   # Full system status
up hooks --check            # Verify hooks installed
```

---

## FAQ

**Q: Do I need to use `up start` for memory to work?**

A: No. Memory works independently. `up start` is for the automated product loop. Git hooks + manual sync cover most use cases.

**Q: How often should I run `up memory sync`?**

A: If you have hooks installed, commits are auto-synced. Run manual sync when you want to index file content changes or at the start/end of sessions.

**Q: Will my memory carry over when I switch branches?**

A: Yes! All memories are preserved. Each entry is tagged with the branch it was created on, so you can filter by branch if needed.

**Q: Is the data stored locally or in the cloud?**

A: 100% local. Everything is stored in `.up/memory/` in your project directory.
