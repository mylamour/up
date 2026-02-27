# Concurrency & Thread Safety

**Updated**: 2026-02-27

This guide describes how up-cli keeps shared state and file-backed data safe when multiple agents, threads, or processes run in parallel. Follow these patterns when adding or changing core or plugin code.

---

## Locking Model

### FileLock (cross-process)

All file-based state that can be read or written by more than one process uses [filelock](https://py-filelock.readthedocs.io/) with a lock file next to the data file (e.g. `state.json.lock`). This ensures:

- Only one writer at a time per file
- No TOCTOU: read and write are under the same lock where needed
- Safe behavior when multiple worktrees or CLI invocations touch the same workspace

### Where locks are used

| File / resource | Lock file | Used by |
|-----------------|-----------|--------|
| `.up/state.json` | `.up/state.json.lock` | `StateManager` (load, save, atomic_update) |
| `.up/config.json` | `.up/config.json.lock` | `StateManager` (_load_config, save_config) |
| `prd.json` (any path) | `prd.json.lock` | `get_pending_tasks`, `mark_task_complete_in_prd` |
| `.up/current_session.json` | `.up/current_session.json.lock` | `MemoryManager` (session start/end/update) |

### No double locking

- **ParallelExecutionManager** does not use a separate `threading.Lock`. It relies on `StateManager.atomic_update()` so that all state changes are serialized by the state `FileLock` only. This avoids deadlock (e.g. thread holds state lock then tries to acquire a second lock that another thread holds before releasing state).
- Config uses its own `FileLock` so that code that holds the state lock (e.g. `load()`) can still read config without deadlock.

---

## State mutations

### Prefer atomic_update

For any change to unified state (`.up/state.json`), use:

```python
manager = get_state_manager(workspace)
manager.atomic_update(lambda s: ...)
```

The updater receives the current in-memory state; the manager re-reads from disk inside the lock, runs your updater, then writes once. This avoids lost updates when multiple threads or processes mutate state.

### Batching writes

When you need several state changes in one flow (e.g. in a loop), use `batch_update()` so that only one disk write happens at the end:

```python
with manager.batch_update():
    manager.state.parallel.agents.append(task_id)
    manager.state.loop.iteration += 1
# Single write on exit
```

---

## Subprocess calls

Blocking subprocess calls (git, hooks, pytest, etc.) are run via a shared thread pool so they do not block the main thread:

```python
from up.concurrency import run_subprocess

result = run_subprocess(
    ["git", "status"], cwd=workspace, capture_output=True, text=True, timeout=10
)
```

Use `run_subprocess` in:

- `src/up/parallel/executor.py` (git, verify)
- `src/up/plugins/hooks.py` (hook execution)
- `src/up/memory/_manager.py` (git log / diff for indexing)

Same signature as `subprocess.run`; implementation lives in `src/up/concurrency.py`.

---

## Plugin and extension guidance

1. **Reading/writing shared files**  
   If your plugin or command reads or writes files under `.up/` or other shared paths, consider whether multiple processes could touch the same file. If yes, use a `FileLock` (e.g. `FileLock(str(path) + ".lock", timeout=30)`) around read-modify-write.

2. **Unified state**  
   Use `get_state_manager(workspace)` and either `atomic_update` for single changes or `batch_update()` for multiple changes in one go. Do not hold a custom lock while calling state methods that take the state lock.

3. **Subprocess**  
   Prefer `run_subprocess` from `up.concurrency` for any subprocess that may block (git, tests, external tools) so the main thread stays responsive.

4. **PRD and session files**  
   PRD and memory session file locking are implemented in core. If you add new shared JSON or file state, follow the same pattern: one lock file per data file, hold the lock for the full read-modify-write.

---

## Reference

- State and config locking: `src/up/core/state.py`
- PRD locking: `src/up/parallel/executor.py` (`_prd_lock`, `get_pending_tasks`, `mark_task_complete_in_prd`)
- Session locking: `src/up/memory/_manager.py` (`_session_lock`, `start_session`, `end_session`, `_update_session`)
- Subprocess pool: `src/up/concurrency.py`
- Architecture overview: [SESRC Design](../architecture/SESRC_DESIGN.md#concurrency--thread-safety)
