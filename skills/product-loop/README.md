# Product Build Loop

> Infinite autonomous product development - design, build, test, document, ship

## Overview

The **Product Build Loop** is a comprehensive skill that runs continuously through all phases of software development:

```
DESIGN → BUILD → TEST → SHIP → ANALYZE → (repeat)
```

Unlike reactive skills that only fix existing issues, this loop is **proactive** - it designs features, implements them, tests them, documents them, and ships them.

---

## 🤖 FULLY AUTONOMOUS MODE (No Human Required)

Run the AI agent in the background - uses your existing `claude` CLI command.
**NO API keys needed!**

```bash
# Start the autonomous agent
cd .claude/skills/product-loop
./start-autonomous.sh start

# Monitor progress
./start-autonomous.sh logs

# Check status
./start-autonomous.sh status

# Stop when needed
./start-autonomous.sh stop
```

**What it does:**
1. Reads TODO.md and V1_RELEASE_CHECKLIST.md
2. Finds the next `[ ]` uncompleted task
3. Calls `claude -p /product-loop` to implement it
4. Waits for completion (~10-15 min per task)
5. Repeats until ALL tasks are `[x]` done
6. Runs 24/7 in background with NO human intervention

**Requirements:**
- Claude CLI (`claude` command) - which you already have!

---

## Quick Start (Interactive Mode)

### In Cursor/Claude IDE

Simply invoke the skill:
```
/product-loop
```

Note: Interactive mode has ~15-20 min session limits. Re-invoke to continue.

### Via Shell Script (if you have Claude CLI)

```bash
cd .claude/skills/product-loop
chmod +x run-loop.sh
./run-loop.sh
```

## Comparison with Other Skills

| Skill | Focus | Proactive? | Continuous? |
|-------|-------|------------|-------------|
| `dev-loop` | Fix tests/types/lint | ❌ No | ✅ Yes |
| `enhancement-loop` | Code improvements | ❌ No | ✅ Yes |
| `master-loop` | Features + QA | ⚠️ Partial | ✅ Yes |
| **`product-loop`** | **Full SDLC** | ✅ Yes | ✅ Yes |

## The Five Phases

### Phase 1: DESIGN
- Analyze requirements from TODO.md
- Create design docs for complex features
- Write Architecture Decision Records (ADRs)
- Break features into implementable tasks

### Phase 2: BUILD
- Implement features from prioritized backlog
- Write tests alongside code
- Follow coding standards strictly
- Update task status as work progresses

### Phase 3: TEST
- Run full test suite (pytest)
- Run type checking (mypy)
- Run linting (ruff)
- Fix any failures before proceeding

### Phase 4: SHIP
- Update documentation
- Update CHANGELOG.md
- Commit changes (when requested)
- Version bump on milestones

### Phase 5: ANALYZE
- Scan codebase for improvement opportunities
- Log findings to ENHANCEMENTS.md
- Add quick wins to TODO.md
- Create issues for complex improvements

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_ITERATIONS` | 100 | Safety limit to prevent infinite loops |
| `SLEEP_BETWEEN` | 3 | Seconds between iterations |

### Example

```bash
# Run up to 200 iterations with 5s between each
MAX_ITERATIONS=200 SLEEP_BETWEEN=5 ./run-loop.sh
```

## Commands

```bash
# Start the loop
./run-loop.sh

# Check current status
./run-loop.sh --status

# Reset and start fresh
./run-loop.sh --reset

# Show help
./run-loop.sh --help
```

## Files Used

### Input Files (Read)
- `TODO.md` - Feature backlog
- `docs/todo/TODO.md` - Detailed tasks
- `docs/todo/DESIGN_IMPROVEMENTS.md` - Architecture improvements
- `ENHANCEMENTS.md` - Code quality improvements
- `CLAUDE.md` - Coding standards

### Output Files (Written)
- `CHANGELOG.md` - Release notes
- `docs/design/*.md` - Design documents
- `docs/adr/*.md` - Architecture Decision Records
- `product-loop.log` - Loop execution log

## Completion Criteria

The loop completes when ALL conditions are met:

- ✅ All TODO items are complete (🟢)
- ✅ All critical improvements are done
- ✅ All tests pass
- ✅ No type errors
- ✅ No linting errors
- ✅ Documentation is current

## Recovery

### Pause and Resume
```bash
# Ctrl+C to pause
# ./run-loop.sh to resume from last iteration
```

### Reset
```bash
./run-loop.sh --reset
```

### View Logs
```bash
cat product-loop.log
```

## Best Practices

1. **Start with a clear TODO.md** - Define what you want built
2. **Keep CLAUDE.md updated** - Coding standards guide the agent
3. **Review periodically** - Check the loop's progress
4. **Commit milestones** - Let the loop commit completed features

## Example Output

```
╔═══════════════════════════════════════════════════════════════╗
║   🎉 PRODUCT BUILD COMPLETE 🎉                                ║
╠═══════════════════════════════════════════════════════════════╣
║   Features Implemented: 12                                    ║
║   Bugs Fixed: 8                                               ║
║   Tests Added: 47                                             ║
║   Documentation Updated: 15 files                             ║
║   Total Iterations: 34                                        ║
╚═══════════════════════════════════════════════════════════════╝
```
