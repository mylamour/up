"""AI CLI utilities - shared functions for Claude and Cursor agent CLIs.

This module now wraps the AIEngine abstraction for backward compatibility.
"""

from pathlib import Path
from typing import Optional, Tuple

from up.ai.engine import CliEngine
from up.exceptions import (  # noqa: F401
    AICliError,
    AICliNotFoundError,
    AICliTimeoutError,
    AICliExecutionError,
)

# Shared instance for backward compatibility
_default_engine: Optional[CliEngine] = None

def _get_engine(cli_name: Optional[str] = None) -> CliEngine:
    global _default_engine
    if cli_name:
        return CliEngine(cli_name=cli_name)
    if _default_engine is None:
        _default_engine = CliEngine()
    return _default_engine


def check_ai_cli() -> tuple[str, bool]:
    """Check which AI CLI is available.
    
    Checks for Claude CLI first, then Cursor agent CLI.
    
    Returns:
        (cli_name, available) - e.g., ("claude", True) or ("agent", True)
    """
    engine = CliEngine()
    return engine.name(), engine.is_available()


def run_ai_prompt(
    workspace: Path,
    prompt: str,
    cli_name: str,
    timeout: int = 180,
    silent: bool = False,
    continue_session: bool = False,
) -> Optional[str]:
    """Run a prompt through AI CLI and return the response."""
    engine = _get_engine(cli_name)
    return engine.execute_prompt(
        workspace, prompt, timeout=timeout, silent=silent,
        continue_session=continue_session,
    )


def run_ai_task(
    workspace: Path,
    prompt: str,
    cli_name: str,
    timeout: int = 600,
    max_tokens: int = 0,
    raise_on_error: bool = False,
    continue_session: bool = False,
) -> Tuple[bool, str]:
    """Run an AI task (like implementing code) and return success status."""
    engine = _get_engine(cli_name)
    return engine.execute_task(
        workspace, prompt, timeout=timeout, raise_on_error=raise_on_error,
        continue_session=continue_session,
    )


def get_ai_cli_install_instructions() -> str:
    """Get installation instructions for AI CLIs."""
    return """Install one of these AI CLIs:

Claude CLI:
  npm install -g @anthropic-ai/claude-code
  
Cursor Agent CLI:
  curl https://cursor.com/install -fsS | bash
  
See: https://cursor.com/docs/cli/overview
"""