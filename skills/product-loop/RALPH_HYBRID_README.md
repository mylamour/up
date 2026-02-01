# Ralph Hybrid Implementation

> Production-grade autonomous development loop with safety systems

## Quick Start

```bash
# Start the autonomous loop
./.claude/skills/product-loop/ralph_hybrid.sh start

# Check status
./.claude/skills/product-loop/ralph_hybrid.sh status

# Reset if stuck
./.claude/skills/product-loop/ralph_hybrid.sh reset
```

## Components

| File | Purpose |
|------|---------|
| `ralph_hybrid.sh` | Main orchestrator script |
| `ralph_response_analyzer.py` | Parses RALPH_STATUS blocks |
| `ralph_circuit_breaker.py` | Prevents runaway loops |
| `ralph_rate_limiter.py` | API call management |
| `ralph_state.py` | State file utilities |
| `SKILL.md` | Agent instructions |

## Safety Features

### Circuit Breaker
- **CLOSED**: Normal operation
- **HALF_OPEN**: Monitoring after issues
- **OPEN**: Halted - requires reset

Triggers:
- 3 iterations with no file changes
- 5 iterations with same error
- 70% output decline

### Dual-Condition Exit
Prevents false completion. Requires BOTH:
1. `EXIT_SIGNAL: true` from agent
2. At least 2 completion indicators

### Rate Limiting
- Default: 100 calls/hour
- Auto-waits when limit reached

## State Files

All state stored in `.ralph/` directory:
- `.circuit_breaker_state`
- `.rate_limiter_state`
- `.response_analysis`
- `.exit_signals`
- `ralph_hybrid.log`

## Configuration

Environment variables:
```bash
MAX_ITERATIONS=100
MAX_CALLS_PER_HOUR=100
CLAUDE_TIMEOUT_MINUTES=15
SLEEP_BETWEEN=5
```

Or create `.ralphrc` in workspace root.

## Commands

```bash
ralph_hybrid.sh start         # Start loop
ralph_hybrid.sh status        # Show status
ralph_hybrid.sh reset         # Reset all state
ralph_hybrid.sh reset-circuit # Reset circuit breaker
ralph_hybrid.sh reset-rate    # Reset rate limiter
ralph_hybrid.sh help          # Show help
```
