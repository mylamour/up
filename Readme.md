# up-cli

<img width="3498" height="2182" alt="543426914-37655a9f-e661-4ab5-b994-e4e11f97dd95" src="https://github.com/user-attachments/assets/7cbc2614-af8e-41cb-be2f-df2b6cd43b07" />


An AI-powered CLI tool for scaffolding projects with built-in documentation, learning systems, and product-loop workflows designed for use with Claude Code and Cursor AI.

**Learned from real practice** - Built on insights from 5+ billion tokens of development experience and commercial products. Extracts best practices from chat history, documentation patterns, and proven workflows.

## Installation

```bash
pip install up-cli
```

## Quick Start

```bash
# Create new project
up new my-project

# Or initialize in existing project
cd existing-project
up init

# Check system health
up status

# Live dashboard
up dashboard
```

## Commands

| Command | Description |
|---------|-------------|
| `up new <name>` | Create a new project with full scaffolding |
| `up new <name> --template <type>` | Create project from specific template |
| `up init` | Initialize up systems in current directory |
| `up init --ai claude` | Initialize for Claude Code only |
| `up init --ai cursor` | Initialize for Cursor AI only |
| `up init --systems docs,learn` | Initialize specific systems only |
| `up start` | Start the product loop |
| `up start --resume` | Resume from last checkpoint |
| `up start --dry-run` | Preview mode without changes |
| `up status` | Show health of all systems |
| `up dashboard` | Live interactive health dashboard |
| `up learn auto` | Auto-analyze project for improvements |
| `up learn plan` | Generate improvement PRD |
| `up summarize` | Summarize AI conversation history |

## Project Templates

Create projects with pre-configured tech stacks:

```bash
# FastAPI backend with SQLAlchemy
up new my-api --template fastapi

# Next.js frontend with TypeScript
up new my-app --template nextjs

# Python library with packaging
up new my-lib --template python-lib

# Minimal structure
up new my-project --template minimal

# Full setup with MCP
up new my-project --template full
```

| Template | Description |
|----------|-------------|
| `minimal` | Basic structure with docs |
| `standard` | Full up systems (default) |
| `full` | Everything including MCP server |
| `fastapi` | FastAPI + SQLAlchemy + pytest |
| `nextjs` | Next.js 14 + TypeScript + Tailwind |
| `python-lib` | Python library with pyproject.toml |

## Usage Examples

### Create a new project

```bash
# Create a new project with all systems
up new my-saas-app

# Create with a specific template
up new my-api --template fastapi
```

### Initialize in existing project

```bash
cd my-existing-project

# Full initialization
up init

# Claude Code focused setup
up init --ai claude

# Only add docs and learn systems
up init --systems docs,learn
```

### Monitor System Health

```bash
# Quick status check
up status

# Live dashboard (updates every 5 seconds)
up dashboard

# JSON output for scripting
up status --json
```

### Using the Learn System

```bash
# Auto-analyze your project and generate insights
up learn auto

# Check learning system status
up learn status

# Generate a PRD from analysis
up learn plan
```

### Using the Product Loop

```bash
# Start the product loop
up start

# Resume from checkpoint
up start --resume

# Preview what would happen
up start --dry-run

# Start with specific task
up start --task US-003

# Use custom PRD file
up start --prd path/to/prd.json
```

### Summarize Conversations

```bash
# Summarize Cursor chat history
up summarize

# Export as JSON
up summarize --format json --output summary.json

# Filter by project
up summarize --project myproject
```

## Systems

### 1. Docs System

Comprehensive documentation structure:

```
docs/
├── CONTEXT.md         # AI reads first
├── INDEX.md           # Quick reference
├── roadmap/           # Strategic planning
│   ├── vision/        # Product vision
│   └── phases/        # Phase roadmaps
├── architecture/      # System design
├── features/          # Feature specs
├── changelog/         # Progress tracking
├── handoff/           # Session continuity
├── decisions/         # ADRs
└── learnings/         # Patterns discovered
```

### 2. Learn System

Research and improvement pipeline:

```
RESEARCH → ANALYZE → COMPARE → PLAN → IMPLEMENT
```

- `/learn auto` - Auto-analyze project
- `/learn research [topic]` - Research topic
- `/learn plan` - Generate improvement PRD

### 3. Product Loop (SESRC)

Autonomous development with safety guardrails:

| Principle | Implementation |
|-----------|----------------|
| **Stable** | Graceful degradation, fallback modes |
| **Efficient** | Token budgets, incremental testing |
| **Safe** | Input validation, path whitelisting |
| **Reliable** | Timeouts, idempotency, rollback |
| **Cost-effective** | Early termination, ROI threshold |

Features:
- Circuit breaker (max 3 failures)
- Checkpoint/rollback
- Health checks
- Budget limits

### 4. Context Budget

Tracks AI context window usage:

- Estimates token usage per file/message
- Warns at 80% capacity
- Suggests handoff at 90%
- Persists across sessions

### 5. MCP Server Support

Model Context Protocol integration:

```
.mcp/
├── config.json       # Server configuration
├── tools/            # Custom tool definitions
└── README.md         # Usage guide
```

## AI Integration

### Generated Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code instructions |
| `.cursorrules` | Cursor AI rules |
| `.cursor/rules/*.md` | File-specific rules |
| `.claude/context_budget.json` | Context tracking |

### Cursor Rules

Generated rules for different file types:
- `main.md` - General project rules
- `python.md` - Python standards
- `typescript.md` - TypeScript standards
- `docs.md` - Documentation standards
- `tests.md` - Testing standards

## Design Principles & Practices

### AI-First Development

**Design for AI collaboration, not just human readability.**

- **Context-aware scaffolding** - Project structures optimized for AI agents to navigate and understand quickly
- **Explicit over implicit** - Clear file naming, directory structures, and documentation that AI can parse without ambiguity
- **Prompt-friendly patterns** - Code and docs written to be easily referenced in AI conversations
- **Tool integration** - Native support for Claude Code skills and Cursor AI rules

### Documentation-Driven Development

**Documentation is the source of truth, not an afterthought.**

- **Docs-first workflow** - Write documentation before implementation to clarify intent
- **Living documentation** - Docs evolve with the codebase through automated learning systems
- **Knowledge extraction** - `/learn` commands analyze patterns and generate insights from real usage
- **Structured knowledge** - Vision, roadmaps, and changelogs in predictable locations for AI and human consumption

### Product Loop Patterns (SESRC)

**Autonomous development with safety guardrails.**

- **Circuit breaker protection** - Max 3 consecutive failures before stopping to prevent runaway loops
- **Checkpoint/rollback** - Save state before risky operations, restore on failure
- **Health checks** - Validate system state between iterations
- **Budget limits** - Token and time constraints to prevent unbounded execution
- **Human-in-the-loop** - Critical decisions require explicit approval

### Core Practices

| Practice | Description |
|----------|-------------|
| **Incremental delivery** | Ship small, working increments over big-bang releases |
| **Fail fast, recover faster** | Detect issues early, rollback automatically |
| **Observable by default** | Logging, metrics, and state visible to both AI and humans |
| **Convention over configuration** | Sensible defaults that work out of the box |

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
│   ├── cli.py              # Main CLI
│   ├── context.py          # Context budget management
│   ├── summarizer.py       # Conversation analysis
│   ├── commands/           # CLI commands
│   │   ├── init.py
│   │   ├── new.py
│   │   ├── status.py
│   │   ├── dashboard.py
│   │   ├── learn.py
│   │   └── summarize.py
│   └── templates/          # Scaffolding templates
│       ├── config/         # CLAUDE.md, .cursor/rules
│       ├── docs/           # Documentation system
│       ├── learn/          # Learning system
│       ├── loop/           # Product loop
│       ├── mcp/            # MCP server
│       └── projects/       # Project templates
├── scripts/                # Utility scripts
│   ├── export_claude_history.py
│   └── export_cursor_history.py
└── skills/                 # Reference skills
```

## License

MIT
