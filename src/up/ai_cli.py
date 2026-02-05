"""AI CLI utilities - shared functions for Claude and Cursor agent CLIs."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


# =============================================================================
# Exceptions
# =============================================================================

class AICliError(Exception):
    """Base exception for AI CLI operations."""
    pass


class AICliNotFoundError(AICliError):
    """No AI CLI is installed or available."""
    pass


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


# =============================================================================
# CLI Detection
# =============================================================================


def check_ai_cli() -> tuple[str, bool]:
    """Check which AI CLI is available.
    
    Checks for Claude CLI first, then Cursor agent CLI.
    
    Returns:
        (cli_name, available) - e.g., ("claude", True) or ("agent", True)
    """
    # Check for Claude CLI first
    if shutil.which("claude"):
        return "claude", True
    
    # Check for Cursor Agent CLI
    # See: https://cursor.com/docs/cli/overview
    if shutil.which("agent"):
        return "agent", True
    
    return "", False


def run_ai_prompt(
    workspace: Path,
    prompt: str,
    cli_name: str,
    timeout: int = 180,
    silent: bool = False
) -> Optional[str]:
    """Run a prompt through AI CLI and return the response.
    
    Supports both Claude CLI and Cursor agent CLI.
    
    Args:
        workspace: Working directory
        prompt: The prompt to send
        cli_name: "claude" or "agent"
        timeout: Timeout in seconds (default 3 minutes)
        silent: If True, don't print warning messages on failure
    
    Returns:
        Response text or None if failed
    """
    # Verify CLI is available
    if not shutil.which(cli_name):
        if not silent:
            console.print(f"[yellow]AI CLI '{cli_name}' not found, using basic analysis[/]")
        return None
    
    try:
        if cli_name == "claude":
            # Claude CLI: claude -p "prompt"
            cmd = ["claude", "-p", prompt]
        else:
            # Cursor agent CLI: agent -p "prompt" --output-format text
            # See: https://cursor.com/docs/cli/overview
            cmd = ["agent", "-p", prompt, "--output-format", "text"]
        
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
    except FileNotFoundError:
        if not silent:
            console.print(f"[yellow]AI CLI '{cli_name}' not found, using basic analysis[/]")
        return None
    except Exception as e:
        if not silent:
            console.print(f"[yellow]AI error: {e}, using basic analysis[/]")
        return None


def run_ai_task(
    workspace: Path,
    prompt: str,
    cli_name: str,
    timeout: int = 600,
    max_tokens: int = 0,
    raise_on_error: bool = False
) -> tuple[bool, str]:
    """Run an AI task (like implementing code) and return success status.
    
    Args:
        workspace: Working directory
        prompt: The task prompt
        cli_name: "claude" or "agent"
        timeout: Timeout in seconds (default 10 minutes)
        max_tokens: Max output tokens (0 = no limit/use CLI default)
        raise_on_error: If True, raise exceptions instead of returning (False, error)
    
    Returns:
        (success, output) tuple
        
    Raises:
        AICliNotFoundError: If raise_on_error and CLI not found
        AICliTimeoutError: If raise_on_error and command times out
        AICliExecutionError: If raise_on_error and command fails
    """
    # Verify CLI is available
    if not shutil.which(cli_name):
        error_msg = f"AI CLI '{cli_name}' not found in PATH"
        if raise_on_error:
            raise AICliNotFoundError(error_msg)
        return False, error_msg
    
    try:
        if cli_name == "claude":
            # Claude CLI: claude -p "prompt" [--max-tokens N]
            cmd = ["claude", "-p", prompt]
            # Note: Claude CLI doesn't use --max-tokens, it uses model limits
            # The output is effectively unlimited for code tasks
        else:
            # Cursor agent with text output for automation
            cmd = ["agent", "-p", prompt, "--output-format", "text"]
        
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
    except FileNotFoundError:
        # This shouldn't happen since we check with shutil.which, but handle anyway
        error_msg = f"AI CLI '{cli_name}' not found"
        if raise_on_error:
            raise AICliNotFoundError(error_msg)
        return False, error_msg
    except (AICliError,):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        if raise_on_error:
            raise AICliExecutionError(error_msg, returncode=-1, stderr=str(e))
        return False, error_msg


def get_ai_cli_install_instructions() -> str:
    """Get installation instructions for AI CLIs."""
    return """Install one of these AI CLIs:

Claude CLI:
  npm install -g @anthropic-ai/claude-code
  
Cursor Agent CLI:
  curl https://cursor.com/install -fsS | bash
  
See: https://cursor.com/docs/cli/overview
"""
