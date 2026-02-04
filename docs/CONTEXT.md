# Project Context

**Updated**: 2026-02-04
**Status**: ✅ Active Development
**Version**: 0.4.0

---

## Current State

| Aspect | Status |
|--------|--------|
| Phase | Implementation Complete |
| Focus | Verifiable AI-assisted development |
| Blockers | None |

## Architecture

```
.up/
├── state.json           # Unified state (loop, context, agents, metrics)
├── checkpoints/         # Checkpoint metadata
├── provenance/          # AI operation lineage tracking
└── config.json          # Configuration

src/up/
├── core/                # Core modules
│   ├── state.py         # Unified state management
│   ├── checkpoint.py    # Git checkpoint operations
│   └── provenance.py    # AI operation tracking
├── learn/               # Refactored learning system
│   ├── analyzer.py      # Project analysis
│   ├── research.py      # Topic/file learning
│   └── plan.py          # PRD generation
└── commands/            # CLI commands
    ├── vibe.py          # save/reset/diff
    ├── agent.py         # Multi-agent worktrees
    ├── bisect.py        # Bug hunting
    ├── provenance.py    # Lineage tracking
    ├── review.py        # AI code review
    └── branch.py        # Branch hierarchy
```

## Key Features

### Vibe Coding Safety Rails
- `up save` / `up reset` - Checkpoint and recovery
- `up diff` / `up review` - Mandatory review
- Doom loop detection (3 consecutive failures)

### Multi-Agent Orchestration
- `up start --parallel` - Parallel worktree execution
- `up agent spawn/merge` - Agent management
- Branch hierarchy enforcement

### Provenance Tracking
- Content-addressed storage
- AI operation lineage
- Verification tracking

## Recent Changes

- Implemented unified state management (F-001 to F-006)
- Added vibe safety commands (US-004 to US-006)
- Added multi-agent support (US-007 to US-010)
- Added debugging tools (US-011 to US-012)
- Added provenance tracking (US-013 to US-015)
- Added AI review and branch hierarchy (US-016 to US-017)
- Refactored learn.py into modular structure
- Added auto-commit with verification

## Key Files

| File | Purpose |
|------|---------|
| CLAUDE.md | AI instructions |
| docs/handoff/LATEST.md | Session continuity |
| .claude/skills/learning-system/prd.json | Task tracking |
| docs/roadmap/IMPROVEMENT_PLAN.md | Development roadmap |
