# SESRC Resilient Product Loop Design

**Created**: 2026-01-31
**Updated**: 2026-02-21
**Status**: 🔄 Active
**Source**: Extracted from original Ralph Hybrid skill design

---

## Design Principles (SESRC)

| Principle | Implementation |
|-----------|----------------|
| **Stable** | Graceful degradation, fallback modes, watchdog |
| **Efficient** | Token budgets, incremental testing, caching |
| **Safe** | Input validation, path whitelisting, dry-run |
| **Reliable** | Timeouts, idempotency, verified rollback |
| **Cost-effective** | Early termination, ROI threshold, batching |

## Core Loop

```
OBSERVE → ORIENT → DECIDE → ACT → VERIFY → CHECKPOINT
```

Key properties:
- **Detects failures early** with health checks
- **Recovers gracefully** with rollback capabilities
- **Prevents infinite loops** with circuit breakers
- **Preserves progress** with state checkpoints

---

## Resilience Patterns

### 1. Circuit Breaker

```
CIRCUIT_BREAKER:
  max_failures: 3
  reset_timeout: 300s
  half_open_tests: 1

States:
  CLOSED    → Normal operation, failures counted
  OPEN      → Skip operation, return cached/default
  HALF_OPEN → Test with single request

State transitions:
  CLOSED ──[failure]──► count++ ──[count >= 3]──► OPEN
     ▲                                              │
     │                                              │
     └────────────[success]◄────── HALF_OPEN ◄─────┘
                                     (after timeout)
```

Implementation: `src/up/core/state.py` (`CircuitBreakerState`)

### 2. Checkpoint & Rollback

```
CHECKPOINT:
  before: [edit, write, delete]
  storage: .up/checkpoints/
  max_checkpoints: 50

ROLLBACK:
  trigger: [test_failure, build_error, corruption]
  strategy: git tag + reset
```

Implementation: `src/up/core/checkpoint.py` (`CheckpointManager`)

### 3. Health Checks

```
HEALTH_CHECKS:
  pre_loop:
    - git_clean: "git status --porcelain"
    - deps_installed: "pip check || npm ls"
    - tests_exist: "find tests/ -name '*.py'"
  post_change:
    - syntax_valid: "python -m py_compile {file}"
    - imports_work: "python -c 'import {module}'"
```

### 4. Retry with Exponential Backoff

```
RETRY:
  max_attempts: 3
  base_delay: 1s
  max_delay: 30s
  multiplier: 2
  # Delay = min(base_delay * (multiplier ^ attempt), max_delay)
```

---

## Degradation Modes

```python
DEGRADATION_MODES = {
    "FULL": {
        "tests": True, "types": True, "lint": True,
        "checkpoint": "always", "analyze": True
    },
    "REDUCED": {
        "tests": True, "types": False, "lint": False,
        "checkpoint": "on_risk", "analyze": False
    },
    "MINIMAL": {
        "tests": "critical_only", "types": False, "lint": False,
        "checkpoint": "never", "analyze": False
    }
}
```

Mode selection based on health status and remaining budget.

## Budget Controls

```python
BUDGET = {
    "max_iterations": 20,
    "max_retries_per_task": 3,
    "max_total_rollbacks": 5,
    "timeout_per_operation": 120,  # seconds
}
```

Configuration: `.up/config.json`

## Error Recovery

| Category | Example | Recovery |
|----------|---------|----------|
| Transient | Network timeout | Retry with backoff |
| Fixable | Syntax error | Auto-fix, retry |
| Blocking | Missing dependency | Install, retry |
| Fatal | Corrupted state | Rollback, notify |

## Safety: Path Validation

```python
ALLOWED_PATHS = ["src/", "tests/", "docs/"]
FORBIDDEN_PATTERNS = [".env", "credentials", "secret", ".git/"]
```

## Implementation Map

| Concept | File |
|---------|------|
| Unified state + circuit breaker | `src/up/core/state.py` |
| Checkpoint/rollback | `src/up/core/checkpoint.py` |
| Provenance tracking | `src/up/core/provenance.py` |
| Product loop | `src/up/commands/start/loop.py` |
| Parallel execution | `src/up/parallel_scheduler.py` |
| AI CLI integration | `src/up/ai_cli.py` |
