# up-cli Improvement Plan

**Created**: 2026-02-04
**Status**: 📋 Ready for Implementation
**Version**: 2.0

---

## Vision Alignment

> **up** helps you build any tool in a **verifiable** and **observable** way using **vibe coding**, resulting in stable, high-performance, and modern software engineering.

### Three Pillars

| Pillar | Meaning | Features |
|--------|---------|----------|
| **Verifiable** | Every change can be tested, traced, and validated | Automated tests, bisect, verification gates, clean history |
| **Observable** | Full visibility into what's happening | Status dashboard, provenance tracking, event system, metrics |
| **Vibe Coding** | AI-assisted development with safety rails | Checkpoints, multi-agent, doom loop detection, context budget |

---

## Critical Issues (Must Fix First)

### Issue 1: State File Fragmentation (CRITICAL)

**Current State:**
```
.loop_state.json           # Product loop
.parallel_state.json       # Parallel execution
.worktrees/*/.agent_state.json  # Per-agent
.claude/context_budget.json     # Context tracking
.up/config.json                 # Event config
prd.json                        # Tasks
```

**Problem:** 6+ state files, hard to debug, inconsistent, confusing.

**Solution:** Unified state in `.up/` directory.

### Issue 2: learn.py Monolith (CRITICAL)

**Current State:** 1742 lines with 6+ distinct features crammed into one file.

**Problem:** Unmaintainable, hard to test, violates single responsibility.

**Solution:** Split into command group with submodules.

### Issue 3: Flat Command Structure (HIGH)

**Current State:** 10 top-level commands, some with hidden subcommands.

**Problem:** Poor discoverability, namespace collision, doesn't scale.

**Solution:** Logical command groups aligned with pillars.

### Issue 4: Duplicate Checkpoint Logic (MEDIUM)

**Current State:** 
- `start.py` has `_create_checkpoint()`
- `git/worktree.py` has `create_checkpoint()`
- Planned `up vibe save` would be third

**Problem:** Inconsistent behavior, maintenance burden.

**Solution:** Single checkpoint implementation in core module.

---

## Proposed Architecture

### Command Structure (Aligned with Pillars)

```
up
│
├── VERIFIABLE ─────────────────────────────────────
│   ├── up verify              # Run verification suite
│   ├── up test                # Run tests with coverage
│   └── up bisect              # Find bug-introducing commit
│
├── OBSERVABLE ─────────────────────────────────────
│   ├── up status              # System health overview
│   ├── up dashboard           # Live monitoring
│   ├── up history             # Git history with provenance
│   └── up provenance          # AI generation context
│
├── VIBE CODING ────────────────────────────────────
│   ├── up start               # Start product loop
│   │   ├── --parallel         # Multi-agent mode
│   │   └── --task <id>        # Specific task
│   │
│   ├── up save                # Checkpoint (was: vibe save)
│   ├── up reset               # Restore checkpoint
│   ├── up diff                # Review AI changes
│   │
│   ├── up agent               # Multi-agent orchestration
│   │   ├── spawn <name>       # Create worktree
│   │   ├── status             # List agents
│   │   ├── merge <name>       # Squash & merge
│   │   └── cleanup            # Remove worktrees
│   │
│   └── up learn               # Research & planning
│       ├── research <topic>   # Web research
│       ├── analyze            # Analyze findings
│       └── plan               # Generate PRD
│
├── PROJECT ────────────────────────────────────────
│   ├── up init                # Initialize project
│   ├── up new <name>          # Create new project
│   └── up sync                # Sync all systems
│
└── MEMORY ─────────────────────────────────────────
    ├── up memory search       # Semantic search
    ├── up memory record       # Record entry
    └── up memory sync         # Sync to storage
```

### Unified State Architecture

```
.up/                              # Single state directory
├── state.json                    # Unified state file
│   {
│     "version": "2.0",
│     "loop": { ... },            # Product loop state
│     "context": { ... },         # Context budget
│     "agents": { ... },          # Active worktrees
│     "circuit_breaker": { ... }, # Circuit states
│     "metrics": { ... }          # Performance metrics
│   }
├── config.json                   # User configuration
├── provenance/                   # AI provenance logs
│   └── <commit-sha>.json
├── checkpoints/                  # Checkpoint metadata
│   └── <checkpoint-id>.json
└── memory/                       # Long-term memory (unchanged)
    └── ...
```

### Module Architecture

```
src/up/
├── cli.py                        # Entry point (simplified)
├── state.py                      # NEW: Unified state management
├── checkpoint.py                 # NEW: Unified checkpoint logic
│
├── commands/
│   ├── __init__.py
│   ├── project/                  # up init, up new
│   │   ├── __init__.py
│   │   ├── init.py
│   │   └── new.py
│   ├── loop/                     # up start, up save, up reset
│   │   ├── __init__.py
│   │   ├── start.py              # Simplified, uses parallel.py
│   │   ├── save.py               # Checkpoint command
│   │   ├── reset.py              # Reset command
│   │   └── diff.py               # Diff review command
│   ├── agent/                    # up agent spawn/status/merge
│   │   ├── __init__.py
│   │   ├── spawn.py
│   │   ├── status.py
│   │   ├── merge.py
│   │   └── cleanup.py
│   ├── learn/                    # up learn research/analyze/plan
│   │   ├── __init__.py
│   │   ├── research.py
│   │   ├── analyze.py
│   │   └── plan.py
│   ├── verify/                   # up verify, up test, up bisect
│   │   ├── __init__.py
│   │   ├── verify.py
│   │   ├── test.py
│   │   └── bisect.py
│   ├── observe/                  # up status, up dashboard, up provenance
│   │   ├── __init__.py
│   │   ├── status.py
│   │   ├── dashboard.py
│   │   └── provenance.py
│   └── memory/                   # Unchanged
│       └── ...
│
├── core/                         # Shared core modules
│   ├── state.py                  # Unified state
│   ├── checkpoint.py             # Checkpoint logic
│   ├── git.py                    # Git operations
│   └── ai.py                     # AI CLI integration
│
└── git/                          # Git utilities (exists)
    └── worktree.py
```

---

## Implementation Plan

### Sprint 0: Foundation (Fix Critical Issues)

**Goal:** Clean foundation before adding features.

| Task | Priority | Effort | Description |
|------|----------|--------|-------------|
| F-001 | CRITICAL | Medium | Create unified `state.py` module |
| F-002 | CRITICAL | Low | Migrate `.loop_state.json` to `.up/state.json` |
| F-003 | CRITICAL | Low | Migrate `context_budget.json` to `.up/state.json` |
| F-004 | HIGH | Medium | Create unified `checkpoint.py` module |
| F-005 | HIGH | Low | Update `start.py` to use new state/checkpoint |
| F-006 | MEDIUM | Low | Add backwards compatibility layer |

**Deliverable:** Single state file, single checkpoint implementation.

---

### Sprint 1: Safety Rails (Phase 1 from PRD)

**Goal:** Core vibe coding safety features.

| Task | PRD ID | Priority | Description |
|------|--------|----------|-------------|
| S1-001 | US-004 | HIGH | `up save` - Quick checkpoint command |
| S1-002 | US-005 | HIGH | `up reset` - Instant recovery |
| S1-003 | US-006 | MEDIUM | `up diff` - Review AI changes |
| S1-004 | US-002 | HIGH | Doom loop detection in `start.py` |
| S1-005 | - | HIGH | Integrate commands into CLI |

**Deliverable:** Working `up save`, `up reset`, `up diff` commands.

---

### Sprint 2: Multi-Agent (Phase 2 from PRD)

**Goal:** Parallel AI agent orchestration.

| Task | PRD ID | Priority | Description |
|------|--------|----------|-------------|
| S2-001 | US-007 | HIGH | `up agent spawn` - Create worktree |
| S2-002 | US-008 | HIGH | `up agent status` - Monitor agents |
| S2-003 | US-009 | HIGH | `up agent merge` - Squash & merge |
| S2-004 | US-010 | MEDIUM | `up agent cleanup` - Remove worktrees |
| S2-005 | - | MEDIUM | Enhance `up start --parallel` |

**Deliverable:** Full multi-agent workflow.

---

### Sprint 3: Debugging & History (Phase 3 from PRD)

**Goal:** Verifiable development through debugging tools.

| Task | PRD ID | Priority | Description |
|------|--------|----------|-------------|
| S3-001 | US-011 | HIGH | `up bisect` - Automated bug hunting |
| S3-002 | US-012 | MEDIUM | `up history squash` - Clean commits |
| S3-003 | - | MEDIUM | `up verify` - Run verification suite |
| S3-004 | - | LOW | `up test` - Enhanced test runner |

**Deliverable:** Automated debugging and clean history tools.

---

### Sprint 4: Architecture Refactor

**Goal:** Sustainable architecture for growth.

| Task | Priority | Effort | Description |
|------|----------|--------|-------------|
| A-001 | HIGH | High | Split `learn.py` into `learn/` submodules |
| A-002 | HIGH | Medium | Reorganize commands into groups |
| A-003 | MEDIUM | Medium | Update CLI help and documentation |
| A-004 | MEDIUM | Low | Add command aliases for compatibility |

**Deliverable:** Clean, modular architecture.

---

### Sprint 5: Provenance & Observability (Phase 4 from PRD)

**Goal:** Full observability of AI-generated code.

| Task | PRD ID | Priority | Description |
|------|--------|----------|-------------|
| S5-001 | US-013 | MEDIUM | Provenance logging for commits |
| S5-002 | US-014 | MEDIUM | `up provenance show` - Query context |
| S5-003 | - | LOW | Enhanced `up history` with provenance |
| S5-004 | US-015 | LOW | Content-addressed state (optional) |

**Deliverable:** Full AI provenance tracking.

---

### Sprint 6: Advanced Features (Phase 5 from PRD)

**Goal:** Enterprise-grade vibe coding.

| Task | PRD ID | Priority | Description |
|------|--------|----------|-------------|
| S6-001 | US-016 | LOW | Adversarial AI review |
| S6-002 | US-017 | LOW | Branch hierarchy enforcement |
| S6-003 | - | LOW | Merge queue integration |

**Deliverable:** Advanced features for large teams.

---

## Task Dependency Graph

```
Sprint 0 (Foundation)
    │
    ├── F-001 (state.py) ────┬──► F-002 (migrate loop state)
    │                        └──► F-003 (migrate context)
    │
    └── F-004 (checkpoint.py) ──► F-005 (update start.py)
                │
                ▼
Sprint 1 (Safety Rails)
    │
    ├── S1-001 (up save) ◄──── depends on F-004
    ├── S1-002 (up reset) ◄─── depends on F-004
    ├── S1-003 (up diff)
    └── S1-004 (doom loop)
                │
                ▼
Sprint 2 (Multi-Agent)
    │
    ├── S2-001 (agent spawn) ◄── depends on F-001
    ├── S2-002 (agent status)
    ├── S2-003 (agent merge) ◄── depends on S1-001 (checkpoint)
    └── S2-004 (agent cleanup)
                │
                ▼
Sprint 3 (Debugging)          Sprint 4 (Refactor)
    │                              │
    ├── S3-001 (bisect)           ├── A-001 (split learn.py)
    ├── S3-002 (squash)           ├── A-002 (reorg commands)
    └── S3-003 (verify)           └── A-003 (update docs)
                │                      │
                └──────────┬───────────┘
                           ▼
                Sprint 5 (Provenance)
                    │
                    ├── S5-001 (logging)
                    └── S5-002 (query)
                           │
                           ▼
                Sprint 6 (Advanced)
```

---

## Quick Reference: PRD Task Mapping

| PRD ID | Sprint | Task | Status |
|--------|--------|------|--------|
| US-001 | - | Pre-prompt checkpoint | ✅ Done |
| US-002 | S1 | Doom loop detection | 🔲 Pending |
| US-003 | - | Context budget tracking | ✅ Done |
| US-004 | S1 | `up save` | 🔲 Pending |
| US-005 | S1 | `up reset` | 🔲 Pending |
| US-006 | S1 | `up diff` | 🔲 Pending |
| US-007 | S2 | `up agent spawn` | 🔲 Pending |
| US-008 | S2 | `up agent status` | 🔲 Pending |
| US-009 | S2 | `up agent merge` | 🔲 Pending |
| US-010 | S2 | `up agent cleanup` | 🔲 Pending |
| US-011 | S3 | `up bisect` | 🔲 Pending |
| US-012 | S3 | `up history squash` | 🔲 Pending |
| US-013 | S5 | Provenance logging | 🔲 Pending |
| US-014 | S5 | `up provenance show` | 🔲 Pending |
| US-015 | S5 | Content-addressed state | 🔲 Pending |
| US-016 | S6 | Adversarial AI review | 🔲 Pending |
| US-017 | S6 | Branch hierarchy | 🔲 Pending |

---

## Success Metrics

| Metric | Current | Sprint 2 Target | Sprint 6 Target |
|--------|---------|-----------------|-----------------|
| State files | 6 | 1 | 1 |
| Max command file LOC | 1742 | 500 | 300 |
| Top-level commands | 10 | 8 | 8 |
| Test coverage | ? | 60% | 80% |
| Time to recover bad AI | 30-60s | <5s | <5s |
| Parallel agents | 1 | 5 | 10 |

---

## Implementation Order (Recommended)

```
Week 1: Sprint 0 (Foundation)
        ├── Create state.py
        ├── Create checkpoint.py
        └── Migrate existing state files

Week 2: Sprint 1 (Safety Rails)
        ├── up save
        ├── up reset
        ├── up diff
        └── Doom loop detection

Week 3: Sprint 2 (Multi-Agent)
        ├── up agent spawn
        ├── up agent status
        ├── up agent merge
        └── up agent cleanup

Week 4: Sprint 3 + Sprint 4
        ├── up bisect
        ├── Split learn.py
        └── Reorganize commands

Week 5+: Sprint 5 + Sprint 6
        ├── Provenance tracking
        └── Advanced features
```

---

## Getting Started

To begin implementation:

```bash
# Start with foundation
up start --task F-001

# Or run the full plan
up start --all
```

The plan is designed so each sprint builds on the previous one. **Do not skip Sprint 0** - the foundation fixes are critical for everything else.

---

*Generated by up-cli learning system*
