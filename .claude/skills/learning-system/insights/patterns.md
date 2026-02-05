# Patterns Extracted

**Generated**: 2026-02-04
**Updated**: 2026-02-04
**Files Analyzed**: 2
**Method**: claude CLI + manual analysis

---

## Part A: Git Design Philosophy Patterns

### Core Principles (from Git internals)

| Principle | Description | Application to Vibe Coding |
|-----------|-------------|---------------------------|
| **Content-Addressable** | Store by SHA hash of content | Track vibe state by content hash |
| **Merkle Tree** | Parent hash in child = chain integrity | Chain checkpoints like Git commits |
| **Distributed** | Every clone is complete | Each agent has full context |
| **Atomic Commits** | One logical change per commit | Squash AI mess into clean history |
| **Branch Hierarchy** | Changes flow upward only | experiment → feature → develop → main |

### Scaling Patterns (from Linux kernel workflow)

| Pattern | Description | Team Size |
|---------|-------------|-----------|
| **Integration Branches** | seen → next → master → maint | 10+ devs |
| **Merge Upward Rule** | Fixes go to oldest branch, merge up | All sizes |
| **Worktree Isolation** | Parallel working directories | 4+ devs |
| **Automated Bisect** | Binary search for bug commits | All sizes |
| **Squash Before Merge** | Clean history from AI commits | All sizes |

---

## Part B: Vibe Coding Patterns

### From 2026-02-04_git_for_ai_vibe_coding.md

| Pattern | Description |
|---------|-------------|
| **Commit-Before-Prompt** | Always commit clean state before AI generation |
| **Hard Reset Recovery** | Reset immediately on bad generation vs "prompting out" |
| **Git Worktrees** | Parallel development with multiple AI agents |
| **Specification-Driven** | Use specs/rules files before code generation |
| **Version Loop** | Checkpoint → Prompt → Diff → Accept/Reset |
| **Shadow Branch** | Experiment on ephemeral branch, squash to feature |

---

## Part C: Best Practices

### Safety Practices
1. **Never "prompt your way out"** - Reset and refine prompt
2. **Review every diff** - Mandatory before accepting changes
3. **Checkpoint before risk** - Auto-commit/stash before AI ops
4. **Detect doom loops** - Warn after 2-3 failed prompts

### Git Practices
1. **Commit atomically** - One logical change per commit
2. **Squash AI commits** - Clean history before merge
3. **Use worktrees** - Prevent agent collision
4. **Bisect for debugging** - O(log n) bug finding

### Provenance Practices
1. **Log prompts** - Store alongside commits
2. **Track model version** - claude-3.5, gpt-4, etc.
3. **Record confidence** - AI's self-assessment
4. **Chain state hashes** - Merkle-style integrity

---

## Part D: Implementation Architecture

### The Vibe Version Loop
```
┌─────────────────────────────────────────────────────────┐
│  CHECKPOINT → PROMPT → DIFF → ACCEPT/RESET → REPEAT    │
│      │          │        │         │                    │
│  git commit   AI work   Review   git commit             │
│  git tag               mandatory  OR git reset          │
└─────────────────────────────────────────────────────────┘
```

### Multi-Agent Architecture
```
project/
├── .git/                    # Shared repository
├── main/                    # Production (protected)
└── .worktrees/
    ├── agent-frontend/      # Agent 1
    ├── agent-backend/       # Agent 2
    └── agent-tests/         # Agent 3
```

### State Chain (Merkle-style)
```
Checkpoint 1 ──► Checkpoint 2 ──► Checkpoint 3
   hash_1    ◄──    hash_2    ◄──    hash_3
             (includes parent hash)
```

---

## Part E: Gaps Identified

| Gap | Impact | Priority |
|-----|--------|----------|
| **No checkpoint command** | Manual git saves, easy to forget | P0 |
| **No worktree orchestration** | Can't run parallel agents | P0 |
| **No provenance tracking** | Lost context for debugging | P1 |
| **No automated bisect** | Manual bug hunting in 100+ commits | P1 |
| **No doom loop detection** | Waste tokens on bad prompts | P1 |
| **No squash helper** | Messy AI commit history | P2 |
| **No adversarial review** | Single-agent blind spots | P2 |

---

## Part F: Action Items

### Phase 1: Safety Rails (P0)
- [x] Pre-prompt checkpoint command
- [x] Context budget tracking
- [ ] `up vibe save` - Quick checkpoint
- [ ] `up vibe reset` - Instant recovery
- [ ] `up vibe diff` - Mandatory review step

### Phase 2: Multi-Agent (P0)
- [ ] `up agent spawn` - Create worktree environment
- [ ] `up agent status` - List active agents
- [ ] `up agent merge` - Squash and merge agent work
- [ ] `up agent cleanup` - Remove completed worktrees

### Phase 3: Debugging (P1)
- [ ] `up bisect` - Automated bug hunting
- [ ] `up history squash` - Clean up AI commits
- [ ] Doom loop detection with warning

### Phase 4: Provenance (P1)
- [ ] Prompt logging alongside commits
- [ ] Model/confidence tracking
- [ ] State chain with hash integrity

### Phase 5: Advanced (P2)
- [ ] Adversarial AI review
- [ ] Semantic merge (AST-aware)
- [ ] Merge queue for conflicts

