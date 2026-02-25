"""Tests for skill pipeline orchestration (US-007)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from up.learn import learn_cmd


class TestPipelineOrchestration:
    def test_auto_start_flag_exists(self):
        """Verify --auto-start is a valid option."""
        params = {p.name for p in learn_cmd.params}
        assert "auto_start" in params

    @patch("up.learn.learn_plan")
    @patch("up.learn.learn_analyze")
    @patch("up.learn.analyze_project")
    def test_no_auto_start_shows_prompt(
        self, mock_analyze, mock_learn_analyze, mock_plan, tmp_path
    ):
        mock_analyze.return_value = None
        runner = CliRunner()
        result = runner.invoke(learn_cmd, ["-w", str(tmp_path)], input="n\n")
        assert result.exit_code == 0
