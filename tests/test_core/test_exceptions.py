"""Tests for the unified exception hierarchy."""

from up.exceptions import (
    UpError,
    GitError,
    GitNotInstalledError,
    GitTimeoutError,
    GitCommandError,
    NotAGitRepoError,
    CheckpointError,
    CheckpointNotFoundError,
    AICliError,
    AICliNotFoundError,
    AICliTimeoutError,
    AICliExecutionError,
    StateError,
    StateCorruptedError,
)


class TestExceptionHierarchy:
    """All exceptions should inherit from UpError."""

    def test_git_errors_are_up_errors(self):
        assert issubclass(GitError, UpError)
        assert issubclass(GitNotInstalledError, GitError)
        assert issubclass(GitTimeoutError, GitError)
        assert issubclass(GitCommandError, GitError)
        assert issubclass(NotAGitRepoError, GitError)

    def test_checkpoint_errors_are_up_errors(self):
        assert issubclass(CheckpointError, UpError)
        assert issubclass(CheckpointNotFoundError, CheckpointError)

    def test_ai_cli_errors_are_up_errors(self):
        assert issubclass(AICliError, UpError)
        assert issubclass(AICliNotFoundError, AICliError)
        assert issubclass(AICliTimeoutError, AICliError)
        assert issubclass(AICliExecutionError, AICliError)

    def test_state_errors_are_up_errors(self):
        assert issubclass(StateError, UpError)
        assert issubclass(StateCorruptedError, StateError)


class TestExceptionAttributes:
    """Custom attributes on exception subclasses."""

    def test_git_timeout_has_timeout(self):
        exc = GitTimeoutError("timed out", timeout=60)
        assert exc.timeout == 60
        assert "timed out" in str(exc)

    def test_git_command_error_has_returncode(self):
        exc = GitCommandError("failed", returncode=128, stderr="fatal: not a repo")
        assert exc.returncode == 128
        assert exc.stderr == "fatal: not a repo"

    def test_ai_cli_timeout_has_timeout(self):
        exc = AICliTimeoutError("AI timed out", timeout=600)
        assert exc.timeout == 600

    def test_ai_cli_execution_error_has_returncode(self):
        exc = AICliExecutionError("AI failed", returncode=1, stderr="error")
        assert exc.returncode == 1
        assert exc.stderr == "error"


class TestBackwardCompatibility:
    """Exceptions re-exported from original modules still work."""

    def test_checkpoint_module_exports(self):
        from up.core.checkpoint import (
            CheckpointError as CpError,
            GitError as CpGitError,
            NotAGitRepoError as CpNotGit,
        )
        assert CpError is CheckpointError
        assert CpGitError is GitError
        assert CpNotGit is NotAGitRepoError

    def test_ai_cli_module_exports(self):
        from up.ai_cli import (
            AICliError as AcError,
            AICliNotFoundError as AcNotFound,
        )
        assert AcError is AICliError
        assert AcNotFound is AICliNotFoundError

    def test_catch_broadly(self):
        try:
            raise GitNotInstalledError("no git")
        except UpError:
            pass  # should be caught

        try:
            raise AICliTimeoutError("timeout", timeout=30)
        except UpError:
            pass  # should be caught
