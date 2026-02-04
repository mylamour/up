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
| `up init` | Initialize up systems (auto-installs git hooks, builds memory) |
| `up init --ai claude` | Initialize for Claude Code only |
| `up init --ai cursor` | Initialize for Cursor AI only |
| `up init --systems docs,learn` | Initialize specific systems only |
| `up start` | Start the product loop |
| `up start --resume` | Resume from last checkpoint |
| `up start --dry-run` | Preview mode without changes |
| `up status` | Show health of all systems |
| `up dashboard` | Live interactive health dashboard |
| `up sync` | Sync all systems (memory, docs) |
| `up hooks` | Install/manage git hooks for auto-sync |
| `up learn` | Auto-improve project (requires vision map) |
| `up learn "topic"` | Learn about specific topic/feature |
| `up learn "path"` | Learn from project or file (quick extraction) |
| `up learn -d "file"` | Deep AI analysis (prepare prompt for chat) |
| `up learn -r "file"` | Auto-analyze with Claude/Cursor CLI |
| `up learn auto` | Analyze project (no vision check) |
| `up learn plan` | Generate improvement PRD |
| `up memory search <query>` | Semantic search in memory |
| `up memory sync` | Index git commits and files |
| `up memory branch` | Show branch-specific knowledge |
| `up memory record` | Record learnings/decisions/errors |
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
# Self-improvement analysis (requires configured vision map)
up learn

# Learn about a specific topic
up learn "caching strategies"
up learn "authentication"
up learn "testing best practices"

# Learn from another project's design
up learn "../other-project"
up learn "~/projects/reference-app"

# Learn from a file (markdown, code, config)
up learn "docs/architecture.md"
up learn "src/utils.py"
up learn "package.json"

# Deep AI analysis (prepare for chat)
up learn -d "docs/guide.md"
# Then copy the prompt to chat for AI to analyze deeply

# Auto-analyze with Claude CLI or Cursor Agent
up learn -r "docs/guide.md"
# Runs claude or agent CLI automatically and saves analysis

# Auto-analyze without vision map requirement
up learn auto

# Check learning system status
up learn status

# Generate a PRD from analysis
up learn plan
```

The learn system has five modes:
- **Self-improvement** (`up learn`): Analyzes current project and tracks improvements over time. Requires a configured `docs/roadmap/vision/PRODUCT_VISION.md`.
- **Topic learning** (`up learn "topic"`): Creates research files for specific topics based on your project's tech stack.
- **File learning** (`up learn "path"`): Quick extraction from files or projects using regex patterns.
- **Deep analysis** (`up learn -d "file"`): Prepares file for deep AI analysis - generates a prompt to copy into chat.
- **Auto analysis** (`up learn -r "file"`): Automatically runs Claude CLI to analyze the file and saves the result.

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

Three learning modes:

| Mode | Command | Description |
|------|---------|-------------|
| Self-improvement | `up learn` | Analyze and improve current project (requires vision map) |
| Topic learning | `up learn "topic"` | Create research file for specific topic |
| External learning | `up learn "path"` | Learn from project directory or file |

Supported file types for learning:
- **Documentation**: `.md`, `.markdown`, `.txt`, `.rst`
- **Python**: `.py` (extracts patterns, classes, functions)
- **JavaScript/TypeScript**: `.js`, `.ts`, `.tsx`, `.jsx`
- **Config**: `.json`, `.yaml`, `.yml`, `.toml`

Additional commands:
- `up learn auto` - Analyze without vision map requirement
- `up learn analyze` - Extract patterns from research files
- `up learn plan` - Generate improvement PRD
- `up learn status` - Show learning system status

Storage:
```
.claude/skills/learning-system/
├── project_profile.json    # Current project analysis
├── research/               # Topic research files
├── external_learnings/     # Learnings from other projects
├── file_learnings/         # Learnings from individual files
├── insights/               # Extracted patterns
└── prd.json               # Generated improvement plan
```

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

### 5. Long-Term Memory System

Persistent knowledge that survives across sessions:

```bash
# Search for relevant knowledge
up memory search "authentication"

# Sync git commits and files to memory
up memory sync

# Record learnings and decisions
up memory record --learning "Use dataclasses for configs"
up memory record --decision "Chose PostgreSQL for ACID compliance"

# View branch-specific knowledge
up memory branch
up memory branch feature-x --compare main
```

Features:
- **Semantic search** using ChromaDB (local embeddings, no API required)
- **Branch/commit-aware** - knowledge tagged with git context
- **Auto-indexing** - git hooks sync commits automatically
- **Cross-session persistence** - remembers learnings, decisions, errors

Storage:
```
.up/
└── memory/
    └── chroma/     # ChromaDB vector database
```

### 6. MCP Server Support

Model Context Protocol integration:

```
.mcp/
├── config.json       # Server configuration
├── tools/            # Custom tool definitions
└── README.md         # Usage guide
```

## AI Integration

### Automatic Memory Sync

When you run `up init`, git hooks are automatically installed:

```bash
# Git hooks auto-installed by up init
.git/hooks/
├── post-commit      # Auto-indexes commits to memory
└── post-checkout    # Updates context on branch switch
```

This means your knowledge is captured automatically:
- Every `git commit` is indexed to memory
- Branch switches update context
- No manual sync required for commits

### Generated Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code instructions |
| `.cursorrules` | Cursor AI rules |
| `.cursor/rules/*.md` | File-specific rules |
| `.claude/context_budget.json` | Context tracking |
| `.up/memory/` | Long-term memory storage |

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
│   ├── memory.py           # Long-term memory (ChromaDB)
│   ├── events.py           # Event-driven integration
│   ├── summarizer.py       # Conversation analysis
│   ├── commands/           # CLI commands
│   │   ├── init.py         # Initialize project
│   │   ├── new.py          # Create new project
│   │   ├── status.py       # System health
│   │   ├── dashboard.py    # Live monitoring
│   │   ├── learn.py        # Learning system
│   │   ├── memory.py       # Memory commands
│   │   ├── sync.py         # Sync & hooks
│   │   ├── start.py        # Product loop
│   │   └── summarize.py    # Conversation summary
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
├── docs/                   # Documentation
│   ├── architecture/       # System architecture
│   └── guides/             # Usage guides
└── skills/                 # Reference skills
```

## License

MIT
