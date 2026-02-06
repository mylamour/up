# Patterns Extracted

**Generated**: 2026-02-04
**Updated**: 2026-02-06
**Files Analyzed**: 4 (2 original research + 1 hardening research + full code audit)
**Method**: Deep code audit + targeted research

---

## Part A: Git Design Philosophy Patterns

### Core Principles (from Git internals)

| Principle | Description | Application to Vibe Coding |
|-----------|-------------|---------------------------|
| **Content-Addressable** | Store by SHA hash of content | Track vibe state by content hash |
| **Merkle Tree** | Parent hash in child = chain integrity | Chain checkpoints like Git commits |
| **Distributed** | Every clone is complete | Each agent has full context |
| **Atomic Commits** | One logical change per commit | Squash AI mess into clean history |
| **Branch Hierarchy** | Changes flow upward only | experiment -> feature -> develop -> main |

### Scaling Patterns (from Linux kernel workflow)

| Pattern | Description | Team Size |
|---------|-------------|-----------|
| **Integration Branches** | seen -> next -> master -> maint | 10+ devs |
| **Merge Upward Rule** | Fixes go to oldest branch, merge up | All sizes |
| **Worktree Isolation** | Parallel working directories | 4+ devs |
| **Automated Bisect** | Binary search for bug commits | All sizes |
| **Squash Before Merge** | Clean history from AI commits | All sizes |

---

## Part B: Vibe Coding Patterns

| Pattern | Description |
|---------|-------------|
| **Commit-Before-Prompt** | Always commit clean state before AI generation |
| **Hard Reset Recovery** | Reset immediately on bad generation vs "prompting out" |
| **Git Worktrees** | Parallel development with multiple AI agents |
| **Specification-Driven** | Use specs/rules files before code generation |
| **Version Loop** | Checkpoint -> Prompt -> Diff -> Accept/Reset |
| **Shadow Branch** | Experiment on ephemeral branch, squash to feature |

---

## Part C: Hardening Patterns (NEW - 2026-02-06)

### Thread-Safe State Management

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| **File Lock + Atomic Write** | `filelock` + `os.replace()` + fsync | Any shared state file |
| **Read-Modify-Write Lock** | Hold lock for entire read->modify->write cycle | Concurrent state updates |
| **Rolling Backups** | `.bak` copy before overwrite | Critical state files |
| **Same-Dir Temp Files** | `tempfile.mkstemp(dir=parent)` | Atomic rename guarantee |
| **Lock File Separation** | `.lock` suffix separate from data | Prevent lock/data confusion |

### Content-Addressed Storage

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| **Content-Only Hashing** | Hash ONLY content fields, never timestamps/metadata | Deduplication |
| **Deterministic Ordering** | Sort lists before hashing | Reproducible hashes |
| **Parent Chain** | Include parent_id in hash for Merkle integrity | Provenance chains |
| **Existence Check** | Check hash exists before creating | Storage efficiency |
| **Domain Separators** | Include type prefix in hash input | Prevent cross-type collisions |

### CLI Testing

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| **CliRunner + isolated_filesystem** | Full file isolation per test | Every CLI test |
| **pytest-subprocess (fp)** | Mock all subprocess.run calls | Git/AI CLI tests |
| **Test Factory Fixtures** | Reusable setup (git repo, .up/ dir) | Reduce boilerplate |
| **Error Path Testing** | Test missing git, corrupted state, etc. | Robustness |
| **Exit Code + Output Assertions** | Check both code and text | Complete validation |

---

## Part D: Implementation Architecture

### The Vibe Version Loop
```
+-----------------------------------------------------------+
|  CHECKPOINT -> PROMPT -> DIFF -> ACCEPT/RESET -> REPEAT   |
|      |          |        |         |                       |
|  git commit   AI work   Review   git commit                |
|  git tag               mandatory  OR git reset             |
+-----------------------------------------------------------+
```

### Multi-Agent Architecture
```
project/
+-- .git/                    # Shared repository
+-- main/                    # Production (protected)
+-- .worktrees/
    +-- agent-frontend/      # Agent 1
    +-- agent-backend/       # Agent 2
    +-- agent-tests/         # Agent 3
```

### Safe State Architecture (NEW)
```
.up/
+-- state.json               # Main state (locked writes)
+-- state.json.lock          # File lock (filelock library)
+-- state.json.bak           # Rolling backup
+-- checkpoints/             # Checkpoint metadata
+-- provenance/              # Content-addressed entries
    +-- <content-hash>.json  # Deduplicated by content
+-- config.json              # User configuration
```

### Test Architecture (NEW)
```
tests/
+-- conftest.py              # Shared fixtures
+-- test_core/
|   +-- test_state.py        # StateManager tests
|   +-- test_checkpoint.py   # CheckpointManager tests
|   +-- test_provenance.py   # ProvenanceManager tests
+-- test_commands/
|   +-- test_vibe.py         # save/reset/diff tests
|   +-- test_agent.py        # agent commands tests
|   +-- test_start.py        # start loop tests
+-- test_git/
    +-- test_utils.py        # Git utility tests
    +-- test_worktree.py     # Worktree tests
```

---

## Part E: Anti-Patterns Identified (from code audit)

| Anti-Pattern | Where Found | Correct Pattern |
|-------------|-------------|-----------------|
| **setattr() missing arg** | state.py:403 | `setattr(obj, key, value)` |
| **Timestamp in content hash** | provenance.py:72 | Hash only content fields |
| **print() for errors** | events.py:163 | Use `logging` module |
| **Direct file access** | dashboard.py, status.py | Use Manager APIs |
| **Dict manipulation** | start.py:660 | Use StateManager methods |
| **No file locking** | state.py:458-472 | filelock + atomic write |
| **Silent exception swallow** | learn/utils.py:68 | Log before ignoring |
| **Fragile regex parsing** | review.py:108 | Structured output parsing |
| **Dead code** | commands/learn.py (1741 lines) | Delete after verification |
| **Version scatter** | 3 locations disagree | Single source of truth |

---

## Part F: Best Practices Summary

### Safety
1. Never "prompt your way out" - Reset and refine prompt
2. Review every diff - Mandatory before accepting changes
3. Checkpoint before risk - Auto-commit/stash before AI ops
4. Detect doom loops - Warn after 2-3 failed prompts
5. **Lock before write** - File lock on all shared state
6. **Atomic writes** - temp + fsync + replace

### Git
1. Commit atomically - One logical change per commit
2. Squash AI commits - Clean history before merge
3. Use worktrees - Prevent agent collision
4. Bisect for debugging - O(log n) bug finding

### Testing
1. **Test every command** - CliRunner + assertions
2. **Mock external deps** - pytest-subprocess for git/AI
3. **Isolate filesystem** - isolated_filesystem() per test
4. **Test error paths** - Not just happy paths
5. **Coverage gates** - Minimum 60% threshold

### Code Quality
1. **Single version source** - Import from __init__.py everywhere
2. **Manager API only** - Never read state files directly
3. **Proper logging** - logging module, not print()
4. **Type hints** - On all public functions
5. **Delete dead code** - Don't leave deprecated files
