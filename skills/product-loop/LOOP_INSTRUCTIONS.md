# How to Run Infinite Product Loop

The "infinite loop" works by **re-invoking** the skill multiple times, since each AI session has a ~15-20 minute limit.

## Method 1: Manual Re-invocation (Recommended for Cursor)

Since Cursor doesn't have a CLI, manually re-invoke when the session ends:

```
1. Type: /product-loop
2. Wait until it stops (~15-20 min)
3. Check output - if not "PRODUCT BUILD COMPLETE"
4. Type: /product-loop again
5. Repeat until complete
```

**Why this works:** Each invocation reads the current state from:
- TODO.md (sees what's already ✅)
- V1_RELEASE_CHECKLIST.md (sees progress)
- CHANGELOG.md (sees what's done)

So it picks up where it left off automatically.

## Method 2: Claude CLI (If Available)

If you have Claude CLI installed (`claude` command):

```bash
cd /Users/mour/AI/ai-code-auditor
./.claude/skills/product-loop/run-loop.sh
```

This script:
1. Invokes Claude with `/product-loop`
2. Waits for completion or timeout
3. Checks if "PRODUCT BUILD COMPLETE" appeared
4. If not, invokes again
5. Repeats up to MAX_ITERATIONS times

## Method 3: Cursor Keyboard Macro (Advanced)

Set up a keyboard macro to:
1. Type `/product-loop`
2. Press Enter
3. Wait 20 minutes
4. Repeat

Tools like BetterTouchTool (macOS) or AutoHotkey (Windows) can do this.

## State Persistence

The loop maintains state through files, not memory:

| State | Stored In |
|-------|-----------|
| Completed tasks | TODO.md (🔴→🟢) |
| Checklist progress | V1_RELEASE_CHECKLIST.md ([x]) |
| Changes made | CHANGELOG.md |
| Code changes | Git working directory |

Each new invocation reads these files and continues from current state.

## Expected Behavior

```
Invocation 1: Implements 2-3 checklist items, runs tests
Invocation 2: Implements 2-3 more items, fixes test failures
Invocation 3: Adds documentation, runs full verification
...
Invocation N: "🎉 PRODUCT BUILD COMPLETE 🎉"
```

## Tips for Efficiency

1. **Start fresh each day** - Context is cleaner
2. **Commit between sessions** - Save progress
3. **Check TODO.md** - See what was completed
4. **Use focused modes** - `--mode quality` for just testing

## Limitations

| Limitation | Workaround |
|------------|------------|
| 15-20 min per session | Re-invoke manually |
| Context window fills up | New session starts fresh |
| No memory between sessions | State stored in files |
| May repeat some work | Files track what's done |
