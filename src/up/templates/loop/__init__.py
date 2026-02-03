"""Product-loop system templates."""

from pathlib import Path
from datetime import date


def create_loop_system(target_dir: Path, ai_target: str, force: bool = False) -> None:
    """Create the product-loop system structure."""
    # Determine skill directory based on AI target
    if ai_target in ("claude", "both"):
        skill_dir = target_dir / ".claude/skills/product-loop"
    else:
        skill_dir = target_dir / ".cursor/skills/product-loop"

    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create files
    _create_skill_md(skill_dir, force)
    _create_circuit_breaker(skill_dir, force)
    _create_state_manager(skill_dir, force)
    _create_loop_state(target_dir, force)


def _write_file(path: Path, content: str, force: bool) -> None:
    """Write file if it doesn't exist or force is True."""
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _create_skill_md(skill_dir: Path, force: bool) -> None:
    """Create SKILL.md for product-loop."""
    content = """---
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

| Command | Description |
|---------|-------------|
| `/product-loop` | Start the development loop |
| `/product-loop resume` | Resume from last checkpoint |
| `/product-loop status` | Show current state |
| `/product-loop rollback` | Rollback last change |

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
1. `.loop_state.json` - Resume interrupted task
2. `prd.json` - Structured user stories
3. `TODO.md` - Feature backlog

### Phase 2: CHECKPOINT

Before risky operations:
- Create git stash checkpoint
- Record modified files
- Save state to `.loop_state.json`

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

## State File: `.loop_state.json`

```json
{
  "version": "1.0",
  "iteration": 5,
  "phase": "VERIFY",
  "current_task": "US-003",
  "tasks_completed": ["US-001", "US-002"],
  "circuit_breaker": {
    "test": {"failures": 0, "state": "CLOSED"},
    "build": {"failures": 0, "state": "CLOSED"}
  },
  "checkpoints": [],
  "metrics": {
    "total_edits": 15,
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
"""
    _write_file(skill_dir / "SKILL.md", content, force)


def _create_circuit_breaker(skill_dir: Path, force: bool) -> None:
    """Create circuit breaker implementation."""
    content = '''#!/usr/bin/env python3
"""
Circuit Breaker for Product Loop

Prevents runaway loops by tracking failures and opening circuit.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class CircuitState(Enum):
    CLOSED = "CLOSED"
    HALF_OPEN = "HALF_OPEN"
    OPEN = "OPEN"


@dataclass
class CircuitConfig:
    max_failures: int = 3
    reset_timeout_seconds: int = 300
    half_open_success_threshold: int = 2


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, name: str, state_dir: Optional[Path] = None, config: Optional[CircuitConfig] = None):
        self.name = name
        self.state_dir = state_dir or Path.cwd()
        self.config = config or CircuitConfig()
        self.state_file = self.state_dir / f".circuit_{name}.json"
        self._load()
    
    def _load(self) -> None:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.state = CircuitState(data.get("state", "CLOSED"))
                self.failures = data.get("failures", 0)
                self.successes = data.get("successes", 0)
                self.last_failure = data.get("last_failure")
            except (json.JSONDecodeError, ValueError):
                self._reset()
        else:
            self._reset()
    
    def _reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure = None
    
    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "successes": self.successes,
            "last_failure": self.last_failure,
            "updated_at": datetime.now().isoformat(),
        }, indent=2))
    
    def can_execute(self) -> bool:
        """Check if operation can proceed."""
        if self.state == CircuitState.OPEN:
            # Check if cooldown period has passed
            if self.last_failure:
                try:
                    last = datetime.fromisoformat(self.last_failure)
                    elapsed = (datetime.now() - last).total_seconds()
                    if elapsed >= self.config.reset_timeout_seconds:
                        self.state = CircuitState.HALF_OPEN
                        self.successes = 0
                        self._save()
                        return True
                except ValueError:
                    pass
            return False
        return True
    
    def record_success(self) -> None:
        """Record successful operation."""
        self.failures = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.config.half_open_success_threshold:
                self.state = CircuitState.CLOSED
        
        self._save()
    
    def record_failure(self) -> CircuitState:
        """Record failed operation. Returns new state."""
        self.failures += 1
        self.last_failure = datetime.now().isoformat()
        
        if self.state == CircuitState.HALF_OPEN:
            # Immediate open on failure in half-open
            self.state = CircuitState.OPEN
        elif self.failures >= self.config.max_failures:
            self.state = CircuitState.OPEN
        
        self._save()
        return self.state
    
    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._reset()
        self._save()
    
    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "can_execute": self.can_execute(),
        }


if __name__ == "__main__":
    import sys
    
    name = sys.argv[1] if len(sys.argv) > 1 else "default"
    cb = CircuitBreaker(name)
    
    if len(sys.argv) > 2:
        cmd = sys.argv[2]
        if cmd == "success":
            cb.record_success()
            print(f"Recorded success. State: {cb.state.value}")
        elif cmd == "failure":
            new_state = cb.record_failure()
            print(f"Recorded failure. State: {new_state.value}")
        elif cmd == "reset":
            cb.reset()
            print("Circuit reset to CLOSED")
        else:
            print(f"Unknown command: {cmd}")
    else:
        print(json.dumps(cb.get_status(), indent=2))
'''
    _write_file(skill_dir / "circuit_breaker.py", content, force)


def _create_state_manager(skill_dir: Path, force: bool) -> None:
    """Create state manager for loop."""
    content = '''#!/usr/bin/env python3
"""
State Manager for Product Loop

Manages loop state, checkpoints, and progress tracking.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class LoopState:
    """Current state of the product loop."""
    version: str = "1.0"
    iteration: int = 0
    phase: str = "INIT"
    current_task: Optional[str] = None
    tasks_completed: list[str] = field(default_factory=list)
    tasks_remaining: list[str] = field(default_factory=list)
    checkpoints: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=lambda: {
        "total_edits": 0,
        "total_rollbacks": 0,
        "success_rate": 1.0,
    })
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class StateManager:
    """Manages product loop state."""
    
    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()
        self.state_file = self.workspace / ".loop_state.json"
        self.state = self._load()
    
    def _load(self) -> LoopState:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return LoopState(
                    version=data.get("version", "1.0"),
                    iteration=data.get("iteration", 0),
                    phase=data.get("phase", "INIT"),
                    current_task=data.get("current_task"),
                    tasks_completed=data.get("tasks_completed", []),
                    tasks_remaining=data.get("tasks_remaining", []),
                    checkpoints=data.get("checkpoints", []),
                    metrics=data.get("metrics", {}),
                    last_updated=data.get("last_updated", datetime.now().isoformat()),
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return LoopState()
    
    def save(self) -> None:
        self.state.last_updated = datetime.now().isoformat()
        self.state_file.write_text(json.dumps(asdict(self.state), indent=2))
    
    def start_iteration(self) -> None:
        self.state.iteration += 1
        self.state.phase = "OBSERVE"
        self.save()
    
    def set_phase(self, phase: str) -> None:
        self.state.phase = phase
        self.save()
    
    def set_current_task(self, task_id: str) -> None:
        self.state.current_task = task_id
        self.save()
    
    def complete_task(self, task_id: str) -> None:
        if task_id not in self.state.tasks_completed:
            self.state.tasks_completed.append(task_id)
        if task_id in self.state.tasks_remaining:
            self.state.tasks_remaining.remove(task_id)
        if self.state.current_task == task_id:
            self.state.current_task = None
        self.save()
    
    def add_checkpoint(self, description: str, files: list[str]) -> str:
        checkpoint_id = f"cp-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.state.checkpoints.append({
            "id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "files": files,
        })
        # Keep only last 10 checkpoints
        self.state.checkpoints = self.state.checkpoints[-10:]
        self.save()
        return checkpoint_id
    
    def record_edit(self) -> None:
        self.state.metrics["total_edits"] = self.state.metrics.get("total_edits", 0) + 1
        self._update_success_rate()
        self.save()
    
    def record_rollback(self) -> None:
        self.state.metrics["total_rollbacks"] = self.state.metrics.get("total_rollbacks", 0) + 1
        self._update_success_rate()
        self.save()
    
    def _update_success_rate(self) -> None:
        edits = self.state.metrics.get("total_edits", 0)
        rollbacks = self.state.metrics.get("total_rollbacks", 0)
        if edits > 0:
            self.state.metrics["success_rate"] = round((edits - rollbacks) / edits, 2)
    
    def get_summary(self) -> dict:
        return {
            "iteration": self.state.iteration,
            "phase": self.state.phase,
            "current_task": self.state.current_task,
            "completed": len(self.state.tasks_completed),
            "remaining": len(self.state.tasks_remaining),
            "success_rate": self.state.metrics.get("success_rate", 1.0),
            "checkpoints": len(self.state.checkpoints),
        }
    
    def reset(self) -> None:
        self.state = LoopState()
        self.save()


if __name__ == "__main__":
    import sys
    
    manager = StateManager()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "summary":
            print(json.dumps(manager.get_summary(), indent=2))
        elif cmd == "reset":
            manager.reset()
            print("State reset")
        elif cmd == "full":
            print(json.dumps(asdict(manager.state), indent=2))
        else:
            print(f"Unknown command: {cmd}")
    else:
        print(json.dumps(manager.get_summary(), indent=2))
'''
    _write_file(skill_dir / "state_manager.py", content, force)


def _create_loop_state(target_dir: Path, force: bool) -> None:
    """Create initial loop state file."""
    today = date.today().isoformat()
    content = f"""{{
  "version": "1.0",
  "iteration": 0,
  "phase": "INIT",
  "current_task": null,
  "tasks_completed": [],
  "tasks_remaining": [],
  "circuit_breaker": {{
    "test": {{"failures": 0, "state": "CLOSED"}},
    "build": {{"failures": 0, "state": "CLOSED"}},
    "lint": {{"failures": 0, "state": "CLOSED"}}
  }},
  "checkpoints": [],
  "metrics": {{
    "total_edits": 0,
    "total_rollbacks": 0,
    "success_rate": 1.0
  }},
  "created_at": "{today}",
  "last_updated": "{today}"
}}
"""
    _write_file(target_dir / ".loop_state.json", content, force)
