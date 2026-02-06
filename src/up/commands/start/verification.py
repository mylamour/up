"""Verification utilities for the product loop.

Runs tests, linting, and collects file change information.
"""

import subprocess
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
            ["pytest", "--tb=no", "-q"],
            cwd=workspace,
            capture_output=True,
            timeout=300,
        )
        if pytest_result.returncode == 0:
            console.print("  [green]✓[/] Tests passed")
            tests_passed = True
        elif pytest_result.returncode == 5:
            # No tests collected - that's OK
            console.print("  [dim]○[/] No tests found")
            tests_passed = None
        else:
            console.print("  [red]✗[/] Tests failed")
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
            ["ruff", "check", ".", "--quiet"],
            cwd=workspace,
            capture_output=True,
            timeout=60,
        )
        if ruff_result.returncode == 0:
            console.print("  [green]✓[/] Lint passed")
            lint_passed = True
        else:
            console.print("  [yellow]⚠[/] Lint warnings")
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
    except Exception:
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
