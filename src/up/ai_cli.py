"""AI CLI utilities - shared functions for Claude and Cursor agent CLIs.

This module wraps the AIEngine abstraction, supporting both:
- CliEngine: subprocess-based (claude -p, agent -p)
- AgentSdkEngine: in-process via claude-agent-sdk (persistent sessions, hooks, compaction)
"""

from pathlib import Path
from typing import Callable, Optional, Tuple

from up.ai.engine import AIEngine, CliEngine
from up.exceptions import (  # noqa: F401
    AICliError,
    AICliNotFoundError,
    AICliTimeoutError,
    AICliExecutionError,
)

# Shared engine instances
_default_engine: Optional[AIEngine] = None
_sdk_engine: Optional[AIEngine] = None


def _get_engine(
    cli_name: Optional[str] = None,
    use_sdk: bool = False,
) -> AIEngine:
    """Get an AI engine instance.

    Args:
        cli_name: "claude" or "agent" for CliEngine. Ignored if use_sdk=True.
        use_sdk: If True, use AgentSdkEngine (in-process, persistent sessions).
    """
    global _default_engine, _sdk_engine

    if use_sdk:
        if _sdk_engine is None:
            from up.ai.sdk_engine import AgentSdkEngine
            _sdk_engine = AgentSdkEngine()
        return _sdk_engine

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
    cli_name: str = "",
    timeout: int = 180,
    silent: bool = False,
    continue_session: bool = False,
    use_sdk: bool = False,
) -> Optional[str]:
    """Run a prompt through AI and return the response.

    Args:
        use_sdk: Use Agent SDK engine (persistent sessions, compaction).
    """
    engine = _get_engine(cli_name, use_sdk=use_sdk)
    return engine.execute_prompt(
        workspace, prompt, timeout=timeout, silent=silent,
        continue_session=continue_session,
    )


def run_ai_task(
    workspace: Path,
    prompt: str,
    cli_name: str = "",
    timeout: int = 600,
    max_tokens: int = 0,
    raise_on_error: bool = False,
    continue_session: bool = False,
    on_output: Optional[Callable[[str], None]] = None,
    use_sdk: bool = False,
) -> Tuple[bool, str]:
    """Run an AI task (like implementing code) and return success status.

    Args:
        use_sdk: Use Agent SDK engine (persistent sessions, compaction).
    """
    engine = _get_engine(cli_name, use_sdk=use_sdk)
    return engine.execute_task(
        workspace, prompt, timeout=timeout, raise_on_error=raise_on_error,
        continue_session=continue_session, on_output=on_output,
    )


def check_sdk_available() -> bool:
    """Check if the Agent SDK engine is available."""
    try:
        from up.ai.sdk_engine import AgentSdkEngine
        return AgentSdkEngine().is_available()
    except ImportError:
        return False


def get_ai_cli_install_instructions() -> str:
    """Get installation instructions for AI engines."""
    return """Install one of these AI engines:

Agent SDK (recommended — persistent sessions, compaction, hooks):
  pip install up-cli[sdk]

Claude CLI (subprocess mode):
  npm install -g @anthropic-ai/claude-code

Cursor Agent CLI (subprocess mode):
  curl https://cursor.com/install -fsS | bash
"""