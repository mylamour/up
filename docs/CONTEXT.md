# Project Context

**Updated**: 2026-02-27
**Status**: ✅ Production Ready
**Version**: 1.0.0

---

## Target (North Star)

Work is aligned to the **final target** and **self-evolution** loop. See [docs/TARGET.md](TARGET.md) for vision, success metrics, and current focus.

---

## Current State

| Aspect | Status |
|--------|--------|
| Phase | All 6 phases complete |
| Focus | Stability, docs, blog |
| Blockers | None |
| Tests | 534 passing (59 test files) |
| Source | 91 Python modules |

## Architecture

```
.up/
├── state.json           # Unified state (loop, context, agents, metrics)
├── config.json          # Configuration (thresholds, timeouts, workers)
├── checkpoints/         # Checkpoint metadata (git tags + JSON)
├── provenance/          # AI operation lineage (Merkle chain)
├── memory/              # ChromaDB + JSON fallback
│   ├── chroma/          # Vector embeddings (semantic search)
│   └── index.json       # JSON fallback (keyword search)
└── plugins/
    ├── registry.json    # Plugin enable/disable state
    ├── builtin/         # 4 core plugins
    └── installed/       # 4 community plugins

src/up/
├── core/                # Core modules
│   ├── state.py         # Unified state management (atomic writes)
│   ├── checkpoint.py    # Git checkpoint operations
│   ├── provenance.py    # AI operation tracking (Merkle chain)
│   └── prd_schema.py    # PRD/UserStory data models
├── memory/              # Persistent memory system
│   ├── entry.py         # Data models (MemoryEntry, etc.)
│   ├── stores.py        # ChromaDB + JSON backends
│   ├── _manager.py      # MemoryManager (CRUD, search, indexing)
│   └── patterns.py      # ErrorPatternExtractor
├── plugins/             # Plugin system
│   ├── loader.py        # Auto-discovery from disk
│   ├── registry.py      # Enable/disable state
│   ├── manifest.py      # Schema validation
│   ├── hooks.py         # Polyglot hook execution
│   └── rules.py         # Rules engine
├── sync/                # Config sync pipeline
│   ├── renderer.py      # Base renderer + context builder
│   ├── claude_md.py     # CLAUDE.md generator
│   ├── cursorrules.py   # .cursorrules generator
│   └── claude_settings.py # .claude/settings.json generator
├── learn/               # Learning system
│   ├── analyzer.py      # Project analysis
│   ├── research.py      # Topic/file learning
│   └── plan.py          # PRD generation
├── parallel/            # Multi-agent execution
│   ├── scheduler.py     # Task scheduling
│   └── executor.py      # Parallel worktree execution
└── commands/            # CLI commands
    ├── start/           # Product loop (SESRC)
    ├── sync_config.py   # Config sync (up sync)
    ├── plugin_cmd.py    # Plugin management
    ├── vibe.py          # save/reset/diff
    ├── agent.py         # Multi-agent worktrees
    └── provenance.py    # Lineage tracking
```

## Key Features

### SESRC Product Loop
- `up start` - Autonomous OBSERVE → CHECKPOINT → EXECUTE → VERIFY → COMMIT
- Circuit breaker (3 failures → OPEN → cooldown → HALF_OPEN)
- Automatic rollback on verification failure
- Memory hint injection from past solutions

### Plugin System
- 4 builtin plugins: memory, safety, verify, provenance
- 4 installed plugins: code-review, git-workflow, bisect, security-guidance
- Polyglot hooks (Python/Bash/JS) with JSON stdin, exit code semantics
- `tool_matcher` scoping (e.g., verify only fires on Write|Edit)
- `up sync` generates .claude/settings.json, CLAUDE.md, .cursorrules from plugins

### Persistent Memory
- ChromaDB semantic search with local embeddings (all-MiniLM-L6-v2)
- JSON fallback for fast operations or when ChromaDB unavailable
- Auto-record errors after consecutive failures
- Auto-recall past solutions on task failure
- Auto-index git commits into semantic memory
- Branch-aware knowledge tracking

### Provenance Tracking
- Content-addressed Merkle chain for AI operations
- Tracks: model, prompt hash, context hash, files modified, verification results
- Status lifecycle: pending → accepted/rejected/reverted

### Vibe Coding Safety Rails
- `up save` / `up reset` - Checkpoint and recovery
- `up diff` / `up review` - Mandatory review
- Doom loop detection (configurable threshold, default 3)

## Recent Changes

- **Plugin System (2026-02-25)**: Full plugin architecture — loader, registry, manifest validation, hook execution, scaffold command (US-001 through US-005)
- **Phases 2-6 Implementation (2026-02-25)**: Memory plugin, safety plugin, verify plugin, provenance plugin, installed plugins (code-review, git-workflow, bisect, security-guidance)
- **Claude Code Hooks Fix (2026-02-25)**: Fixed settings.json format (record/matcher), path resolution with $CLAUDE_PROJECT_DIR, tool_matcher scoping, HOOK_TYPE_MAP trimmed to pre_tool_use/post_tool_use only
- **Config Sync Pipeline (2026-02-25)**: `up sync` generates CLAUDE.md, .cursorrules, .claude/settings.json from plugin configs
- **Memory Module Refactor (2026-02-26)**: Deduplicated _manager.py — imports from entry.py and stores.py. Atomic writes for JSON store. Fixed auto_recall type handling.
- **Test Suite (2026-02-26)**: 534 tests passing across 59 test files

## Key Files

| File | Purpose |
|------|---------|
| docs/TARGET.md | North star: vision, success metrics, current focus |
| CLAUDE.md | AI instructions (skills, rules, handoff protocol) |
| docs/handoff/LATEST.md | Session continuity + suggested next steps |
| docs/CONTEXT.md | This file — current project state |
| docs/INDEX.md | Documentation quick reference |
| .up/state.json | Unified state (loop, context, agents, metrics) |
| .up/config.json | Configuration (thresholds, timeouts) |
| prd.json | Current PRD with user stories |
