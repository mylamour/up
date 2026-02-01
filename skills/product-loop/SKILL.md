---
name: product-loop-resilient
description: Resilient autonomous product development with circuit breakers, rollback, and self-healing
user-invocable: true
disable-model-invocation: false
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, TodoWrite
context: default
---

## Design Principles (SESRC)

| Principle | Implementation |
|-----------|----------------|
| **Stable** | Graceful degradation, fallback modes, watchdog |
| **Efficient** | Token budgets, incremental testing, caching |
| **Safe** | Input validation, path whitelisting, dry-run |
| **Reliable** | Timeouts, idempotency, verified rollback |
| **Cost-effective** | Early termination, ROI threshold, batching |

---

# Resilient Product Loop

Autonomous product development with **built-in resilience patterns** for production-grade reliability.

## Core Philosophy

```
OBSERVE → ORIENT → DECIDE → ACT → VERIFY → CHECKPOINT
```

Unlike basic loops, this skill:
- **Detects failures early** with health checks
- **Recovers gracefully** with rollback capabilities
- **Prevents infinite loops** with circuit breakers
- **Preserves progress** with state checkpoints

---

## Resilience Patterns

### 1. Circuit Breaker

Prevents infinite loops on persistent failures.

```
CIRCUIT_BREAKER:
  max_failures: 3           # Failures before circuit opens
  reset_timeout: 300        # Seconds before retry
  half_open_tests: 1        # Tests before fully closing

States:
  CLOSED  → Normal operation, failures counted
  OPEN    → Skip operation, return cached/default
  HALF_OPEN → Test with single request
```

**Implementation:**
```python
# Track in .loop_state.json
{
  "circuit_breaker": {
    "test": {"failures": 0, "state": "CLOSED", "last_failure": null},
    "build": {"failures": 0, "state": "CLOSED", "last_failure": null},
    "lint": {"failures": 0, "state": "CLOSED", "last_failure": null}
  }
}
```

### 2. Checkpoint & Rollback

Save state before risky operations, rollback on failure.

```
CHECKPOINT:
  before: [edit, write, delete]
  storage: .checkpoints/
  max_checkpoints: 5

ROLLBACK:
  trigger: [test_failure, build_error, corruption]
  strategy: git_stash | file_restore | full_reset
```

**Actions:**
- Before editing: `git stash push -m "checkpoint-{timestamp}"`
- On failure: `git stash pop` or `git checkout -- {file}`
- Track in `.loop_state.json`

### 3. Health Checks

Verify system state before proceeding.

```
HEALTH_CHECKS:
  pre_loop:
    - git_clean: "git status --porcelain"
    - deps_installed: "pip check || npm ls"
    - tests_exist: "find tests/ -name '*.py'"

  pre_phase:
    - disk_space: "df -h . | awk 'NR==2 {print $5}'"
    - memory: "free -m | awk 'NR==2 {print $4}'"

  post_change:
    - syntax_valid: "python -m py_compile {file}"
    - imports_work: "python -c 'import {module}'"
```

### 4. Retry with Exponential Backoff

Smart retries that don't waste resources.

```
RETRY:
  max_attempts: 3
  base_delay: 1        # seconds
  max_delay: 30        # seconds
  multiplier: 2        # exponential factor

  # Delay = min(base_delay * (multiplier ^ attempt), max_delay)
  # Attempt 1: 1s, Attempt 2: 2s, Attempt 3: 4s
```

---

## State Management

### State File: `.loop_state.json`

```json
{
  "version": "1.0",
  "last_updated": "2026-01-31T22:00:00Z",
  "session_id": "abc123",

  "phase": "BUILD",
  "iteration": 5,
  "tasks_completed": ["US-001", "US-002"],
  "tasks_remaining": ["US-003", "US-004"],

  "circuit_breaker": {
    "test": {"failures": 0, "state": "CLOSED"},
    "build": {"failures": 1, "state": "CLOSED"},
    "lint": {"failures": 0, "state": "CLOSED"}
  },

  "checkpoints": [
    {"id": "cp-001", "timestamp": "...", "files": ["src/main.py"]},
    {"id": "cp-002", "timestamp": "...", "files": ["src/utils.py"]}
  ],

  "health": {
    "last_check": "2026-01-31T22:00:00Z",
    "status": "HEALTHY",
    "issues": []
  },

  "metrics": {
    "total_edits": 15,
    "total_rollbacks": 1,
    "success_rate": 0.93
  }
}
```

---

## The Resilient Loop

```
RESILIENT PRODUCT LOOP:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PHASE 0: INITIALIZE
load_or_create_state(".loop_state.json")
run_health_checks()
if health_check_failed:
    attempt_self_heal()
    if still_unhealthy:
        EXIT with diagnostic report

while not COMPLETE:

    # PHASE 1: OBSERVE
    read_task_sources()          # TODO.md, prd.json, etc.
    identify_next_task()
    estimate_complexity()

    # PHASE 2: CHECKPOINT
    if task.risk_level >= MEDIUM:
        create_checkpoint()

    # PHASE 3: EXECUTE (with circuit breaker)
    if circuit_breaker.is_open("build"):
        log("Circuit open, skipping build")
        wait_or_skip()
    else:
        try:
            result = execute_task(task)
            circuit_breaker.record_success("build")
        except Error as e:
            circuit_breaker.record_failure("build")
            if should_rollback(e):
                rollback_to_checkpoint()
            if circuit_breaker.is_open("build"):
                notify_user("Build circuit opened after 3 failures")

    # PHASE 4: VERIFY
    run_verification_suite()     # tests, types, lint
    if verification_failed:
        attempt_fix_with_retry()
        if still_failing:
            rollback_to_checkpoint()
            mark_task_blocked()
            continue

    # PHASE 5: COMMIT
    update_state_file()
    update_todo_status()
    if milestone_complete:
        commit_changes()

    # PHASE 6: ANALYZE
    if iteration % 5 == 0:       # Every 5 iterations
        analyze_metrics()
        optimize_approach()

print("🎉 RESILIENT LOOP COMPLETE 🎉")
```

---

## Phase Details

### Phase 0: Initialize

```bash
# Load or create state
if [ -f ".loop_state.json" ]; then
    state=$(cat .loop_state.json)
    echo "Resuming from iteration $iteration"
else
    echo '{"version":"1.0","iteration":0}' > .loop_state.json
fi

# Health checks
git status --porcelain || echo "WARN: Git not clean"
python -c "import sys; sys.exit(0)" || echo "ERROR: Python broken"
```

**Self-Healing Actions:**
| Issue | Auto-Fix |
|-------|----------|
| Uncommitted changes | `git stash` |
| Broken imports | `pip install -r requirements.txt` |
| Missing test dir | `mkdir -p tests/` |
| Corrupted state | Reset to last checkpoint |

---

### Phase 1: Observe

Read task sources in priority order:

1. `.loop_state.json` - Resume interrupted task
2. `prd.json` - Structured user stories
3. `TODO.md` - Feature backlog
4. `ENHANCEMENTS.md` - Improvements

**Task Selection Algorithm:**
```python
def select_next_task(tasks):
    # Priority: blocked_dependencies < in_progress < high_priority < low_effort

    # 1. Resume any in-progress task
    in_progress = [t for t in tasks if t.status == "IN_PROGRESS"]
    if in_progress:
        return in_progress[0]

    # 2. Pick highest priority ready task
    ready = [t for t in tasks if t.dependencies_met]
    ready.sort(key=lambda t: (t.priority, t.effort))
    return ready[0] if ready else None
```

---

### Phase 2: Checkpoint

**When to Checkpoint:**
| Risk Level | Action |
|------------|--------|
| LOW | No checkpoint (simple edits) |
| MEDIUM | Git stash before changes |
| HIGH | Full file backup + git stash |
| CRITICAL | Branch + backup + notify user |

**Checkpoint Command:**
```bash
# Create checkpoint
CHECKPOINT_ID="cp-$(date +%s)"
git stash push -m "$CHECKPOINT_ID"
echo "Checkpoint: $CHECKPOINT_ID"

# Rollback if needed
git stash pop  # or git stash apply stash@{0}
```

---

### Phase 3: Execute with Circuit Breaker

```python
class CircuitBreaker:
    def __init__(self, name, max_failures=3):
        self.name = name
        self.max_failures = max_failures
        self.failures = 0
        self.state = "CLOSED"

    def execute(self, operation):
        if self.state == "OPEN":
            raise CircuitOpenError(f"{self.name} circuit is open")

        try:
            result = operation()
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            if self.failures >= self.max_failures:
                self.state = "OPEN"
                log(f"Circuit {self.name} OPENED after {self.failures} failures")
            raise
```

**Circuit States:**
```
CLOSED ──[failure]──► count++ ──[count >= 3]──► OPEN
   ▲                                              │
   │                                              │
   └────────────[success]◄────── HALF_OPEN ◄─────┘
                                   (after timeout)
```

---

### Phase 4: Verify with Retry

```python
def verify_with_retry(check_fn, max_attempts=3):
    """Retry verification with exponential backoff."""
    for attempt in range(max_attempts):
        try:
            return check_fn()
        except VerificationError as e:
            if attempt == max_attempts - 1:
                raise
            delay = min(2 ** attempt, 30)  # 1s, 2s, 4s... max 30s
            log(f"Retry {attempt+1}/{max_attempts} in {delay}s")
            time.sleep(delay)
```

**Verification Suite:**
```bash
# 1. Syntax check (fast, run first)
python -m py_compile src/**/*.py

# 2. Import check
python -c "from src import main"

# 3. Unit tests
pytest tests/ -x --tb=short

# 4. Type check
mypy src/ --ignore-missing-imports

# 5. Lint
ruff check src/
```

---

### Phase 5: Commit & Save State

```bash
# Update state file
cat > .loop_state.json << EOF
{
  "iteration": $((iteration + 1)),
  "phase": "COMPLETE",
  "last_task": "$TASK_ID",
  "timestamp": "$(date -Iseconds)"
}
EOF

# Update TODO status
sed -i "s/🔴 $TASK_ID/🟢 $TASK_ID/" TODO.md

# Commit if milestone complete
git add -A
git commit -m "feat: $TASK_SUMMARY"
```

---

### Phase 6: Analyze & Optimize

Run every 5 iterations to improve loop efficiency.

```python
def analyze_metrics():
    state = load_state()
    metrics = state.get("metrics", {})

    success_rate = metrics.get("success_rate", 1.0)
    rollback_count = metrics.get("total_rollbacks", 0)

    # Adjust strategy based on metrics
    if success_rate < 0.7:
        log("WARN: Low success rate, enabling conservative mode")
        enable_conservative_mode()

    if rollback_count > 3:
        log("WARN: Many rollbacks, increasing checkpoint frequency")
        increase_checkpoint_frequency()
```

---

## Error Recovery Strategies

### Recovery Decision Tree

```
ERROR DETECTED
     │
     ▼
┌─────────────────┐
│ Is it fixable?  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
   YES        NO
    │         │
    ▼         ▼
  Retry    Rollback
    │         │
    ▼         ▼
 Success?  Mark Blocked
    │         │
   YES/NO     ▼
    │      Next Task
    ▼
Continue/Rollback
```

### Error Categories

| Category | Example | Recovery |
|----------|---------|----------|
| Transient | Network timeout | Retry with backoff |
| Fixable | Syntax error | Auto-fix, retry |
| Blocking | Missing dependency | Install, retry |
| Fatal | Corrupted state | Rollback, notify |

### Auto-Fix Patterns

```python
AUTO_FIXES = {
    "SyntaxError": lambda f: run(f"ruff check --fix {f}"),
    "ImportError": lambda m: run(f"pip install {m}"),
    "IndentationError": lambda f: run(f"autopep8 -i {f}"),
    "TypeError": None,  # Requires manual fix
}
```

---

## Status Output

### Iteration Report

```
═══════════════════════════════════════════════════════════
 RESILIENT LOOP - Iteration #5
═══════════════════════════════════════════════════════════
 Health:     ✅ HEALTHY
 Circuit:    test=CLOSED build=CLOSED lint=CLOSED
 Checkpoint: cp-1706745600 (2 files)
───────────────────────────────────────────────────────────
 Task:       US-003 Add user authentication
 Status:     ✅ COMPLETE
 Duration:   45s
───────────────────────────────────────────────────────────
 Tests:      ✅ 42/42 passing
 Types:      ✅ No errors
 Lint:       ✅ No issues
───────────────────────────────────────────────────────────
 Progress:   [████████░░] 80% (4/5 tasks)
 Next:       US-004 Add password reset
═══════════════════════════════════════════════════════════
```

### RALPH_STATUS (Required)

```
RALPH_STATUS_BEGIN
{
  "STATUS": "IN_PROGRESS",
  "EXIT_SIGNAL": false,
  "HEALTH": "HEALTHY",
  "CIRCUIT_STATE": {"test": "CLOSED", "build": "CLOSED"},
  "CHECKPOINT": "cp-1706745600",
  "FILES_MODIFIED": ["src/auth.py"],
  "TASKS_COMPLETED": ["US-003"],
  "TASKS_REMAINING": 1,
  "ROLLBACKS": 0,
  "SUMMARY": "Add user authentication with JWT tokens"
}
RALPH_STATUS_END
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `/product-loop` | Start resilient loop |
| `/product-loop resume` | Resume from checkpoint |
| `/product-loop status` | Show current state |
| `/product-loop rollback` | Rollback last change |

---

## Start the Loop

1. Read `.loop_state.json` (or create if missing)
2. Run health checks
3. Load task from TODO.md or prd.json
4. Execute with circuit breaker protection
5. Verify and checkpoint
6. Continue until complete

---

## SESRC Implementation Details

### 1. Stable: Graceful Degradation

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

def select_mode(health_status, budget_remaining):
    if health_status == "HEALTHY" and budget_remaining > 50:
        return "FULL"
    elif budget_remaining > 20:
        return "REDUCED"
    return "MINIMAL"
```

### 2. Efficient: Cost & Budget Controls

```python
BUDGET = {
    "max_iterations": 20,
    "max_retries_per_task": 3,
    "max_total_rollbacks": 5,
    "timeout_per_operation": 120,  # seconds
}

def check_budget(state):
    if state["iteration"] >= BUDGET["max_iterations"]:
        return "BUDGET_EXHAUSTED"
    if state["metrics"]["total_rollbacks"] >= BUDGET["max_total_rollbacks"]:
        return "TOO_MANY_ROLLBACKS"
    return "OK"
```

**Incremental Testing:**
```bash
# Only test affected files
pytest tests/ -x --lf          # Last failed first
pytest tests/ --co -q | head   # Show what would run
```

### 3. Safe: Input Validation & Dry-Run

```python
ALLOWED_PATHS = ["src/", "tests/", "docs/"]
FORBIDDEN_PATTERNS = [".env", "credentials", "secret", ".git/"]

def validate_file_path(path):
    # Check whitelist
    if not any(path.startswith(p) for p in ALLOWED_PATHS):
        raise SafetyError(f"Path not in whitelist: {path}")
    # Check blacklist
    if any(p in path for p in FORBIDDEN_PATTERNS):
        raise SafetyError(f"Forbidden pattern in path: {path}")
    return True
```

**Dry-Run Mode:**
```bash
# Preview changes without applying
DRY_RUN=true /product-loop

# In dry-run mode:
# - Edit → prints diff instead of writing
# - Bash → prints command instead of executing
# - Git → skips commit/push
```

### 4. Reliable: Timeouts & Idempotency

```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def run_with_timeout(fn, timeout_sec=120):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_sec)
    try:
        return fn()
    finally:
        signal.alarm(0)
```

**Idempotency Check:**
```python
def is_already_done(task_id, state):
    return task_id in state.get("tasks_completed", [])
```

### 5. Cost-effective: Early Termination

```python
def should_terminate_early(state, task):
    # Stop if ROI is too low
    if task.effort == "HIGH" and task.priority == "LOW":
        return True, "Low ROI task"

    # Stop if budget exhausted
    if state["iteration"] >= BUDGET["max_iterations"]:
        return True, "Budget exhausted"

    # Stop if too many failures
    if state["metrics"]["success_rate"] < 0.5:
        return True, "Success rate too low"

    return False, None
```

**Batch Operations:**
```bash
# Batch multiple small commits
git add -A
git commit -m "feat: implement US-001, US-002, US-003"
```
