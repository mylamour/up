"""Tests for AI CLI utilities."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from up.ai_cli import (
    check_ai_cli,
    run_ai_prompt,
    run_ai_task,
    get_ai_cli_install_instructions,
    AICliNotFoundError,
    AICliTimeoutError,
    AICliExecutionError,
)


class TestCheckAiCli:
    """Tests for check_ai_cli detection."""

    def test_finds_claude(self):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda name: "/usr/bin/claude" if name == "claude" else None
            name, available = check_ai_cli()
            assert name == "claude"
            assert available is True

    def test_finds_agent_when_no_claude(self):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda name: "/usr/bin/agent" if name == "agent" else None
            name, available = check_ai_cli()
            assert name == "agent"
            assert available is True

    def test_prefers_claude_over_agent(self):
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/something"
            name, available = check_ai_cli()
            assert name == "claude"
            assert available is True

    def test_returns_empty_when_none_found(self):
        with patch("shutil.which", return_value=None):
            name, available = check_ai_cli()
            assert name == ""
            assert available is False


class TestRunAiPrompt:
    """Tests for run_ai_prompt."""

    def test_returns_none_when_cli_not_found(self, tmp_path):
        with patch("shutil.which", return_value=None):
            result = run_ai_prompt(tmp_path, "test prompt", "claude", silent=True)
            assert result is None

    def test_returns_stdout_on_success(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="AI response text\n",
                stderr=""
            )
            result = run_ai_prompt(tmp_path, "test prompt", "claude")
            assert result == "AI response text"

    def test_returns_none_on_timeout(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 10)):
            result = run_ai_prompt(tmp_path, "test", "claude", timeout=10, silent=True)
            assert result is None

    def test_returns_none_on_error_returncode(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="error"
            )
            result = run_ai_prompt(tmp_path, "test", "claude", silent=True)
            assert result is None

    def test_builds_agent_command_correctly(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/agent"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            run_ai_prompt(tmp_path, "hello", "agent")
            cmd = mock_run.call_args[0][0]
            assert cmd == ["agent", "-p", "hello", "--output-format", "text"]


class TestRunAiTask:
    """Tests for run_ai_task."""

    def test_returns_false_when_cli_not_found(self, tmp_path):
        with patch("shutil.which", return_value=None):
            success, output = run_ai_task(tmp_path, "test", "claude")
            assert success is False
            assert "not found" in output

    def test_raises_when_cli_not_found_and_raise_on_error(self, tmp_path):
        with patch("shutil.which", return_value=None):
            with pytest.raises(AICliNotFoundError):
                run_ai_task(tmp_path, "test", "claude", raise_on_error=True)

    def test_returns_success_on_zero_exit(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="implemented code",
                stderr=""
            )
            success, output = run_ai_task(tmp_path, "implement", "claude")
            assert success is True
            assert output == "implemented code"

    def test_returns_false_on_nonzero_exit(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="task failed"
            )
            success, output = run_ai_task(tmp_path, "implement", "claude")
            assert success is False
            assert "task failed" in output

    def test_raises_execution_error(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fail")
            with pytest.raises(AICliExecutionError) as exc_info:
                run_ai_task(tmp_path, "test", "claude", raise_on_error=True)
            assert exc_info.value.returncode == 1

    def test_raises_timeout_error(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 600)):
            with pytest.raises(AICliTimeoutError) as exc_info:
                run_ai_task(tmp_path, "test", "claude", raise_on_error=True)
            assert exc_info.value.timeout == 600

    def test_timeout_returns_false_without_raise(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 600)):
            success, output = run_ai_task(tmp_path, "test", "claude")
            assert success is False
            assert "timed out" in output


class TestContinueSession:
    """Tests for --continue flag support."""

    def test_claude_continue_adds_flag(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            run_ai_task(tmp_path, "phase 2", "claude", continue_session=True)
            cmd = mock_run.call_args[0][0]
            assert cmd == ["claude", "--continue", "-p", "phase 2"]

    def test_claude_no_continue_by_default(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            run_ai_task(tmp_path, "phase 1", "claude")
            cmd = mock_run.call_args[0][0]
            assert cmd == ["claude", "-p", "phase 1"]

    def test_agent_ignores_continue_flag(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/agent"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            run_ai_task(tmp_path, "phase 2", "agent", continue_session=True)
            cmd = mock_run.call_args[0][0]
            assert "--continue" not in cmd
            assert cmd == ["agent", "-p", "phase 2", "--output-format", "text"]

    def test_prompt_continue_adds_flag(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="response", stderr="")
            run_ai_prompt(tmp_path, "follow up", "claude", continue_session=True)
            cmd = mock_run.call_args[0][0]
            assert cmd == ["claude", "--continue", "-p", "follow up"]


class TestGetInstallInstructions:
    """Tests for install instructions."""

    def test_contains_claude_instructions(self):
        text = get_ai_cli_install_instructions()
        assert "claude" in text.lower()

    def test_contains_cursor_instructions(self):
        text = get_ai_cli_install_instructions()
        assert "cursor" in text.lower()
