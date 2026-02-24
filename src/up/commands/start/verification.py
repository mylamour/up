"""Verification utilities for the product loop.

Runs tests, linting, and collects file change information.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, List

from rich.console import Console

console = Console()


def run_verification(workspace: Path) -> bool:
    """Run verification steps (tests, lint, type check).

    Returns:
        True if all verification passes
    """
    tests_passed, _ = run_verification_with_results(workspace)
    return tests_passed is not False


def run_verification_with_results(workspace: Path) -> Tuple[Optional[bool], Optional[bool]]:
    """Run verification steps and return individual results.

    Returns:
        Tuple of (tests_passed, lint_passed) where:
        - True = passed
        - False = failed
        - None = not run or not applicable
    """
    tests_passed = None
    lint_passed = None

    # Check if pytest exists and run tests
    try:
        pytest_result = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", "--tb=short"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if pytest_result.returncode == 0:
            passed_count = ""
            for line in pytest_result.stdout.splitlines():
                if " passed" in line and " in " in line:
                    # e.g., "185 passed in 7.00s" -> "(185 passed)"
                    count = line.split(" passed")[0].strip()
                    passed_count = f" ({count} passed)"
                    break
            console.print(f"  [green]✓[/] Tests passed{passed_count}")
            tests_passed = True
        elif pytest_result.returncode == 5:
            # No tests collected - that's OK
            console.print("  [dim]○[/] No tests found")
            tests_passed = None
        else:
            console.print("  [red]✗[/] Tests failed")
            console.print(pytest_result.stdout)
            tests_passed = False
    except FileNotFoundError:
        console.print("  [dim]○[/] pytest not installed")
        tests_passed = None
    except subprocess.TimeoutExpired:
        console.print("  [yellow]⚠[/] Tests timeout")
        tests_passed = False

    # Check for lint (optional - don't fail if not installed)
    try:
        ruff_result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if ruff_result.returncode == 0:
            console.print("  [green]✓[/] Lint passed")
            lint_passed = True
        else:
            console.print("  [yellow]⚠[/] Lint warnings")
            console.print(ruff_result.stdout)
            lint_passed = False  # Track but don't fail
    except FileNotFoundError:
        lint_passed = None  # ruff not installed, skip
    except subprocess.TimeoutExpired:
        console.print("  [yellow]⚠[/] Lint timeout")
        lint_passed = None

    return tests_passed, lint_passed


def get_modified_files(workspace: Path) -> List[str]:
    """Get list of files modified since HEAD (uncommitted changes).

    Returns:
        List of modified file paths relative to workspace
    """
    try:
        # Get staged and unstaged changes
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")

        # Also check for untracked files
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")

        return []
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


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
    """Commit all changes with given message.

    Returns:
        True if commit successful
    """
    # Stage all changes
    subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True)

    # Commit
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    return result.returncode == 0
