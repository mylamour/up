"""Post-execute hook: check circuit breaker state.

Reads event data from stdin, checks if the circuit breaker
should trip based on consecutive failures.
Exit 0 = allow, exit 1 = warn, exit 2 = block.
"""
import json
import sys
from pathlib import Path


def main():
    try:
        event_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        event_data = {}

    workspace = Path(event_data.get("workspace", "."))
    success = event_data.get("success", True)
    task_id = event_data.get("task_id", "unknown")

    state_file = workspace / ".up" / "state.json"
    if not state_file.exists():
        print(f"circuit-breaker:{task_id}:no-state")
        sys.exit(0)

    try:
        state = json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError):
        print(f"circuit-breaker:{task_id}:state-error", file=sys.stderr)
        sys.exit(1)

    # Check circuit breaker
    cb = state.get("circuit_breakers", {}).get("task", {})
    cb_state = cb.get("state", "CLOSED")
    failures = cb.get("consecutive_failures", 0)
    threshold = state.get("config", {}).get(
        "circuit_breaker_threshold", 3
    )

    if cb_state == "OPEN":
        print(
            f"Circuit breaker OPEN ({failures} failures). "
            f"Run 'up start --resume' to reset.",
            file=sys.stderr,
        )
        sys.exit(2)  # block

    if not success:
        new_failures = failures + 1
        if new_failures >= threshold:
            print(
                f"Circuit breaker tripping: {new_failures}/{threshold} failures",
                file=sys.stderr,
            )
            sys.exit(2)  # block
        else:
            print(
                f"Failure {new_failures}/{threshold} before circuit breaker trips",
                file=sys.stderr,
            )
            sys.exit(1)  # warn

    print(f"circuit-breaker:{task_id}:ok")
    sys.exit(0)


if __name__ == "__main__":
    main()
