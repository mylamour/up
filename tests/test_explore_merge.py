"""Tests for merge exploration and cleanup (US-005)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from up.parallel.explore import (
    ExploreResult,
    merge_exploration,
    cleanup_explorations,
)
from up.ui.explore_display import ExploreChoice


def _make_result(name, success=True):
    return ExploreResult(
        strategy_name=name,
        branch=f"up/explore-{name}",
        worktree_path=Path(f"/tmp/wt-{name}"),
        success=success,
        output="ok" if success else "",
        files_changed=["a.py"] if success else [],
    )


class TestMergeExploration:
    @patch("up.parallel.explore.cleanup_explorations")
    def test_none_choice_cleans_up(self, mock_cleanup):
        results = [_make_result("minimal")]
        ok = merge_exploration(ExploreChoice.NONE, results, Path("."))
        assert ok is False
        mock_cleanup.assert_called_once_with(results)

    @patch("up.git.worktree.remove_worktree")
    @patch("up.git.worktree.merge_worktree", return_value=True)
    def test_single_strategy_merges(self, mock_merge, mock_remove):
        results = [_make_result("minimal"), _make_result("clean")]
        ok = merge_exploration(ExploreChoice.STRATEGY_1, results, Path("."))
        assert ok is True
        mock_merge.assert_called_once()

    @patch("up.git.worktree.remove_worktree")
    def test_invalid_index_returns_false(self, mock_remove):
        results = [_make_result("minimal")]
        # STRATEGY_3 index=2 but only 1 result
        ok = merge_exploration(ExploreChoice.STRATEGY_3, results, Path("."))
        assert ok is False

    @patch("up.git.worktree.remove_worktree")
    @patch("up.git.worktree.merge_worktree", return_value=True)
    def test_combine_merges_successful(self, mock_merge, mock_remove):
        results = [_make_result("a"), _make_result("b", success=False)]
        ok = merge_exploration(ExploreChoice.COMBINE, results, Path("."))
        assert ok is True
        assert mock_merge.call_count == 1


class TestCleanupExplorations:
    @patch("up.git.worktree.remove_worktree")
    def test_removes_all_worktrees(self, mock_remove):
        results = [_make_result("a"), _make_result("b")]
        cleanup_explorations(results)
        assert mock_remove.call_count == 2

    @patch("up.git.worktree.remove_worktree", side_effect=Exception("gone"))
    def test_ignores_removal_errors(self, mock_remove):
        results = [_make_result("x")]
        cleanup_explorations(results)  # Should not raise
