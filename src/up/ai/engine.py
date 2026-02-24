"""AI Engine abstraction layer.

Provides an interface for executing AI prompts and tasks.
Allows decoupling from specific AI CLI implementations.
"""

import abc
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console

from up.exceptions import (
    AICliNotFoundError,
    AICliTimeoutError,
    AICliExecutionError,
)

console = Console()


class AIEngine(abc.ABC):
    """Abstract base class for an AI execution engine."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check if the engine is available for use."""
        pass

    @abc.abstractmethod
    def name(self) -> str:
        """Name of the engine."""
        pass

    @abc.abstractmethod
    def execute_prompt(
        self,
        workspace: Path,
        prompt: str,
        timeout: int = 180,
        silent: bool = False,
        continue_session: bool = False,
    ) -> Optional[str]:
        """Execute a prompt and return the response."""
        pass

    @abc.abstractmethod
    def execute_task(
        self,
        workspace: Path,
        prompt: str,
        timeout: int = 600,
        raise_on_error: bool = False,
        continue_session: bool = False,
    ) -> Tuple[bool, str]:
        """Execute an implementation task and return success status and output."""
        pass


class CliEngine(AIEngine):
    """AI engine that uses local CLI tools (Claude or Cursor Agent)."""

    def __init__(self, cli_name: Optional[str] = None):
        """Initialize CLI engine.
        
        Args:
            cli_name: "claude" or "agent". If None, auto-detects.
        """
        self._cli_name = cli_name
        if not self._cli_name:
            self._cli_name, _ = self._detect_cli()

    def _detect_cli(self) -> Tuple[str, bool]:
        if shutil.which("claude"):
            return "claude", True
        if shutil.which("agent"):
            return "agent", True
        return "", False

    def is_available(self) -> bool:
        if not self._cli_name:
            return False
        return bool(shutil.which(self._cli_name))

    def name(self) -> str:
        return self._cli_name or ""

    def _build_command(self, prompt: str, continue_session: bool = False) -> list:
        """Build the CLI command list.

        Args:
            prompt: The prompt text.
            continue_session: If True and CLI is claude, add --continue flag.
        """
        if self.name() == "claude":
            cmd = ["claude"]
            if continue_session:
                cmd.append("--continue")
            cmd.extend(["-p", prompt])
        else:
            cmd = ["agent", "-p", prompt, "--output-format", "text"]
        return cmd

    def execute_prompt(
        self,
        workspace: Path,
        prompt: str,
        timeout: int = 180,
        silent: bool = False,
        continue_session: bool = False,
    ) -> Optional[str]:
        if not self.is_available():
            if not silent:
                console.print(f"[yellow]AI CLI '{self.name()}' not found, using basic analysis[/]")
            return None

        try:
            cmd = self._build_command(prompt, continue_session=continue_session)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            if not silent and result.stderr:
                console.print(f"[yellow]AI returned error: {result.stderr[:200]}[/]")
            return None

        except subprocess.TimeoutExpired:
            if not silent:
                console.print(f"[yellow]AI analysis timed out ({timeout}s), using basic analysis[/]")
            return None
        except Exception as e:
            if not silent:
                console.print(f"[yellow]AI error: {e}, using basic analysis[/]")
            return None

    def execute_task(
        self,
        workspace: Path,
        prompt: str,
        timeout: int = 600,
        raise_on_error: bool = False,
        continue_session: bool = False,
    ) -> Tuple[bool, str]:
        if not self.is_available():
            error_msg = f"AI CLI '{self.name()}' not found in PATH"
            if raise_on_error:
                raise AICliNotFoundError(error_msg)
            return False, error_msg

        try:
            cmd = self._build_command(prompt, continue_session=continue_session)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                stderr = result.stderr or "Unknown error"
                if raise_on_error:
                    raise AICliExecutionError(
                        f"AI task failed with exit code {result.returncode}",
                        returncode=result.returncode,
                        stderr=stderr
                    )
                return False, stderr

        except subprocess.TimeoutExpired:
            error_msg = f"AI task timed out ({timeout}s)"
            if raise_on_error:
                raise AICliTimeoutError(error_msg, timeout=timeout)
            return False, error_msg
        except (AICliNotFoundError, AICliTimeoutError, AICliExecutionError):
            raise
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            if raise_on_error:
                raise AICliExecutionError(error_msg, returncode=-1, stderr=str(e))
            return False, error_msg
