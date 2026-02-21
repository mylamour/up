# Up-CLI 🚀

<div align="center">
<img width="1200" alt="Up-CLI Dashboard" src="https://github.com/user-attachments/assets/7cbc2614-af8e-41cb-be2f-df2b6cd43b07" />

**Make AI-assisted development verifiable, observable, and safe — turning Vibe Coding into Software Engineering.**

[![PyPI version](https://badge.fury.io/py/up-cli.svg)](https://badge.fury.io/py/up-cli)
[![Python Version](https://img.shields.io/pypi/pyversions/up-cli.svg)](https://pypi.org/project/up-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

</div>

An AI-powered CLI tool for scaffolding projects with built-in documentation, learning systems, and SESRC product-loop workflows designed for use with **Claude Code** and **Cursor AI**.

**Learned from real practice** - Built on insights from millions of tokens of development experience. Extracts best practices from chat history, documentation patterns, and proven autonomous workflows.

---

## 🌟 Why Up-CLI? (The SESRC Principles)

Traditional "Vibe Coding" with AI produces unverified changes, leading to silent bugs and runaway loops. Up-CLI wraps your AI assistant in an engineering safety net:

| Principle | Implementation |
|-----------|----------------|
| **Stable** | Graceful degradation, fallback modes, unified state manager |
| **Efficient** | Token budget tracking, incremental testing, AST-based analysis |
| **Safe** | Input validation, path whitelisting, dry-run previews |
| **Reliable** | Circuit breakers, idempotency, verifiable `git` rollback |
| **Cost-effective** | Early termination, multi-agent parallel execution |

---

## ⚡ Installation

```bash
# Minimal installation
pip install up-cli

# Full installation (includes ChromaDB for Semantic Search Memory)
pip install up-cli[all]
```

## 🚀 Quick Start

### 1. Scaffold a new project
```bash
up new my-project --template fastapi
cd my-project
```

### 2. Check System Safety Rails
```bash
up status
```

### 3. Start the Autonomous Loop
```bash
# Write your tasks in TODO.md or prd.json, then run:
up start --auto-commit

# Or run multiple AI agents in parallel!
up start --parallel --jobs 3
```

---

## 🛠️ Commands Reference

### Vibe Coding Safety Rails
| Command | Description |
|---------|-------------|
| `up save` | Create a Git checkpoint before risky AI work |
| `up reset` | Instantly restore workspace to the last checkpoint |
| `up diff` | Review AI changes before accepting |
| `up review` | Run an AI adversarial code review |

### Autonomous Development (Product Loop)
| Command | Description |
|---------|-------------|
| `up start` | Start the SESRC autonomous product loop |
| `up start --parallel` | Run multi-agent execution in isolated git worktrees |
| `up agent spawn/status` | Manage isolated agent worktrees manually |
| `up bisect` | Find bug-introducing commits automatically |
| `up provenance list` | View AI operation lineage and audit trail |

### Knowledge & Memory System
| Command | Description |
|---------|-------------|
| `up learn auto` | Auto-improve project using AST analysis (Requires Vision Map) |
| `up learn "topic"` | Command AI to research and document a specific tech topic |
| `up memory search <q>` | Semantic search across historical decisions and bugs |
| `up memory record` | Manually record learnings/decisions to Long-Term Memory |

### System & Scaffolding
| Command | Description |
|---------|-------------|
| `up new <name> -t <type>`| Scaffold a new project (minimal, full, fastapi, nextjs) |
| `up init` | Initialize up-cli in an existing repository |
| `up status` | Show health of Circuit Breakers and Context Budgets |
| `up dashboard` | Launch the live interactive TUI dashboard |
| `up hooks` | Install git hooks for automatic memory indexing |

---

## 🧠 Core Systems

### 1. The Resilient Product Loop (SESRC)

The `up start` command implements a bulletproof autonomous execution cycle:
`OBSERVE → CHECKPOINT → EXECUTE → VERIFY → COMMIT`

- **Circuit Breaker**: Prevents Doom Loops. If the AI fails to write passing code 3 times in a row, the circuit opens, halts execution, and prevents token burn.
- **Auto-Rollback**: If tests or linting fails, changes are instantly reverted.
- **Smart Merge**: In `--parallel` mode, if multiple agents cause a Git conflict, the system feeds the conflict markers back to the AI to resolve intelligently.

### 2. AST-Based Learning System

The `/learn` commands use Python's Abstract Syntax Tree (`ast`) to physically parse your code, accurately detecting framework usage (e.g., React Hooks, FastAPI Routers, Repository patterns) rather than relying on brittle Regex or AI hallucinations.

### 3. Long-Term Memory

Up-CLI comes with a local ChromaDB instance (`.up/memory`). It auto-indexes your git commits. When the AI gets stuck, it can semantic-search past errors and decisions to avoid repeating mistakes across sessions.

---

## 📂 Project Templates

Create projects with pre-configured tech stacks and AI rules (`CLAUDE.md`, `.cursorrules`):

```bash
# FastAPI backend with SQLAlchemy
up new my-api --template fastapi

# Next.js frontend with TypeScript
up new my-app --template nextjs

# Python library with packaging
up new my-lib --template python-lib

# Full setup with MCP support
up new my-project --template full
```

## Development

```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Type check
mypy src/
```

## Project Structure

```
up-cli/
├── src/up/
│   ├── cli.py              # Main CLI entry point
│   ├── ai_cli.py           # AI CLI utilities (Claude/Cursor)
│   ├── context.py          # Context budget management
│   ├── events.py           # Event-driven integration
│   ├── summarizer.py       # Conversation analysis
│   ├── parallel.py         # Parallel task execution
│   ├── parallel_scheduler.py # Dependency-aware scheduling
│   ├── core/               # Core modules
│   │   ├── state.py        # Unified state management
│   │   ├── checkpoint.py   # Git checkpoint operations
│   │   └── provenance.py   # AI operation tracking
│   ├── git/                # Git utilities
│   │   ├── utils.py        # Git command helpers
│   │   └── worktree.py     # Worktree management
│   ├── learn/              # Learning system
│   │   ├── analyzer.py     # Project analysis
│   │   ├── research.py     # Topic/file learning
│   │   ├── plan.py         # PRD generation
│   │   └── utils.py        # Shared utilities
│   ├── memory/             # Long-term memory (ChromaDB)
│   │   ├── _manager.py     # Memory manager
│   │   ├── entry.py        # Memory entries
│   │   └── stores.py       # Storage backends
│   ├── commands/           # CLI commands
│   │   ├── init.py         # Initialize project
│   │   ├── new.py          # Create new project
│   │   ├── status.py       # System health
│   │   ├── dashboard.py    # Live monitoring
│   │   ├── start/          # Product loop (subpackage)
│   │   ├── vibe.py         # save/reset/diff
│   │   ├── agent.py        # Multi-agent worktrees
│   │   ├── bisect.py       # Bug hunting
│   │   ├── provenance.py   # Lineage tracking
│   │   ├── review.py       # AI code review
│   │   ├── branch.py       # Branch hierarchy
│   │   ├── memory.py       # Memory commands
│   │   ├── sync.py         # Sync & hooks
│   │   └── summarize.py    # Conversation summary
│   ├── ui/                 # Terminal UI components
│   │   ├── loop_display.py # Product loop live display
│   │   └── theme.py        # Rich theme
│   └── templates/          # Scaffolding templates
│       ├── config/         # CLAUDE.md, .cursor/rules
│       ├── docs/           # Documentation system
│       ├── learn/          # Learning system
│       ├── loop/           # Product loop
│       ├── mcp/            # MCP server
│       └── projects/       # Project templates
├── tests/                  # Test suite
├── scripts/                # Utility scripts
└── docs/                   # Documentation
    ├── architecture/       # System architecture
    ├── guides/             # Usage guides
    └── handoff/            # Session continuity
```

## License

MIT
