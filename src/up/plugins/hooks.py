"""Hook pipeline runner with JSON I/O.

Executes hook scripts (any language) via subprocess with JSON stdin
and exit code semantics. This is the polyglot execution layer.

Exit code semantics:
  0 = allow (hook passed)
  1 = warn  (log stderr, continue)
  2 = block (log stderr, halt operation)
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HookSpec:
    """Specification for a hook to execute."""
    type: str  # "command" or "prompt"
    command: str
    timeout: int = 10
    matcher: str | None = None  # UP event matcher regex
    tool_matcher: str | None = None  # Claude Code tool name matcher (e.g. "Write|Edit")

    def matches(self, event_data: dict) -> bool:
        """Check if this hook matches the given event data."""
        if not self.matcher:
            return True
        try:
            pattern = re.compile(self.matcher)
            # Match against common event fields
            for key in ("tool_name", "event_type", "phase", "task_id"):
                value = event_data.get(key, "")
                if isinstance(value, str) and pattern.search(value):
                    return True
            return False
        except re.error:
            logger.warning("Invalid matcher regex: %s", self.matcher)
            return False


@dataclass
class HookResult:
    """Result from executing a hook."""
    allowed: bool
    message: str
    exit_code: int
    hook_name: str = ""
    output: str = ""


class HookRunner:
    """Executes hook scripts via subprocess with JSON I/O.

    Hooks receive event data as JSON on stdin and communicate
    results via exit codes and stderr messages.
    """

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()

    def run_hook(self, spec: HookSpec, event_data: dict) -> HookResult:
        """Execute a single hook and return the result.

        Args:
            spec: Hook specification (command, timeout, matcher).
            event_data: Event context passed as JSON via stdin.

        Returns:
            HookResult with allowed/message/exit_code.
        """
        # Check matcher first
        if not spec.matches(event_data):
            return HookResult(
                allowed=True,
                message="skipped (no match)",
                exit_code=0,
                hook_name=spec.command,
            )

        input_json = json.dumps(event_data)

        try:
            # Use sh -c to support shell features (redirections, chaining)
            # while keeping shell=False. Command strings come from trusted
            # config (hooks.json); untrusted event data flows via stdin only.
            result = subprocess.run(
                ["sh", "-c", spec.command],
                shell=False,
                input=input_json,
                capture_output=True,
                text=True,
                timeout=spec.timeout,
                cwd=str(self.workspace),
            )

            exit_code = result.returncode
            stderr = result.stderr.strip()
            stdout = result.stdout.strip()

            # Shell error codes (126=permission denied, 127=not found)
            # are infrastructure failures, not intentional blocks
            if exit_code in (126, 127):
                logger.error("Hook infrastructure error [%s]: %s", spec.command, stderr)
                return HookResult(
                    allowed=True,
                    message=stderr or f"shell error (exit {exit_code})",
                    exit_code=-1,
                    hook_name=spec.command,
                )

            if exit_code == 0:
                return HookResult(
                    allowed=True,
                    message=stderr or "ok",
                    exit_code=0,
                    hook_name=spec.command,
                    output=stdout,
                )
            elif exit_code == 1:
                logger.warning("Hook warning [%s]: %s", spec.command, stderr)
                return HookResult(
                    allowed=True,
                    message=stderr or "warning",
                    exit_code=1,
                    hook_name=spec.command,
                    output=stdout,
                )
            else:
                # exit_code >= 2 means block
                logger.error("Hook blocked [%s]: %s", spec.command, stderr)
                return HookResult(
                    allowed=False,
                    message=stderr or "blocked by hook",
                    exit_code=exit_code,
                    hook_name=spec.command,
                    output=stdout,
                )

        except subprocess.TimeoutExpired:
            logger.error("Hook timed out [%s] after %ds", spec.command, spec.timeout)
            return HookResult(
                allowed=True,
                message=f"timeout after {spec.timeout}s",
                exit_code=-1,
                hook_name=spec.command,
            )
        except FileNotFoundError:
            logger.error("Hook command not found: %s", spec.command)
            return HookResult(
                allowed=True,
                message=f"command not found: {spec.command}",
                exit_code=-1,
                hook_name=spec.command,
            )
        except PermissionError:
            logger.error("Hook permission denied: %s", spec.command)
            return HookResult(
                allowed=True,
                message=f"permission denied: {spec.command}",
                exit_code=-1,
                hook_name=spec.command,
            )
        except Exception as e:
            logger.error("Hook crashed [%s]: %s", spec.command, e)
            return HookResult(
                allowed=True,
                message=f"hook error: {e}",
                exit_code=-1,
                hook_name=spec.command,
            )

    def run_hooks(
        self, specs: list[HookSpec], event_data: dict
    ) -> list[HookResult]:
        """Execute multiple hooks in order.

        Returns all results. If any hook blocks (exit_code >= 2),
        subsequent hooks still run but the aggregate is "blocked".
        """
        results = []
        for spec in specs:
            result = self.run_hook(spec, event_data)
            results.append(result)
        return results

    def is_blocked(self, results: list[HookResult]) -> bool:
        """Check if any hook result is a block."""
        return any(not r.allowed for r in results)

    def get_block_messages(self, results: list[HookResult]) -> list[str]:
        """Get messages from blocking hooks."""
        return [r.message for r in results if not r.allowed]


def load_hooks_from_json(hooks_json_path: Path) -> list[HookSpec]:
    """Load hook specs from a plugin's hooks/hooks.json file.

    Expected format:
    {
      "hooks": [
        {"type": "command", "command": "python hooks/check.py", "matcher": ".*", "timeout": 10},
        ...
      ]
    }
    """
    if not hooks_json_path.exists():
        return []
    try:
        data = json.loads(hooks_json_path.read_text())
        specs = []
        for raw in data.get("hooks", []):
            specs.append(HookSpec(
                type=raw.get("type", "command"),
                command=raw.get("command", ""),
                timeout=raw.get("timeout", 10),
                matcher=raw.get("matcher"),
                tool_matcher=raw.get("tool_matcher"),
            ))
        return specs
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Could not load hooks from %s: %s", hooks_json_path, e)
        return []
