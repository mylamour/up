"""Tests for explore display UI (US-004)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from up.ui.explore_display import (
    ExploreChoice,
    display_comparison,
    _status,
    _get_diff_preview,
    _prompt_selection,
)
from up.parallel.analyze import ExploreComparison, ExploreResultSummary


class TestExploreChoice:
    def test_enum_values(self):
        assert ExploreChoice.STRATEGY_1.value == "1"
        assert ExploreChoice.STRATEGY_2.value == "2"
        assert ExploreChoice.STRATEGY_3.value == "3"
        assert ExploreChoice.COMBINE.value == "combine"
        assert ExploreChoice.NONE.value == "none"


class TestStatusHelper:
    def test_pass(self):
        assert "green" in _status(True)
        assert "pass" in _status(True)

    def test_fail(self):
        assert "red" in _status(False)
        assert "fail" in _status(False)


class TestPromptSelection:
    @patch("up.ui.explore_display.console")
    def test_valid_numeric(self, mock_console):
        mock_console.input.return_value = "1"
        assert _prompt_selection(3) == ExploreChoice.STRATEGY_1

    @patch("up.ui.explore_display.console")
    def test_combine(self, mock_console):
        mock_console.input.return_value = "combine"
        assert _prompt_selection(3) == ExploreChoice.COMBINE

    @patch("up.ui.explore_display.console")
    def test_none(self, mock_console):
        mock_console.input.return_value = "none"
        assert _prompt_selection(2) == ExploreChoice.NONE

    @patch("up.ui.explore_display.console")
    def test_retry_on_invalid(self, mock_console):
        mock_console.input.side_effect = ["bad", "2"]
        assert _prompt_selection(3) == ExploreChoice.STRATEGY_2


class TestDisplayComparison:
    @patch("up.ui.explore_display._prompt_selection", return_value=ExploreChoice.STRATEGY_1)
    @patch("up.ui.explore_display.console")
    def test_returns_choice(self, mock_console, mock_prompt):
        comparison = ExploreComparison(
            strategies=[
                ExploreResultSummary("minimal", 2, 10, 3, True, True),
            ],
            recommendation="minimal",
        )
        choice = display_comparison(comparison)
        assert choice == ExploreChoice.STRATEGY_1

    @patch("up.ui.explore_display._prompt_selection", return_value=ExploreChoice.NONE)
    @patch("up.ui.explore_display.console")
    def test_with_results(self, mock_console, mock_prompt):
        from up.parallel.explore import ExploreResult
        comparison = ExploreComparison(
            strategies=[ExploreResultSummary("clean", 1, 5, 1, True, True)],
        )
        result = ExploreResult(
            strategy_name="clean", branch="b", worktree_path=Path("."),
            success=True, output="ok",
        )
        choice = display_comparison(comparison, results=[result])
        assert choice == ExploreChoice.NONE
