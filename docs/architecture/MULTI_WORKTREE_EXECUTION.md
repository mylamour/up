# Multi-Worktree Automatic Execution

**Status**: Design Document
**Created**: 2026-02-04

---

## Overview

This document describes how `up start --parallel` automatically runs multiple tasks in separate Git worktrees, verifies each, and merges successful ones into main.

## The Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     up start --parallel                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: DISPATCH                                              │
│  ─────────────────                                              │
│  1. Read prd.json for pending tasks                             │
│  2. Select N tasks (--jobs flag, default: 3)                    │
│  3. For each task:                                              │
│     - Create branch: worktree/US-XXX                            │
│     - Create worktree: .worktrees/US-XXX/                       │
│     - Copy .env, config files                                   │
│     - Initialize .agent_state.json                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: EXECUTE (Parallel)                                    │
│  ──────────────────────────                                     │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Worktree A  │  │ Worktree B  │  │ Worktree C  │             │
│  │ US-004      │  │ US-005      │  │ US-006      │             │
│  │             │  │             │  │             │             │
│  │ 1. Checkpoint│  │ 1. Checkpoint│  │ 1. Checkpoint│           │
│  │ 2. AI impl  │  │ 2. AI impl  │  │ 2. AI impl  │             │
│  │ 3. Commit   │  │ 3. Commit   │  │ 3. Commit   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┴────────────────┘                     │
│                          │                                      │
└──────────────────────────┴──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: VERIFY (Parallel)                                     │
│  ──────────────────────────                                     │
│                                                                 │
│  For each worktree:                                             │
│    1. cd .worktrees/US-XXX/                                     │
│    2. Run: pytest                                               │
│    3. Run: mypy src/ (if Python)                                │
│    4. Run: ruff check src/                                      │
│    5. Mark: PASS or FAIL                                        │
│                                                                 │
│  Results:                                                       │
│    US-004: ✅ PASS (tests: 42/42, lint: clean)                  │
│    US-005: ❌ FAIL (tests: 38/42, 4 errors)                     │
│    US-006: ✅ PASS (tests: 15/15, lint: clean)                  │
│                                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: MERGE (Sequential)                                    │
│  ──────────────────────────                                     │
│                                                                 │
│  For each PASSED worktree:                                      │
│    1. Checkout main                                             │
│    2. Squash merge: git merge --squash worktree/US-XXX          │
│    3. Commit: "feat(US-XXX): <task title>"                      │
│    4. Update prd.json: passes = true                            │
│    5. Cleanup worktree                                          │
│                                                                 │
│  For each FAILED worktree:                                      │
│    1. Keep worktree for debugging                               │
│    2. Log failure reason                                        │
│    3. Option: --retry to re-run failed                          │
│                                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: CONTINUE                                              │
│  ────────────────                                               │
│                                                                 │
│  If more pending tasks:                                         │
│    → Go back to PHASE 1 (next batch)                            │
│                                                                 │
│  If all tasks done:                                             │
│    → Report summary                                             │
│    → Exit                                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Command Interface

```bash
# Run 3 tasks in parallel (default)
up start --parallel

# Run 5 tasks in parallel
up start --parallel --jobs 5

# Run all tasks, 3 at a time
up start --parallel --all

# Dry run to see what would happen
up start --parallel --dry-run

# Retry failed tasks from previous run
up start --parallel --retry
```

## Directory Structure During Execution

```
project/
├── .git/                           # Shared Git database
├── .worktrees/
│   ├── US-004/                     # Task 1 worktree
│   │   ├── src/
│   │   ├── tests/
│   │   ├── .agent_state.json       # Agent status
│   │   └── .vibe_log               # AI interaction log
│   ├── US-005/                     # Task 2 worktree
│   │   └── ...
│   └── US-006/                     # Task 3 worktree
│       └── ...
├── src/                            # Main working directory
├── tests/
├── prd.json
└── .loop_state.json                # Orchestrator state
```

## State Tracking

### .loop_state.json (Orchestrator)

```json
{
  "version": "2.0",
  "mode": "parallel",
  "iteration": 3,
  "parallel_limit": 3,
  "active_worktrees": [
    {
      "task_id": "US-004",
      "branch": "worktree/US-004",
      "path": ".worktrees/US-004",
      "status": "executing",
      "started": "2026-02-04T10:00:00"
    },
    {
      "task_id": "US-005",
      "branch": "worktree/US-005", 
      "path": ".worktrees/US-005",
      "status": "verifying",
      "started": "2026-02-04T10:00:00"
    }
  ],
  "completed_this_run": ["US-001", "US-002", "US-003"],
  "failed_this_run": [],
  "metrics": {
    "total_tasks": 17,
    "completed": 6,
    "in_progress": 2,
    "failed": 0
  }
}
```

### .agent_state.json (Per Worktree)

```json
{
  "task_id": "US-004",
  "task_title": "up vibe save - Quick checkpoint command",
  "branch": "worktree/US-004",
  "status": "executing",
  "phase": "AI_IMPL",
  "started": "2026-02-04T10:00:00",
  "checkpoints": [
    {"name": "cp-1", "time": "2026-02-04T10:00:05"}
  ],
  "ai_invocations": [
    {
      "prompt_hash": "sha256:abc123",
      "model": "claude-3.5-sonnet",
      "success": true,
      "duration_seconds": 45
    }
  ],
  "verification": {
    "tests_passed": null,
    "lint_passed": null,
    "type_check_passed": null
  }
}
```

## Conflict Resolution

When merging, conflicts may occur if two tasks touch the same file.

### Strategy 1: Sequential Merge (Default)

Merge one at a time. If conflict:
1. Stop merging
2. Notify user
3. User resolves manually
4. Continue with `up start --parallel --continue`

### Strategy 2: Dependency Ordering

Define task dependencies in prd.json:
```json
{
  "id": "US-005",
  "depends_on": ["US-004"]
}
```
Dispatcher respects dependencies - US-005 waits for US-004 to merge first.

### Strategy 3: File Locking (Future)

Track which files each task will likely touch:
```json
{
  "id": "US-004",
  "likely_files": ["src/up/commands/vibe.py"]
}
```
Dispatcher avoids parallel execution of tasks touching same files.

## Implementation Plan

### Step 1: Git Worktree Utilities

```python
# src/up/git/worktree.py

def create_worktree(task_id: str, base_branch: str = "main") -> Path:
    """Create isolated worktree for a task."""
    branch = f"worktree/{task_id}"
    path = Path(f".worktrees/{task_id}")
    
    # Create branch and worktree
    subprocess.run(["git", "worktree", "add", "-b", branch, str(path), base_branch])
    
    # Copy environment files
    for env_file in [".env", ".env.local"]:
        if Path(env_file).exists():
            shutil.copy(env_file, path / env_file)
    
    return path

def remove_worktree(task_id: str):
    """Remove worktree after merge or failure."""
    path = Path(f".worktrees/{task_id}")
    branch = f"worktree/{task_id}"
    
    subprocess.run(["git", "worktree", "remove", str(path)])
    subprocess.run(["git", "branch", "-D", branch])

def list_worktrees() -> list[dict]:
    """List all active worktrees."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True, text=True
    )
    # Parse output...
    return worktrees
```

### Step 2: Parallel Executor

```python
# src/up/parallel.py

import asyncio
from concurrent.futures import ProcessPoolExecutor

async def run_parallel_tasks(tasks: list[dict], max_workers: int = 3):
    """Execute multiple tasks in parallel worktrees."""
    
    # Phase 1: Create worktrees
    worktrees = []
    for task in tasks[:max_workers]:
        wt = create_worktree(task["id"])
        worktrees.append({"task": task, "path": wt})
    
    # Phase 2: Execute in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(execute_in_worktree, wt["path"], wt["task"])
            for wt in worktrees
        ]
        results = [f.result() for f in futures]
    
    # Phase 3: Verify each
    verified = []
    for wt, result in zip(worktrees, results):
        if result["success"]:
            verify_result = verify_worktree(wt["path"])
            wt["verified"] = verify_result["passed"]
            verified.append(wt)
    
    # Phase 4: Merge passed
    for wt in verified:
        if wt["verified"]:
            merge_worktree(wt["task"]["id"])
    
    return results
```

### Step 3: CLI Integration

```python
# Add to src/up/commands/start.py

@click.option("--parallel", is_flag=True, help="Run tasks in parallel worktrees")
@click.option("--jobs", "-j", default=3, help="Number of parallel tasks (default: 3)")

def start_cmd(..., parallel: bool, jobs: int):
    if parallel:
        _run_parallel_loop(workspace, state, task_source, jobs, run_all, timeout)
    else:
        # Existing sequential logic
        ...
```

## Safety Mechanisms

1. **Checkpoint before AI**: Each worktree creates checkpoint before AI runs
2. **Isolated branches**: Each task on separate branch, main is protected
3. **Verification gate**: Must pass tests/lint before merge allowed
4. **Squash merge**: Clean history regardless of AI commit mess
5. **Rollback ready**: Can `git reset --hard` any worktree independently

## Limitations

1. **AI CLI limitation**: Most AI CLIs (claude, cursor) run one at a time
   - Workaround: Use subprocess with separate processes
   - Or: Stagger execution (start next when current reaches AI phase)

2. **Resource usage**: Multiple worktrees = more disk space
   - Mitigation: Cleanup completed worktrees immediately

3. **Merge conflicts**: Parallel tasks may conflict
   - Mitigation: Dependency ordering, file locking (future)

## Usage Example

```bash
# Start parallel execution
$ up start --parallel --all --jobs 3

═══════════════════════════════════════════════════════
 PARALLEL PRODUCT LOOP - 3 workers
═══════════════════════════════════════════════════════

[Dispatch] Creating worktrees...
  ✓ .worktrees/US-004 (branch: worktree/US-004)
  ✓ .worktrees/US-005 (branch: worktree/US-005)
  ✓ .worktrees/US-006 (branch: worktree/US-006)

[Execute] Running AI implementations...
  US-004: ████████████████████ 100% (45s)
  US-005: ██████████████░░░░░░  70% (running)
  US-006: ████████████████████ 100% (38s)

[Verify] Running tests...
  US-004: ✅ tests: 42/42, lint: clean
  US-005: ❌ tests: 38/42 (4 failures)
  US-006: ✅ tests: 15/15, lint: clean

[Merge] Merging to main...
  ✓ US-004 merged (squashed 12 commits → 1)
  ✓ US-006 merged (squashed 8 commits → 1)
  ✗ US-005 kept for debugging

[Continue] Next batch...
  → Dispatching US-007, US-008, US-009

───────────────────────────────────────────────────────
Summary: 2 merged, 1 failed, 14 remaining
───────────────────────────────────────────────────────
```
