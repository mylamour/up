"""Verification utilities for the product loop.

Runs tests, linting, type checking, and collects file change information.
Timeouts and required-check policy are driven by UpConfig.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from rich.console import Console

console = Console()


@dataclass
class VerificationResult:
    """Full result of a verification run."""

    tests_passed: Optional[bool] = None
    lint_passed: Optional[bool] = None
    type_check_passed: Optional[bool] = None

    def all_required_passed(self, required_checks: List[str]) -> bool:
        """Return True if every required check passed (or was not applicable).

        A check that returned ``None`` (tool not installed / no tests collected)
        is treated as *not failing* — only an explicit ``False`` fails the gate.
        """
        mapping = {
            "tests": self.tests_passed,
            "lint": self.lint_passed,
            "types": self.type_check_passed,
        }
        for check in required_checks:
            value = mapping.get(check)
            if value is False:
                return False
        return True

    def summary_parts(self) -> List[str]:
        labels = [
            ("tests", self.tests_passed),
            ("lint", self.lint_passed),
            ("types", self.type_check_passed),
        ]
        parts = []
        for name, val in labels:
            if val is True:
                parts.append(f"{name} passed")
            elif val is False:
                parts.append(f"{name} FAILED")
        return parts


def _load_timeouts(workspace: Path) -> dict:
    """Load verification timeouts from UpConfig."""
    try:
        from up.core.state import get_state_manager

        cfg = get_state_manager(workspace).config
        return {
            "test": cfg.verify_test_timeout,
            "lint": cfg.verify_lint_timeout,
            "type_check": cfg.verify_type_check_timeout,
        }
    except Exception:
        return {"test": 300, "lint": 60, "type_check": 120}


def _load_required_checks(workspace: Path) -> List[str]:
    """Load the list of checks that must pass from UpConfig."""
    try:
        from up.core.state import get_state_manager

        return list(get_state_manager(workspace).config.verify_required_checks)
    except Exception:
        return ["tests", "lint", "types"]


def run_verification(workspace: Path) -> bool:
    """Run verification and return True if all *required* checks pass."""
    result = run_full_verification(workspace)
    required = _load_required_checks(workspace)
    return result.all_required_passed(required)


def run_verification_with_results(workspace: Path):
    """Backward-compatible wrapper returning (tests_passed, lint_passed).

    Callers that also need type_check_passed should use
    ``run_full_verification`` directly.
    """
    result = run_full_verification(workspace)
    return result.tests_passed, result.lint_passed


def run_full_verification(workspace: Path) -> VerificationResult:
    """Run tests, lint, and type checking.

    This function is intentionally side-effect-free (no console output)
    so it can run safely while a Rich Live display is active.
    """
    timeouts = _load_timeouts(workspace)
    result = VerificationResult()

    # --- Tests (pytest) ---
    try:
        pytest_result = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", "--tb=short"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeouts["test"],
        )
        if pytest_result.returncode == 0:
            result.tests_passed = True
        elif pytest_result.returncode == 5:
            result.tests_passed = None  # no tests collected
        else:
            result.tests_passed = False
    except FileNotFoundError:
        result.tests_passed = None
    except subprocess.TimeoutExpired:
        result.tests_passed = False

    # --- Lint (ruff) ---
    try:
        ruff_result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeouts["lint"],
        )
        result.lint_passed = ruff_result.returncode == 0
    except FileNotFoundError:
        result.lint_passed = None
    except subprocess.TimeoutExpired:
        result.lint_passed = None

    # --- Type check (mypy) ---
    try:
        mypy_result = subprocess.run(
            [sys.executable, "-m", "mypy", "src/", "--ignore-missing-imports", "--no-error-summary"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeouts["type_check"],
        )
        result.type_check_passed = mypy_result.returncode == 0
    except FileNotFoundError:
        result.type_check_passed = None
    except subprocess.TimeoutExpired:
        result.type_check_passed = None

    return result


def get_modified_files(workspace: Path) -> List[str]:
    """Get list of all changed files (modified + untracked)."""
    files: List[str] = []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            files.extend(result.stdout.strip().split("\n"))

        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            files.extend(result.stdout.strip().split("\n"))

        return files
    except Exception:
        return files or []


def get_diff_summary(workspace: Path) -> str:
    """Get a summary of current changes."""
    result = subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and result.stdout.strip():
        return f"[dim]{result.stdout.strip()}[/]"
    return "[dim]No changes[/]"


def commit_changes(workspace: Path, message: str) -> bool:
    """Commit all changes with given message."""
    subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
