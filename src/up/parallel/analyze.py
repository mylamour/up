"""ExploreAnalyzer — compare results from multiple exploration agents.

Runs verification in each worktree and produces a structured comparison
with diff stats, test/lint status, and an optional recommendation.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class ExploreResultSummary:
    """Summary metrics for one exploration result."""

    strategy_name: str
    files_changed_count: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    tests_passed: bool = False
    lint_passed: bool = False


@dataclass
class ExploreComparison:
    """Structured comparison of all exploration results."""

    strategies: list[ExploreResultSummary] = field(default_factory=list)
    recommendation: str | None = None


class ExploreAnalyzer:
    """Compares results from multiple exploration agents."""

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def _diff_stats(self, worktree: Path) -> tuple[int, int]:
        """Return (lines_added, lines_removed) for the worktree."""
        try:
            result = subprocess.run(
                ["git", "diff", "--numstat", "HEAD~1"],
                capture_output=True, text=True, cwd=worktree,
            )
            if result.returncode != 0:
                return 0, 0
            added = removed = 0
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        added += int(parts[0])
                        removed += int(parts[1])
                    except ValueError:
                        pass  # binary files show "-"
            return added, removed
        except Exception:
            return 0, 0

    def _run_check(self, cmd: list[str], worktree: Path) -> bool:
        """Run a verification command and return pass/fail."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=worktree, timeout=120,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _verify(self, worktree: Path) -> tuple[bool, bool]:
        """Run tests and lint in a worktree. Returns (tests_passed, lint_passed)."""
        tests = self._run_check(["python3", "-m", "pytest", "--tb=no", "-q"], worktree)
        lint = self._run_check(["python3", "-m", "ruff", "check", "."], worktree)
        return tests, lint

    def analyze(self, results, workspace: Path | None = None) -> ExploreComparison:
        """Compare exploration results and produce a structured comparison.

        Args:
            results: List of ExploreResult from ExploreExecutor.
            workspace: Optional override for workspace path.
        """

        summaries: list[ExploreResultSummary] = []

        for r in results:
            if not r.success:
                summaries.append(ExploreResultSummary(
                    strategy_name=r.strategy_name,
                ))
                continue

            added, removed = self._diff_stats(r.worktree_path)
            tests_ok, lint_ok = self._verify(r.worktree_path)

            summaries.append(ExploreResultSummary(
                strategy_name=r.strategy_name,
                files_changed_count=len(r.files_changed),
                lines_added=added,
                lines_removed=removed,
                tests_passed=tests_ok,
                lint_passed=lint_ok,
            ))

        recommendation = self._recommend(summaries)
        return ExploreComparison(strategies=summaries, recommendation=recommendation)

    def _recommend(self, summaries: list[ExploreResultSummary]) -> str | None:
        """Pick a recommendation based on simple heuristics."""
        passing = [s for s in summaries if s.tests_passed and s.lint_passed]
        if not passing:
            return None

        # Prefer smallest diff among passing strategies
        best = min(passing, key=lambda s: s.lines_added + s.lines_removed)
        return best.strategy_name
