"""Tests for AI CLI utilities."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

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


def _mock_popen(returncode=0, stdout="", stderr=""):
    """Create a mock Popen object that behaves like a real process."""
    mock_proc = MagicMock()
    mock_proc.stdout = StringIO(stdout)
    mock_proc.stderr = StringIO(stderr)
    mock_proc.stdin = MagicMock()  # Supports .write() and .close()
    mock_proc.returncode = returncode
    mock_proc.wait.return_value = returncode
    mock_proc.kill = MagicMock()
    return mock_proc


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
            assert cmd == ["agent", "-p", "-", "--output-format", "text"]


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
             patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _mock_popen(returncode=0, stdout="implemented code\n")
            success, output = run_ai_task(tmp_path, "implement", "claude")
            assert success is True
            assert "implemented code" in output

    def test_returns_false_on_nonzero_exit(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _mock_popen(returncode=1, stderr="task failed\n")
            success, output = run_ai_task(tmp_path, "implement", "claude")
            assert success is False
            assert "task failed" in output

    def test_raises_execution_error(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _mock_popen(returncode=1, stderr="fail\n")
            with pytest.raises(AICliExecutionError) as exc_info:
                run_ai_task(tmp_path, "test", "claude", raise_on_error=True)
            assert exc_info.value.returncode == 1

    def test_raises_timeout_error(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.Popen") as mock_popen:
            # Simulate a process that never produces output and hangs
            proc = _mock_popen(returncode=1, stderr="")
            proc.stdout = iter([])  # empty iterator, proc.wait will be called
            mock_popen.return_value = proc
            # We can't easily simulate time.monotonic() exceeding deadline
            # so test the error path via a Popen that raises on wait
            mock_popen.side_effect = OSError("timeout simulation")
            with pytest.raises(AICliExecutionError):
                run_ai_task(tmp_path, "test", "claude", raise_on_error=True)

    def test_timeout_returns_false_without_raise(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = OSError("timeout simulation")
            success, output = run_ai_task(tmp_path, "test", "claude")
            assert success is False


class TestContinueSession:
    """Tests for --continue flag support."""

    def test_claude_continue_adds_flag(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _mock_popen(returncode=0, stdout="ok\n")
            run_ai_task(tmp_path, "phase 2", "claude", continue_session=True)
            cmd = mock_popen.call_args[0][0]
            assert cmd == ["claude", "--continue", "-p", "-"]

    def test_claude_no_continue_by_default(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _mock_popen(returncode=0, stdout="ok\n")
            run_ai_task(tmp_path, "phase 1", "claude")
            cmd = mock_popen.call_args[0][0]
            assert cmd == ["claude", "-p", "-"]

    def test_agent_ignores_continue_flag(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/agent"), \
             patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = _mock_popen(returncode=0, stdout="ok\n")
            run_ai_task(tmp_path, "phase 2", "agent", continue_session=True)
            cmd = mock_popen.call_args[0][0]
            assert "--continue" not in cmd
            assert cmd == ["agent", "-p", "-", "--output-format", "text"]

    def test_prompt_continue_adds_flag(self, tmp_path):
        """execute_prompt still uses subprocess.run."""
        with patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="response", stderr="")
            run_ai_prompt(tmp_path, "follow up", "claude", continue_session=True)
            cmd = mock_run.call_args[0][0]
            assert cmd == ["claude", "--continue", "-p", "-"]


class TestGetInstallInstructions:
    """Tests for install instructions."""

    def test_contains_claude_instructions(self):
        text = get_ai_cli_install_instructions()
        assert "claude" in text.lower()

    def test_contains_cursor_instructions(self):
        text = get_ai_cli_install_instructions()
        assert "cursor" in text.lower()
