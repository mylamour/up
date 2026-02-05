---
name: product-loop
description: Resilient development with SESRC principles
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, TodoWrite
version: "1.0.0"
min-claude-version: "2024.01"
---

# Resilient Product Loop

Autonomous product development with **built-in resilience patterns** for production-grade reliability.

## SESRC Principles

| Principle | Implementation |
|-----------|----------------|
| **Stable** | Graceful degradation, fallback modes |
| **Efficient** | Token budgets, incremental testing |
| **Safe** | Input validation, path whitelisting |
| **Reliable** | Timeouts, idempotency, rollback |
| **Cost-effective** | Early termination, ROI threshold |

## Core Loop

```
OBSERVE → CHECKPOINT → EXECUTE → VERIFY → COMMIT
```

## Commands

### Skill Commands (for AI)
| Command | Description |
|---------|-------------|
| `/product-loop` | Start the development loop |
| `/product-loop resume` | Resume from last checkpoint |
| `/product-loop status` | Show current state |

### CLI Commands (for users)
| Command | Description |
|---------|-------------|
| `up start` | Start the product loop |
| `up start --resume` | Resume from checkpoint |
| `up start --parallel` | Run tasks in parallel |
| `up save` | Create checkpoint |
| `up reset` | Rollback to checkpoint |
| `up status` | Show current state |

---

## Circuit Breaker

Prevents infinite loops on persistent failures.

| State | Description |
|-------|-------------|
| CLOSED | Normal operation, failures counted |
| HALF_OPEN | Testing after cooldown |
| OPEN | Halted - requires intervention |

**Thresholds:**
- Max 3 consecutive failures → circuit opens
- Reset after 5 minutes cooldown
- Requires 2 successes to close

---

## Phase Details

### Phase 1: OBSERVE

Read task sources in priority order:
1. `.up/state.json` - Resume interrupted task (unified state)
2. `prd.json` - Structured user stories
3. `TODO.md` - Feature backlog

### Phase 2: CHECKPOINT

Before risky operations:
- Create git checkpoint via `up save`
- Record modified files
- Save state to `.up/state.json`

### Phase 3: EXECUTE

Execute task with circuit breaker:
- Check circuit state before operation
- Record success/failure
- Open circuit on repeated failures

### Phase 4: VERIFY

Run verification suite:
1. Syntax check (fast)
2. Import check
3. Unit tests
4. Type check
5. Lint

### Phase 5: COMMIT

On success:
- Update state file
- Update TODO status
- Git commit if milestone complete

---

## State File: `.up/state.json`

The unified state file stores loop state, context budget, agent state, and metrics:

```json
{
  "version": "2.0",
  "loop": {
    "iteration": 5,
    "phase": "VERIFY",
    "current_task": "US-003",
    "tasks_completed": ["US-001", "US-002"],
    "tasks_failed": [],
    "last_checkpoint": "cp-20260204-123456"
  },
  "circuit_breakers": {
    "task": {"failures": 0, "state": "CLOSED"}
  },
  "metrics": {
    "total_tasks": 15,
    "total_rollbacks": 1,
    "success_rate": 0.93
  }
}
```

---

## Recovery Strategies

| Error Type | Recovery |
|------------|----------|
| Syntax error | Auto-fix with linter |
| Test failure | Rollback, retry |
| Build error | Rollback, mark blocked |
| Circuit open | Wait or notify user |

---

## Budget Controls

```
max_iterations: 20
max_retries_per_task: 3
max_total_rollbacks: 5
timeout_per_operation: 120s
```

---

## Quick Start

1. Ensure `prd.json` or `TODO.md` exists with tasks
2. Run `/product-loop`
3. Loop will:
   - Pick highest priority task
   - Create checkpoint
   - Execute with circuit breaker
   - Verify changes
   - Commit on success

---

## Context Budget Integration

This skill respects context budget:
- Checks `.claude/context_budget.json` before operations
- Warns when approaching limits
- Creates handoff at critical threshold

---

## Implementation Note

The actual implementation is in `src/up/core/`:
- `state.py` - Unified state management with circuit breaker
- `checkpoint.py` - Git checkpoint operations
- `provenance.py` - AI operation tracking

The Python files in this skill folder (`circuit_breaker.py`, `state_manager.py`) are **reference implementations** for understanding the patterns. The CLI uses the implementations in `src/up/core/`.

---

## Status Output Format

```
═══════════════════════════════════════════
 PRODUCT LOOP - Iteration #5
═══════════════════════════════════════════
 Health:     ✅ HEALTHY
 Circuit:    test=CLOSED build=CLOSED
 Task:       US-003 Add authentication
 Status:     ✅ COMPLETE
───────────────────────────────────────────
 Tests:      ✅ 42/42 passing
 Progress:   [████████░░] 80%
═══════════════════════════════════════════
```
