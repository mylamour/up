"""Tests for remote plugin install (US-006)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import subprocess

from up.commands.plugin import _clone_plugin


class TestClonePlugin:
    @patch("subprocess.run")
    def test_github_shorthand_expansion(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="fail")
        result = _clone_plugin("github:user/repo")
        call_args = mock_run.call_args[0][0]
        assert "https://github.com/user/repo.git" in call_args

    @patch("subprocess.run")
    def test_clone_failure_returns_none(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="not found")
        result = _clone_plugin("https://example.com/bad.git")
        assert result is None

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=60))
    def test_timeout_returns_none(self, mock_run):
        result = _clone_plugin("https://example.com/slow.git")
        assert result is None
