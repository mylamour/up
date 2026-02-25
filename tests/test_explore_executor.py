"""Tests for ExploreExecutor (US-002)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from up.parallel.explore import (
    ExploreExecutor,
    ExploreResult,
    ExploreStrategy,
    get_default_strategies,
)


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.execute_task.return_value = (True, "Done")
    engine.is_available.return_value = True
    return engine


@pytest.fixture
def sample_strategy():
    return ExploreStrategy(
        name="test-strat",
        description="test",
        prompt_template="Solve: {problem}\n{codebase_context}\n{constraints}",
        constraints=["Be fast"],
    )


class TestExploreExecutorBuildPrompt:
    def test_renders_problem(self, sample_strategy):
        executor = ExploreExecutor(workspace=Path("."))
        prompt = executor._build_prompt(sample_strategy, "fix bug", "some context")
        assert "fix bug" in prompt
        assert "some context" in prompt

    def test_renders_constraints(self, sample_strategy):
        executor = ExploreExecutor(workspace=Path("."))
        prompt = executor._build_prompt(sample_strategy, "x")
        assert "Be fast" in prompt

    def test_no_context_fallback(self, sample_strategy):
        executor = ExploreExecutor(workspace=Path("."))
        prompt = executor._build_prompt(sample_strategy, "x", "")
        assert "(no additional context)" in prompt


class TestExploreExecutorRunAgent:
    @patch("up.git.worktree.create_worktree")
    @patch("up.parallel.explore.subprocess.run")
    def test_run_agent_success(self, mock_subprocess, mock_create_wt, mock_engine, tmp_path):
        mock_create_wt.return_value = (tmp_path, MagicMock())
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="file.py\n")

        strategy = ExploreStrategy(
            name="minimal",
            description="test",
            prompt_template="{problem}\n{codebase_context}\n{constraints}",
        )
        executor = ExploreExecutor(workspace=tmp_path, engine=mock_engine)
        result = executor._run_agent(strategy, "fix it", "")

        assert result.strategy_name == "minimal"
        assert result.success is True
        assert result.output == "Done"

    def test_run_agent_no_engine(self, tmp_path):
        strategy = ExploreStrategy(
            name="x", description="", prompt_template="{problem}\n{codebase_context}\n{constraints}",
        )
        executor = ExploreExecutor(workspace=tmp_path, engine=None)

        with patch("up.git.worktree.create_worktree") as mock_wt:
            mock_wt.return_value = (tmp_path, MagicMock())
            result = executor._run_agent(strategy, "test", "")

        assert result.success is False
        assert "No AI engine" in result.error
