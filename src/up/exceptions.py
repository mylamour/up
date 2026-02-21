"""Unified exception hierarchy for up-cli.

All custom exceptions derive from UpError so callers can catch broadly
or narrowly as needed.
"""


class UpError(Exception):
    """Base exception for all up-cli operations."""


# ── Git exceptions ──────────────────────────────────────────────────

class GitError(UpError):
    """Git operation failed."""


class GitNotInstalledError(GitError):
    """Git is not installed or not in PATH."""


class GitTimeoutError(GitError):
    """Git command timed out."""

    def __init__(self, message: str, timeout: int):
        super().__init__(message)
        self.timeout = timeout


class GitCommandError(GitError):
    """Git command returned a non-zero exit code."""

    def __init__(self, message: str, returncode: int, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class NotAGitRepoError(GitError):
    """Not in a git repository."""


# ── Checkpoint exceptions ───────────────────────────────────────────

class CheckpointError(UpError):
    """Checkpoint operation failed."""


class CheckpointNotFoundError(CheckpointError):
    """Checkpoint not found."""


# ── AI CLI exceptions ───────────────────────────────────────────────

class AICliError(UpError):
    """Base exception for AI CLI operations."""


class AICliNotFoundError(AICliError):
    """No AI CLI is installed or available."""


class AICliTimeoutError(AICliError):
    """AI CLI command timed out."""

    def __init__(self, message: str, timeout: int):
        super().__init__(message)
        self.timeout = timeout


class AICliExecutionError(AICliError):
    """AI CLI command failed to execute."""

    def __init__(self, message: str, returncode: int, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


# ── State exceptions ────────────────────────────────────────────────

class StateError(UpError):
    """State management error."""


class StateCorruptedError(StateError):
    """State file is corrupted."""
