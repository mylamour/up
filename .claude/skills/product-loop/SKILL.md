---
name: product-loop
description: Resilient development with SESRC principles
user-invocable: true
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, TodoWrite
version: "3.0.0"
min-claude-version: "2024.01"
---

# Product Loop — Executable Protocol

You ARE the executor. Do NOT run `up start` or shell out to any CLI.
Use the **LoopOrchestrator** from `up.core.loop` for all state management.
Implement tasks directly using your tools (Read, Edit, Write, Bash, Grep, Glob).

## Step 0: Initialize Orchestrator

```bash
python3 -c "
from up.core.loop import LoopOrchestrator
import json

orch = LoopOrchestrator(Path('.'))

# Check circuit breaker
cb = orch.check_circuit_breaker()
if not cb.can_execute:
    print(f'BLOCKED: {cb.message}')
else:
    # Get next task
    task = orch.get_next_task()
    if task:
        print(json.dumps({'id': task.id, 'title': task.title, 'description': task.description, 'criteria': task.acceptance_criteria}))
    else:
        print('NO_TASKS')
" 2>&1
```

If BLOCKED: tell the user. Run `/product-loop resume` to reset.
If NO_TASKS: all tasks complete, stop.

## Step 1: Begin Task

```bash
python3 -c "
from pathlib import Path
from up.core.loop import LoopOrchestrator, TaskInfo

orch = LoopOrchestrator(Path('.'))
task = TaskInfo(id='TASK_ID', title='TASK_TITLE')
result = orch.begin_task(task)
if result.success:
    print(f'OK checkpoint={result.checkpoint_id}')
else:
    print(f'FAIL: {result.error}')
"
```

Replace TASK_ID and TASK_TITLE with actual values from Step 0.
If FAIL: stop and tell the user.

## Step 2: EXECUTE — Implement the Task

Read the task description and acceptance criteria carefully.
Implement using your tools:
- Read files to understand context
- Edit/Write files to make changes
- Use Grep/Glob to find relevant code

Rules:
- One task at a time
- Small, focused changes
- Don't over-engineer
- Follow existing code patterns
- If stuck after 2 attempts, try a different approach
- If 3 failures, record failure and stop

## Step 3: VERIFY — Run Tests

```bash
python3 -m pytest -x -q --tb=short 2>&1 | tail -20
python3 -m ruff check . 2>&1 | tail -10
python3 -m mypy src/ --ignore-missing-imports --no-error-summary 2>&1 | tail -10
```

**If all pass**: go to Step 4.

**If any fail**: fix the issue and re-verify. After 3 failures, record failure:

```bash
python3 -c "
from pathlib import Path
from up.core.loop import LoopOrchestrator, TaskInfo

orch = LoopOrchestrator(Path('.'))
task = TaskInfo(id='TASK_ID', title='TASK_TITLE')
result = orch.record_failure(task, error='BRIEF_ERROR_DESC')
print(f'rolled_back={result.rolled_back} circuit_open={result.circuit_open}')
"
```

If circuit_open: STOP.

## Step 4: COMMIT — Record Success

```bash
python3 -c "
from pathlib import Path
from up.core.loop import LoopOrchestrator, TaskInfo

orch = LoopOrchestrator(Path('.'))
task = TaskInfo(id='TASK_ID', title='TASK_TITLE')
result = orch.record_success(task)
print(result.commit_message)
"
```

Then commit:
```bash
git add -A && git commit -m "feat(TASK_ID): TASK_TITLE"
```

## Step 5: Next Task or Done

- If more tasks and `--all` mode: go back to Step 0
- If more tasks: ask user if they want to continue
- If no more tasks: print summary and stop

Set idle:
```bash
python3 -c "
from pathlib import Path
from up.core.loop import LoopOrchestrator
orch = LoopOrchestrator(Path('.'))
orch.set_idle()
"
```

---

## Arguments

- `/product-loop` — run next task
- `/product-loop resume` — resume interrupted task (resets circuit breaker)
- `/product-loop status` — show current state only
- `/product-loop all` — run ALL remaining tasks

## Resume

```bash
python3 -c "
from pathlib import Path
from up.core.loop import LoopOrchestrator
orch = LoopOrchestrator(Path('.'))
orch.reset_circuit_breaker()
print('Circuit breaker reset. Ready to retry.')
"
```

## Status

```bash
python3 -c "
from pathlib import Path
from up.core.loop import LoopOrchestrator
import json
orch = LoopOrchestrator(Path('.'))
print(json.dumps(orch.get_status(), indent=2))
"
```
