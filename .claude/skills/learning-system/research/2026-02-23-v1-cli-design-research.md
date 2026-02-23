# Research: CLI v1.0 Design Patterns from Successful Tools

**Created**: 2026-02-23
**Status**: Reference
**Sources**: Aider, Claude Code, Git, Docker CLI design analysis

---

## Key Findings

### 1. Successful CLI tools ship with minimal command surfaces

- **Git v1.0**: ~15 porcelain commands (add, commit, push, pull, branch, checkout, merge, log, diff, status, init, clone, fetch, reset, tag)
- **Docker v1.0**: ~12 commands (run, build, pull, push, images, ps, stop, rm, exec, logs, inspect, create)
- **Aider**: Essentially 1 command (`aider`) with flags — no subcommand tree at all
- **Claude Code**: 1 command (`claude`) with slash commands inside the session

**Pattern**: Ship 8-15 commands max. Group by workflow, not by internal architecture.

### 2. AI coding tools prioritize the edit-review-commit loop

- Aider: git-native, every AI change = commit, easy revert
- Claude Code: hooks system for lifecycle control, permissions for safety
- Common pattern: CHECKPOINT → AI WORK → REVIEW → ACCEPT/REJECT

### 3. Safety rails that work

- **Claude Code hooks**: Deterministic guarantees on probabilistic system
- **Aider git integration**: Every change is a commit, trivial to revert
- **Circuit breakers**: Stop after N failures (up-cli already has this)

### 4. What users actually need vs. what developers build

Users want: "make AI coding safe and recoverable"
Developers build: "provenance tracking, event systems, semantic memory, branch hierarchy enforcement"

The gap between these two is where scope creep lives.

## Applicable Patterns

- **One command, one workflow**: Don't expose internal pipeline as separate commands
- **Progressive disclosure**: Basic usage = 3 commands, advanced = flags on those commands
- **Git-native**: Leverage git instead of reinventing (bisect, log, branch rules)
- **Automatic plumbing**: Hooks/sync should be invisible, not manual commands
