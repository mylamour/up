# up-cli

![img](https://img.iami.xyz/images/ai-futures/543426914-37655a9f-e661-4ab5-b994-e4e11f97dd95.png)

An AI-powered CLI tool for scaffolding projects with built-in documentation, learning systems, and product-loop workflows designed for use with Claude Code and Cursor AI.

**Learned from real practice** - Built on insights from 5+ billion tokens of development experience and commercial products. Extracts best practices from chat history, documentation patterns, and proven workflows.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Create new project
up new my-project

# Or initialize in existing project
cd existing-project
up init
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

### Using the Learn System

```bash
# Auto-analyze your project and generate insights
/learn auto

# Research a specific topic with web sources
/learn research "authentication patterns"

# Generate a PRD from your codebase
/learn plan
```

### Using the Product Loop

```bash
# Start autonomous development loop
./skills/product-loop/start-autonomous.sh

# Run with circuit breaker protection
./skills/product-loop/ralph_hybrid.sh
```

## Systems

### 1. Docs System

```
docs/roadmap/vision/      # Product vision
docs/roadmap/phases/      # Phase roadmaps
docs/changelog/           # Progress tracking
```

### 2. Learn System

- `/learn auto` - Auto-analyze project
- `/learn research [topic]` - Research topic
- `/learn plan` - Generate PRD

### 3. Product Loop (SESRC)

- Circuit breaker (max 3 failures)
- Checkpoint/rollback
- Health checks
- Budget limits

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
pip install -e .
pytest
```

## License

MIT
