"""Tests for ExploreAnalyzer (US-003)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from up.parallel.analyze import (
    ExploreAnalyzer,
    ExploreComparison,
    ExploreResultSummary,
)


@pytest.fixture
def analyzer(tmp_path):
    return ExploreAnalyzer(workspace=tmp_path)


def _make_result(name, success=True, files=None):
    from up.parallel.explore import ExploreResult
    return ExploreResult(
        strategy_name=name,
        branch=f"up/explore-{name}",
        worktree_path=Path("."),
        success=success,
        output="ok",
        files_changed=files or [],
    )


class TestExploreAnalyzer:
    def test_failed_result_gets_zero_summary(self, analyzer):
        results = [_make_result("minimal", success=False)]
        comparison = analyzer.analyze(results)
        assert len(comparison.strategies) == 1
        s = comparison.strategies[0]
        assert s.strategy_name == "minimal"
        assert s.files_changed_count == 0
        assert s.tests_passed is False

    @patch.object(ExploreAnalyzer, "_verify", return_value=(True, True))
    @patch.object(ExploreAnalyzer, "_diff_stats", return_value=(10, 3))
    def test_successful_result_gets_stats(self, mock_diff, mock_verify, analyzer):
        results = [_make_result("clean", files=["a.py", "b.py"])]
        comparison = analyzer.analyze(results)
        s = comparison.strategies[0]
        assert s.files_changed_count == 2
        assert s.lines_added == 10
        assert s.lines_removed == 3
        assert s.tests_passed is True
        assert s.lint_passed is True

    def test_recommend_smallest_passing(self, analyzer):
        summaries = [
            ExploreResultSummary("big", lines_added=100, lines_removed=50, tests_passed=True, lint_passed=True),
            ExploreResultSummary("small", lines_added=5, lines_removed=2, tests_passed=True, lint_passed=True),
        ]
        rec = analyzer._recommend(summaries)
        assert rec == "small"

    def test_recommend_none_when_all_fail(self, analyzer):
        summaries = [
            ExploreResultSummary("a", tests_passed=False, lint_passed=True),
            ExploreResultSummary("b", tests_passed=True, lint_passed=False),
        ]
        rec = analyzer._recommend(summaries)
        assert rec is None

    def test_comparison_dataclass(self):
        c = ExploreComparison()
        assert c.strategies == []
        assert c.recommendation is None
