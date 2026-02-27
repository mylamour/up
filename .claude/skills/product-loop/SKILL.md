---
name: product-loop
description: Resilient development with SESRC principles
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, TodoWrite
version: "2.0.0"
min-claude-version: "2024.01"
---

# Product Loop — Executable Protocol

You ARE the executor. Do NOT run `up start` or shell out to any CLI.
Follow this protocol step by step using your tools (Read, Edit, Write, Bash, Grep, Glob).

## Step 0: Load State

```
Read .up/state.json → get loop state, circuit breaker, current task
Read prd.json (or .claude/skills/learning-system/prd.json or TODO.md) → get task list
```

If `.up/state.json` doesn't exist, create it with default state.

Check circuit breaker: if `circuit_breakers.task.state == "OPEN"`, check cooldown.
If still open, STOP and tell the user: "Circuit breaker is OPEN. Run `up start --resume` or wait for cooldown."

## Step 1: OBSERVE — Pick Next Task

From the PRD/TODO, find the highest-priority task that is NOT in `loop.tasks_completed`.
If a specific task was requested, use that one.
If `loop.current_task` is set and not completed, resume it.

Update `.up/state.json`:
- `loop.phase` = "OBSERVE"
- `loop.current_task` = task ID
- `loop.iteration` += 1

Print the task you're working on.

## Step 2: CHECKPOINT — Save Before Changes

Run:
```bash
git stash push -m "up-checkpoint-before-{task_id}" --include-untracked
```

Or if using `up save`:
```bash
up save "before {task_id}"
```

Update `.up/state.json`:
- `loop.phase` = "CHECKPOINT"
- `loop.last_checkpoint` = checkpoint ID

## Step 3: EXECUTE — Implement the Task

Update `.up/state.json`: `loop.phase` = "EXECUTE"

Read the task's description and acceptance criteria carefully.
Implement the task using your tools:
- Read files to understand context
- Edit/Write files to make changes
- Use Grep/Glob to find relevant code

Follow these rules:
- One task at a time
- Small, focused changes
- Don't over-engineer
- Follow existing code patterns

If you get stuck after 2 attempts on the same approach, try a different approach.
If you fail 3 times, record the failure and move on (doom loop prevention).

## Step 4: VERIFY — Run Tests

Update `.up/state.json`: `loop.phase` = "VERIFY"

Run verification in order (stop on first failure):

```bash
# 1. Tests
python3 -m pytest -x -q 2>&1 | tail -20

# 2. Lint (if ruff available)
python3 -m ruff check src/ 2>&1 | tail -10

# 3. Type check (if mypy available)
python3 -m mypy src/ --ignore-missing-imports 2>&1 | tail -10
```

**If verification PASSES**: go to Step 5.

**If verification FAILS**:
1. Record failure in circuit breaker: increment `circuit_breakers.task.failures`
2. If failures >= 3: set circuit breaker to OPEN, STOP
3. Otherwise: rollback checkpoint, go back to Step 3 with the error context
4. Update `loop.consecutive_failures` += 1

## Step 5: COMMIT — Record Success

Update `.up/state.json`:
- `loop.phase` = "COMMIT"
- Add task ID to `loop.tasks_completed`
- `loop.current_task` = null
- `loop.consecutive_failures` = 0
- Reset circuit breaker failures to 0

Commit changes:
```bash
git add -A && git commit -m "feat({task_id}): {task_title}"
```

Record to memory (if available):
```bash
python3 -c "
from up.memory import MemoryManager
m = MemoryManager(use_vectors=False)
m.record_task('{task_id}: {task_title}')
" 2>/dev/null || true
```

## Step 6: Next Task or Done

Check if there are more tasks in the PRD.
- If yes and `--all` mode: go back to Step 1
- If yes: ask user if they want to continue
- If no more tasks: print summary and stop

Update `.up/state.json`: `loop.phase` = "IDLE"

---

## Circuit Breaker Rules

| State | Meaning | Action |
|-------|---------|--------|
| CLOSED | Normal | Execute tasks |
| HALF_OPEN | Testing after cooldown | Allow 1 attempt |
| OPEN | Halted | Stop, tell user |

- 3 consecutive failures → OPEN
- 5 minute cooldown → HALF_OPEN
- 1 success in HALF_OPEN → CLOSED

## State File Format

```json
{
  "version": "2.0",
  "loop": {
    "iteration": 0,
    "phase": "IDLE",
    "current_task": null,
    "tasks_completed": [],
    "tasks_failed": [],
    "last_checkpoint": null,
    "consecutive_failures": 0
  },
  "circuit_breakers": {
    "task": {"failures": 0, "state": "CLOSED"}
  },
  "metrics": {
    "total_tasks": 0,
    "total_rollbacks": 0,
    "success_rate": 1.0
  }
}
```

## Recovery

If interrupted mid-task:
1. Read `.up/state.json` to find `loop.current_task` and `loop.phase`
2. If phase is EXECUTE or VERIFY: rollback to last checkpoint, retry
3. If phase is COMMIT: the task was likely done, verify and commit

## Arguments

- `/product-loop` — run next task
- `/product-loop resume` — resume interrupted task (reset circuit breaker)
- `/product-loop status` — show current state only
- `/product-loop all` — run ALL remaining tasks
