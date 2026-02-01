#!/usr/bin/env python3
"""
Ralph Circuit Breaker

Implements the circuit breaker pattern from Ralph Hybrid Design.
Prevents runaway token consumption by detecting stuck loops.

States:
    CLOSED: Normal operation
    HALF_OPEN: Monitoring after detecting issues
    OPEN: Halted - requires intervention
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    HALF_OPEN = "HALF_OPEN"
    OPEN = "OPEN"


@dataclass
class CircuitBreakerConfig:
    """Configuration thresholds for circuit breaker."""
    no_progress_threshold: int = 3      # Open after N loops with no file changes
    same_error_threshold: int = 5       # Open after N loops with same error
    output_decline_threshold: int = 70  # Open if output declines by >70%
    half_open_after_progress: int = 2   # Return to CLOSED after N progress loops


@dataclass
class IterationMetrics:
    """Metrics from a single iteration."""
    timestamp: str
    files_modified: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    output_length: int = 0
    tasks_completed: list[str] = field(default_factory=list)

    @property
    def has_progress(self) -> bool:
        """Check if this iteration made progress."""
        return len(self.files_modified) > 0 or len(self.tasks_completed) > 0


class CircuitBreaker:
    """
    Circuit breaker for Ralph Hybrid orchestration.

    Tracks iteration metrics and transitions between states
    to prevent runaway loops.
    """

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.state_dir = state_dir or Path.cwd()
        self.config = config or CircuitBreakerConfig()
        self.state_file = self.state_dir / ".circuit_breaker_state"

        # Load or initialize state
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file or initialize."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.state = CircuitState(data.get("state", "CLOSED"))
                self.no_progress_count = data.get("no_progress_count", 0)
                self.same_error_count = data.get("same_error_count", 0)
                self.last_error = data.get("last_error")
                self.last_output_length = data.get("last_output_length", 0)
                self.progress_in_half_open = data.get("progress_in_half_open", 0)
                self.history = data.get("history", [])
            except (json.JSONDecodeError, KeyError):
                self._init_state()
        else:
            self._init_state()

    def _init_state(self) -> None:
        """Initialize fresh state."""
        self.state = CircuitState.CLOSED
        self.no_progress_count = 0
        self.same_error_count = 0
        self.last_error: Optional[str] = None
        self.last_output_length = 0
        self.progress_in_half_open = 0
        self.history: list[dict] = []

    def _save_state(self) -> None:
        """Persist state to file."""
        data = {
            "state": self.state.value,
            "no_progress_count": self.no_progress_count,
            "same_error_count": self.same_error_count,
            "last_error": self.last_error,
            "last_output_length": self.last_output_length,
            "progress_in_half_open": self.progress_in_half_open,
            "history": self.history[-50:],  # Keep last 50
            "updated_at": datetime.now().isoformat(),
        }
        self.state_file.write_text(json.dumps(data, indent=2))

    def record_iteration(self, metrics: IterationMetrics) -> CircuitState:
        """
        Record iteration metrics and update circuit state.

        Returns the new circuit state.
        """
        # Add to history
        self.history.append({
            "timestamp": metrics.timestamp,
            "has_progress": metrics.has_progress,
            "files_modified": len(metrics.files_modified),
            "errors": metrics.errors[:3],  # Keep first 3
            "output_length": metrics.output_length,
        })

        # Check for no progress
        if not metrics.has_progress:
            self.no_progress_count += 1
        else:
            self.no_progress_count = 0

        # Check for same error
        if metrics.errors:
            current_error = metrics.errors[0] if metrics.errors else None
            if current_error == self.last_error:
                self.same_error_count += 1
            else:
                self.same_error_count = 1
                self.last_error = current_error
        else:
            self.same_error_count = 0
            self.last_error = None

        # Check for output decline
        output_declined = False
        if self.last_output_length > 0 and metrics.output_length > 0:
            decline_pct = (
                (self.last_output_length - metrics.output_length)
                / self.last_output_length * 100
            )
            output_declined = decline_pct > self.config.output_decline_threshold

        self.last_output_length = metrics.output_length

        # State transitions
        self._transition(metrics.has_progress, output_declined)

        self._save_state()
        return self.state

    def _transition(self, has_progress: bool, output_declined: bool) -> None:
        """Handle state transitions based on metrics."""
        if self.state == CircuitState.CLOSED:
            # CLOSED -> HALF_OPEN: 2 no-progress iterations
            if self.no_progress_count >= 2:
                self.state = CircuitState.HALF_OPEN
                self.progress_in_half_open = 0
            # CLOSED -> OPEN: thresholds exceeded
            elif self._should_open(output_declined):
                self.state = CircuitState.OPEN

        elif self.state == CircuitState.HALF_OPEN:
            if has_progress:
                self.progress_in_half_open += 1
                # HALF_OPEN -> CLOSED: enough progress
                if self.progress_in_half_open >= self.config.half_open_after_progress:
                    self.state = CircuitState.CLOSED
                    self.no_progress_count = 0
            else:
                # HALF_OPEN -> OPEN: continued no progress
                if self.no_progress_count >= self.config.no_progress_threshold:
                    self.state = CircuitState.OPEN

        # OPEN state requires manual reset

    def _should_open(self, output_declined: bool) -> bool:
        """Check if circuit should open."""
        return (
            self.no_progress_count >= self.config.no_progress_threshold
            or self.same_error_count >= self.config.same_error_threshold
            or output_declined
        )

    def is_open(self) -> bool:
        """Check if circuit is open (halted)."""
        return self.state == CircuitState.OPEN

    def can_proceed(self) -> bool:
        """Check if loop can proceed."""
        return self.state != CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        self._init_state()
        self._save_state()

    def get_status(self) -> dict:
        """Get current status for reporting."""
        return {
            "state": self.state.value,
            "can_proceed": self.can_proceed(),
            "no_progress_count": self.no_progress_count,
            "same_error_count": self.same_error_count,
            "last_error": self.last_error,
            "thresholds": {
                "no_progress": self.config.no_progress_threshold,
                "same_error": self.config.same_error_threshold,
            }
        }


def check_circuit(state_dir: Optional[str] = None) -> dict:
    """Convenience function for shell script integration."""
    cb = CircuitBreaker(Path(state_dir) if state_dir else None)
    return cb.get_status()


def record_iteration(
    files_modified: list[str],
    errors: list[str],
    output_length: int,
    tasks_completed: list[str],
    state_dir: Optional[str] = None
) -> dict:
    """Record iteration and return new state."""
    cb = CircuitBreaker(Path(state_dir) if state_dir else None)
    metrics = IterationMetrics(
        timestamp=datetime.now().isoformat(),
        files_modified=files_modified,
        errors=errors,
        output_length=output_length,
        tasks_completed=tasks_completed,
    )
    new_state = cb.record_iteration(metrics)
    return {
        "state": new_state.value,
        "can_proceed": cb.can_proceed(),
        **cb.get_status()
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        result = check_circuit()
    elif len(sys.argv) > 1 and sys.argv[1] == "reset":
        cb = CircuitBreaker()
        cb.reset()
        result = {"message": "Circuit breaker reset", **cb.get_status()}
    else:
        result = check_circuit()

    print(json.dumps(result, indent=2))
