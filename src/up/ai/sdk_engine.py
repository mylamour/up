"""Agent SDK engine — runs Claude in-process via claude-agent-sdk.

Replaces subprocess `claude -p` with persistent sessions, native hooks,
tool control, and automatic context compaction.
"""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from up.ai.engine import AIEngine

logger = logging.getLogger(__name__)


def _ensure_sdk():
    """Import and return the SDK, raising a clear error if missing."""
    try:
        import claude_agent_sdk
        return claude_agent_sdk
    except ImportError:
        raise ImportError(
            "claude-agent-sdk is required for AgentSdkEngine. "
            "Install with: pip install up-cli[sdk]"
        )


class AgentSdkEngine(AIEngine):
    """AI engine using claude-agent-sdk for in-process agent execution.

    Benefits over CliEngine:
    - Persistent sessions with automatic context compaction
    - Native hooks that map to UP's EventBridge
    - Tool whitelisting per call
    - Session resumption across SESRC loop phases
    """

    def __init__(
        self,
        allowed_tools: list[str] | None = None,
        permission_mode: str = "acceptEdits",
        max_turns: int = 50,
        model: str | None = None,
    ):
        _ensure_sdk()
        self._allowed_tools = allowed_tools or ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]
        self._permission_mode = permission_mode
        self._max_turns = max_turns
        self._model = model  # None = SDK default (claude-opus-4-6)
        self._session_id: str | None = None

    def is_available(self) -> bool:
        try:
            _ensure_sdk()
            return True
        except ImportError:
            return False

    def name(self) -> str:
        return "claude-sdk"

    @property
    def session_id(self) -> str | None:
        """Current session ID for resumption across SESRC phases."""
        return self._session_id

    def reset_session(self) -> None:
        """Clear session — next call starts fresh."""
        self._session_id = None

    def _build_hooks(self) -> dict:
        """Build SDK hooks that bridge to UP's EventBridge.

        Maps Agent SDK hook events to UP EventTypes so plugin hooks
        fire automatically during agent execution.
        """
        hooks = {}

        try:
            from up.events import EventBridge, EventType

            bridge = EventBridge()

            async def on_pre_tool(input_data, tool_use_id, context):
                bridge.emit_simple(
                    EventType.PRE_TOOL_USE,
                    source=self.name(),
                    tool_input=input_data,
                    tool_use_id=tool_use_id,
                )
                return {}

            async def on_post_tool(input_data, tool_use_id, context):
                bridge.emit_simple(
                    EventType.POST_TOOL_USE,
                    source=self.name(),
                    tool_input=input_data,
                    tool_use_id=tool_use_id,
                )
                return {}

            from claude_agent_sdk import HookMatcher

            hooks["PreToolUse"] = [
                HookMatcher(matcher=".*", hooks=[on_pre_tool])
            ]
            hooks["PostToolUse"] = [
                HookMatcher(matcher=".*", hooks=[on_post_tool])
            ]

        except ImportError:
            logger.debug("EventBridge not available, skipping hook integration")

        return hooks

    async def _run_query(
        self,
        workspace: Path,
        prompt: str,
        continue_session: bool = False,
        on_output: Callable[[str], None] | None = None,
    ) -> tuple[str | None, bool]:
        """Core async method that drives the SDK query loop.

        Returns:
            (result_text, success) tuple
        """
        from claude_agent_sdk import ClaudeAgentOptions, query

        options_kwargs: dict = {
            "cwd": str(workspace),
            "allowed_tools": self._allowed_tools,
            "permission_mode": self._permission_mode,
            "max_turns": self._max_turns,
            "hooks": self._build_hooks(),
        }

        if self._model:
            options_kwargs["model"] = self._model

        # Resume existing session if continuing
        if continue_session and self._session_id:
            options_kwargs["resume"] = self._session_id

        result_text = None

        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(**options_kwargs),
        ):
            # Capture session ID for future resumption
            if message.type == "system" and getattr(message, "subtype", None) == "init":
                self._session_id = getattr(message, "session_id", None)
                if on_output:
                    on_output(f"[session:{self._session_id[:8]}] Agent started")

            # Stream assistant text as it arrives
            elif message.type == "assistant":
                text = getattr(message, "text", None) or getattr(message, "content", None)
                if on_output and text and isinstance(text, str):
                    for line in text.splitlines():
                        stripped = line.rstrip()
                        if stripped:
                            on_output(stripped)

            # Stream tool use events
            elif message.type == "tool_use":
                tool_name = getattr(message, "name", "unknown")
                if on_output:
                    on_output(f"[tool] {tool_name}")

            # Stream tool results
            elif message.type == "tool_result":
                content = getattr(message, "content", None)
                if on_output and content and isinstance(content, str):
                    # Truncate long tool output
                    for line in content[:500].splitlines():
                        stripped = line.rstrip()
                        if stripped:
                            on_output(f"  {stripped}")

            # Capture final result
            elif message.type == "result":
                result_text = getattr(message, "result", None)
                if on_output and result_text:
                    on_output("[done] Agent finished")

        return result_text, result_text is not None

    def _run_sync(self, coro):
        """Run an async coroutine synchronously.

        Handles the case where we're already inside an event loop
        (e.g., running inside Claude Code's own agent loop).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in an async context — use a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)

    def execute_prompt(
        self,
        workspace: Path,
        prompt: str,
        timeout: int = 180,
        silent: bool = False,
        continue_session: bool = False,
    ) -> str | None:
        """Execute a prompt via the Agent SDK and return the response."""
        if not self.is_available():
            if not silent:
                from rich.console import Console
                Console().print("[yellow]claude-agent-sdk not installed[/]")
            return None

        try:
            result_text, _ = self._run_sync(
                self._run_query(
                    workspace=workspace,
                    prompt=prompt,
                    continue_session=continue_session,
                )
            )
            return result_text

        except Exception as e:
            if not silent:
                logger.warning("Agent SDK error: %s", e)
            return None

    def execute_task(
        self,
        workspace: Path,
        prompt: str,
        timeout: int = 600,
        raise_on_error: bool = False,
        continue_session: bool = False,
        on_output: Callable[[str], None] | None = None,
    ) -> tuple[bool, str]:
        """Execute an implementation task via the Agent SDK."""
        from up.exceptions import (
            AICliExecutionError,
            AICliNotFoundError,
        )

        if not self.is_available():
            msg = "claude-agent-sdk not installed. Run: pip install up-cli[sdk]"
            if raise_on_error:
                raise AICliNotFoundError(msg)
            return False, msg

        try:
            result_text, success = self._run_sync(
                self._run_query(
                    workspace=workspace,
                    prompt=prompt,
                    continue_session=continue_session,
                    on_output=on_output,
                )
            )

            if success and result_text:
                return True, result_text

            error = result_text or "Agent returned no result"
            if raise_on_error:
                raise AICliExecutionError(error, returncode=1, stderr=error)
            return False, error

        except (AICliNotFoundError, AICliExecutionError):
            raise
        except Exception as e:
            error_msg = f"Agent SDK error: {e}"
            if raise_on_error:
                raise AICliExecutionError(error_msg, returncode=-1, stderr=str(e))
            return False, error_msg
