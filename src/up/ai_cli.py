"""AI CLI utilities - shared functions for Claude and Cursor agent CLIs."""

import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


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
    timeout: int = 180
) -> str | None:
    """Run a prompt through AI CLI and return the response.
    
    Supports both Claude CLI and Cursor agent CLI.
    
    Args:
        workspace: Working directory
        prompt: The prompt to send
        cli_name: "claude" or "agent"
        timeout: Timeout in seconds (default 3 minutes)
    
    Returns:
        Response text or None if failed
    """
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
        return None
    
    except subprocess.TimeoutExpired:
        console.print(f"[yellow]AI analysis timed out ({timeout}s), using basic analysis[/]")
        return None
    except Exception as e:
        console.print(f"[yellow]AI error: {e}, using basic analysis[/]")
        return None


def run_ai_task(
    workspace: Path,
    prompt: str,
    cli_name: str,
    timeout: int = 300
) -> tuple[bool, str]:
    """Run an AI task (like implementing code) and return success status.
    
    Args:
        workspace: Working directory
        prompt: The task prompt
        cli_name: "claude" or "agent"
        timeout: Timeout in seconds (default 5 minutes)
    
    Returns:
        (success, output) tuple
    """
    try:
        if cli_name == "claude":
            cmd = ["claude", "-p", prompt]
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
            return False, result.stderr or "Unknown error"
    
    except subprocess.TimeoutExpired:
        return False, f"AI task timed out ({timeout}s)"
    except Exception as e:
        return False, str(e)


def get_ai_cli_install_instructions() -> str:
    """Get installation instructions for AI CLIs."""
    return """Install one of these AI CLIs:

Claude CLI:
  npm install -g @anthropic-ai/claude-code
  
Cursor Agent CLI:
  curl https://cursor.com/install -fsS | bash
  
See: https://cursor.com/docs/cli/overview
"""
