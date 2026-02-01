#!/usr/bin/env python3
"""
Ralph Response Analyzer

Parses Claude output to extract RALPH_STATUS blocks and completion indicators.
Implements dual-condition exit detection from Ralph Hybrid Design.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class RalphStatus:
    """Parsed RALPH_STATUS block."""
    status: str = "UNKNOWN"
    exit_signal: bool = False
    work_type: str = "unknown"
    files_modified: list[str] = field(default_factory=list)
    tasks_completed: list[str] = field(default_factory=list)
    tasks_remaining: int = -1
    errors: list[str] = field(default_factory=list)
    summary: str = ""
    raw_json: dict = field(default_factory=dict)
    parse_error: Optional[str] = None


@dataclass
class CompletionIndicators:
    """Tracks completion indicators for dual-condition exit."""
    explicit_complete: bool = False      # "PRODUCT BUILD COMPLETE" found
    all_tasks_done: bool = False         # tasks_remaining == 0
    exit_signal_true: bool = False       # EXIT_SIGNAL: true
    no_errors: bool = False              # errors array empty
    status_complete: bool = False        # STATUS: "COMPLETE"

    @property
    def count(self) -> int:
        """Count of positive indicators."""
        return sum([
            self.explicit_complete,
            self.all_tasks_done,
            self.exit_signal_true,
            self.no_errors,
            self.status_complete,
        ])

    def should_exit(self) -> bool:
        """
        Dual-condition exit: requires EXIT_SIGNAL AND at least 2 indicators.
        This prevents false positives from phrases like "done with X".
        """
        return self.exit_signal_true and self.count >= 2


class ResponseAnalyzer:
    """Analyzes Claude output for Ralph Hybrid orchestration."""

    # Patterns for RALPH_STATUS block
    STATUS_BLOCK_PATTERN = re.compile(
        r'RALPH_STATUS_BEGIN\s*\n?(.*?)\n?RALPH_STATUS_END',
        re.DOTALL
    )

    # Completion phrase patterns (for indicator detection)
    COMPLETION_PATTERNS = [
        r'PRODUCT BUILD COMPLETE',
        r'all tasks (?:are )?(?:done|complete)',
        r'project (?:is )?complete',
        r'nothing (?:left|remaining) to do',
    ]

    def __init__(self, state_dir: Optional[Path] = None):
        """Initialize analyzer with optional state directory."""
        self.state_dir = state_dir or Path.cwd()
        self.analysis_file = self.state_dir / ".response_analysis"
        self.exit_signals_file = self.state_dir / ".exit_signals"

    def analyze(self, output: str) -> tuple[RalphStatus, CompletionIndicators]:
        """
        Analyze Claude output and return status + completion indicators.

        Returns:
            tuple of (RalphStatus, CompletionIndicators)
        """
        status = self._parse_ralph_status(output)
        indicators = self._detect_completion_indicators(output, status)

        # Persist analysis
        self._save_analysis(status, indicators)

        return status, indicators

    def _parse_ralph_status(self, output: str) -> RalphStatus:
        """Extract and parse RALPH_STATUS block from output."""
        match = self.STATUS_BLOCK_PATTERN.search(output)

        if not match:
            return RalphStatus(parse_error="No RALPH_STATUS block found")

        json_str = match.group(1).strip()

        try:
            data = json.loads(json_str)
            return RalphStatus(
                status=data.get("STATUS", "UNKNOWN"),
                exit_signal=data.get("EXIT_SIGNAL", False),
                work_type=data.get("WORK_TYPE", "unknown"),
                files_modified=data.get("FILES_MODIFIED", []),
                tasks_completed=data.get("TASKS_COMPLETED", []),
                tasks_remaining=data.get("TASKS_REMAINING", -1),
                errors=data.get("ERRORS", []),
                summary=data.get("SUMMARY", ""),
                raw_json=data,
            )
        except json.JSONDecodeError as e:
            return RalphStatus(parse_error=f"JSON parse error: {e}")

    def _detect_completion_indicators(
        self,
        output: str,
        status: RalphStatus
    ) -> CompletionIndicators:
        """Detect completion indicators from output and status."""
        indicators = CompletionIndicators()

        # Check explicit completion phrase
        for pattern in self.COMPLETION_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                indicators.explicit_complete = True
                break

        # Check from parsed status
        if status.parse_error is None:
            indicators.exit_signal_true = status.exit_signal
            indicators.status_complete = status.status == "COMPLETE"
            indicators.all_tasks_done = status.tasks_remaining == 0
            indicators.no_errors = len(status.errors) == 0

        return indicators

    def _save_analysis(
        self,
        status: RalphStatus,
        indicators: CompletionIndicators
    ) -> None:
        """Persist analysis to state files."""
        # Save response analysis
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "status": {
                "status": status.status,
                "exit_signal": status.exit_signal,
                "work_type": status.work_type,
                "files_modified": status.files_modified,
                "tasks_completed": status.tasks_completed,
                "tasks_remaining": status.tasks_remaining,
                "errors": status.errors,
                "summary": status.summary,
                "parse_error": status.parse_error,
            },
            "indicators": {
                "explicit_complete": indicators.explicit_complete,
                "all_tasks_done": indicators.all_tasks_done,
                "exit_signal_true": indicators.exit_signal_true,
                "no_errors": indicators.no_errors,
                "status_complete": indicators.status_complete,
                "count": indicators.count,
                "should_exit": indicators.should_exit(),
            }
        }

        self.analysis_file.write_text(json.dumps(analysis, indent=2))

        # Append to exit signals history
        signal_entry = {
            "timestamp": datetime.now().isoformat(),
            "exit_signal": status.exit_signal,
            "should_exit": indicators.should_exit(),
            "indicator_count": indicators.count,
        }

        history = []
        if self.exit_signals_file.exists():
            try:
                history = json.loads(self.exit_signals_file.read_text())
            except json.JSONDecodeError:
                history = []

        history.append(signal_entry)
        # Keep last 100 entries
        history = history[-100:]
        self.exit_signals_file.write_text(json.dumps(history, indent=2))


def analyze_output(output: str, state_dir: Optional[str] = None) -> dict:
    """
    Convenience function for shell script integration.

    Returns dict with:
        - should_exit: bool
        - exit_signal: bool
        - indicator_count: int
        - status: str
        - summary: str
        - error: str (if any)
    """
    analyzer = ResponseAnalyzer(Path(state_dir) if state_dir else None)
    status, indicators = analyzer.analyze(output)

    return {
        "should_exit": indicators.should_exit(),
        "exit_signal": status.exit_signal,
        "indicator_count": indicators.count,
        "status": status.status,
        "summary": status.summary,
        "files_modified": status.files_modified,
        "tasks_remaining": status.tasks_remaining,
        "error": status.parse_error,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Read from file
        output = Path(sys.argv[1]).read_text()
    else:
        # Read from stdin
        output = sys.stdin.read()

    result = analyze_output(output)
    print(json.dumps(result, indent=2))
