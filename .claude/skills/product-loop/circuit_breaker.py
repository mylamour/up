#!/usr/bin/env python3
"""
Circuit Breaker for Product Loop

Prevents runaway loops by tracking failures and opening circuit.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class CircuitState(Enum):
    CLOSED = "CLOSED"
    HALF_OPEN = "HALF_OPEN"
    OPEN = "OPEN"


@dataclass
class CircuitConfig:
    max_failures: int = 3
    reset_timeout_seconds: int = 300
    half_open_success_threshold: int = 2


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, name: str, state_dir: Optional[Path] = None, config: Optional[CircuitConfig] = None):
        self.name = name
        self.state_dir = state_dir or Path.cwd()
        self.config = config or CircuitConfig()
        self.state_file = self.state_dir / f".circuit_{name}.json"
        self._load()
    
    def _load(self) -> None:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.state = CircuitState(data.get("state", "CLOSED"))
                self.failures = data.get("failures", 0)
                self.successes = data.get("successes", 0)
                self.last_failure = data.get("last_failure")
            except (json.JSONDecodeError, ValueError):
                self._reset()
        else:
            self._reset()
    
    def _reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure = None
    
    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "successes": self.successes,
            "last_failure": self.last_failure,
            "updated_at": datetime.now().isoformat(),
        }, indent=2))
    
    def can_execute(self) -> bool:
        """Check if operation can proceed."""
        if self.state == CircuitState.OPEN:
            # Check if cooldown period has passed
            if self.last_failure:
                try:
                    last = datetime.fromisoformat(self.last_failure)
                    elapsed = (datetime.now() - last).total_seconds()
                    if elapsed >= self.config.reset_timeout_seconds:
                        self.state = CircuitState.HALF_OPEN
                        self.successes = 0
                        self._save()
                        return True
                except ValueError:
                    pass
            return False
        return True
    
    def record_success(self) -> None:
        """Record successful operation."""
        self.failures = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.config.half_open_success_threshold:
                self.state = CircuitState.CLOSED
        
        self._save()
    
    def record_failure(self) -> CircuitState:
        """Record failed operation. Returns new state."""
        self.failures += 1
        self.last_failure = datetime.now().isoformat()
        
        if self.state == CircuitState.HALF_OPEN:
            # Immediate open on failure in half-open
            self.state = CircuitState.OPEN
        elif self.failures >= self.config.max_failures:
            self.state = CircuitState.OPEN
        
        self._save()
        return self.state
    
    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._reset()
        self._save()
    
    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "can_execute": self.can_execute(),
        }


if __name__ == "__main__":
    import sys
    
    name = sys.argv[1] if len(sys.argv) > 1 else "default"
    cb = CircuitBreaker(name)
    
    if len(sys.argv) > 2:
        cmd = sys.argv[2]
        if cmd == "success":
            cb.record_success()
            print(f"Recorded success. State: {cb.state.value}")
        elif cmd == "failure":
            new_state = cb.record_failure()
            print(f"Recorded failure. State: {new_state.value}")
        elif cmd == "reset":
            cb.reset()
            print("Circuit reset to CLOSED")
        else:
            print(f"Unknown command: {cmd}")
    else:
        print(json.dumps(cb.get_status(), indent=2))
