#!/usr/bin/env python3
"""
Ralph Rate Limiter

Implements rate limiting from Ralph Hybrid Design.
Manages API call consumption with hourly limits.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class RateLimitConfig:
    """Rate limiter configuration."""
    max_calls_per_hour: int = 100
    cooldown_minutes: int = 5  # Wait time when limit hit


class RateLimiter:
    """
    Rate limiter for Ralph Hybrid orchestration.

    Tracks API calls per hour and enforces limits.
    """

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        config: Optional[RateLimitConfig] = None
    ):
        self.state_dir = state_dir or Path.cwd()
        self.config = config or RateLimitConfig()
        self.state_file = self.state_dir / ".rate_limiter_state"
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file or initialize."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.calls_this_hour = data.get("calls_this_hour", 0)
                self.hour_start = datetime.fromisoformat(
                    data.get("hour_start", datetime.now().isoformat())
                )
                self.total_calls = data.get("total_calls", 0)
                self.history = data.get("history", [])
            except (json.JSONDecodeError, KeyError, ValueError):
                self._init_state()
        else:
            self._init_state()

    def _init_state(self) -> None:
        """Initialize fresh state."""
        self.calls_this_hour = 0
        self.hour_start = datetime.now()
        self.total_calls = 0
        self.history: list[dict] = []

    def _save_state(self) -> None:
        """Persist state to file."""
        data = {
            "calls_this_hour": self.calls_this_hour,
            "hour_start": self.hour_start.isoformat(),
            "total_calls": self.total_calls,
            "history": self.history[-100:],
            "updated_at": datetime.now().isoformat(),
        }
        self.state_file.write_text(json.dumps(data, indent=2))

    def _check_hour_reset(self) -> None:
        """Reset counter if hour has passed."""
        now = datetime.now()
        if now - self.hour_start >= timedelta(hours=1):
            # Log the completed hour
            self.history.append({
                "hour_start": self.hour_start.isoformat(),
                "calls": self.calls_this_hour,
            })
            # Reset for new hour
            self.calls_this_hour = 0
            self.hour_start = now

    def can_proceed(self) -> bool:
        """Check if we can make another call."""
        self._check_hour_reset()
        return self.calls_this_hour < self.config.max_calls_per_hour

    def record_call(self) -> bool:
        """
        Record an API call.

        Returns True if call was allowed, False if rate limited.
        """
        self._check_hour_reset()

        if self.calls_this_hour >= self.config.max_calls_per_hour:
            self._save_state()
            return False

        self.calls_this_hour += 1
        self.total_calls += 1
        self._save_state()
        return True

    def get_wait_time(self) -> int:
        """Get seconds to wait until next call allowed."""
        if self.can_proceed():
            return 0

        # Calculate time until hour resets
        now = datetime.now()
        next_hour = self.hour_start + timedelta(hours=1)
        wait_seconds = (next_hour - now).total_seconds()
        return max(0, int(wait_seconds))

    def get_status(self) -> dict:
        """Get current rate limiter status."""
        self._check_hour_reset()
        return {
            "can_proceed": self.can_proceed(),
            "calls_this_hour": self.calls_this_hour,
            "max_calls_per_hour": self.config.max_calls_per_hour,
            "remaining": self.config.max_calls_per_hour - self.calls_this_hour,
            "total_calls": self.total_calls,
            "hour_start": self.hour_start.isoformat(),
            "wait_seconds": self.get_wait_time(),
        }

    def reset(self) -> None:
        """Reset rate limiter."""
        self._init_state()
        self._save_state()


def check_rate_limit(state_dir: Optional[str] = None) -> dict:
    """Convenience function for shell integration."""
    rl = RateLimiter(Path(state_dir) if state_dir else None)
    return rl.get_status()


def record_call(state_dir: Optional[str] = None) -> dict:
    """Record a call and return status."""
    rl = RateLimiter(Path(state_dir) if state_dir else None)
    allowed = rl.record_call()
    return {"allowed": allowed, **rl.get_status()}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "record":
        result = record_call()
    elif len(sys.argv) > 1 and sys.argv[1] == "reset":
        rl = RateLimiter()
        rl.reset()
        result = {"message": "Rate limiter reset", **rl.get_status()}
    else:
        result = check_rate_limit()

    print(json.dumps(result, indent=2))
