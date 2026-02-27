"""Tests for internal hook runtime and hook script correctness."""

import stat
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from up._hook_runtime import sync_memory, sync_context, main


class TestSyncMemory:
    """Tests for the memory sync invoked by post-commit hook."""

    def test_returns_stats_on_success(self, tmp_path):
        mock_manager = MagicMock()
        mock_manager.sync.return_value = {"commits_indexed": 3, "files_indexed": 5}
        mock_manager._backend = "json"

        with patch("up.memory.MemoryManager", return_value=mock_manager), \
             patch("up.memory._check_chromadb", return_value=False):
            result = sync_memory(tmp_path)

        assert result["commits"] == 3
        assert result["files"] == 5

    def test_returns_error_on_failure(self, tmp_path):
        with patch("up.memory.MemoryManager", side_effect=RuntimeError("broken")):
            result = sync_memory(tmp_path)
        assert "error" in result


class TestSyncContext:
    """Tests for the context refresh invoked by post-checkout hook."""

    def test_updates_context_date(self, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        ctx = docs / "CONTEXT.md"
        ctx.write_text("**Updated**: 2025-01-01\n")

        result = sync_context(tmp_path)
        assert result["updated"] == 1
        assert "2025-01-01" not in ctx.read_text()

    def test_noop_when_no_context_file(self, tmp_path):
        result = sync_context(tmp_path)
        assert result["updated"] == 0


class TestMainEntrypoint:
    """Tests for the __main__ entry point."""

    def test_memory_action(self, tmp_path):
        with patch("up._hook_runtime.sync_memory") as mock:
            with patch("sys.argv", ["_hook_runtime", "memory"]):
                with patch("up._hook_runtime.Path") as mock_path:
                    mock_path.cwd.return_value = tmp_path
                    main()
            mock.assert_called_once()

    def test_context_action(self, tmp_path):
        with patch("up._hook_runtime.sync_context") as mock:
            with patch("sys.argv", ["_hook_runtime", "context"]):
                with patch("up._hook_runtime.Path") as mock_path:
                    mock_path.cwd.return_value = tmp_path
                    main()
            mock.assert_called_once()

    def test_no_args_exits_cleanly(self, tmp_path):
        with patch("sys.argv", ["_hook_runtime"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


class TestHookScriptContent:
    """Ensure generated hook scripts call the internal runtime, not removed commands."""

    def test_post_commit_hook_calls_hook_runtime(self, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)

        from up.commands.init import _install_git_hooks
        _install_git_hooks(tmp_path)

        hook = git_dir / "post-commit"
        assert hook.exists()
        content = hook.read_text()
        assert "up._hook_runtime memory" in content
        assert "up memory sync" not in content
        assert hook.stat().st_mode & stat.S_IEXEC

    def test_post_checkout_hook_calls_hook_runtime(self, tmp_path):
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True)

        from up.commands.init import _install_git_hooks
        _install_git_hooks(tmp_path)

        hook = git_dir / "post-checkout"
        assert hook.exists()
        content = hook.read_text()
        assert "up._hook_runtime context" in content
        assert "up sync" not in content
        assert hook.stat().st_mode & stat.S_IEXEC
