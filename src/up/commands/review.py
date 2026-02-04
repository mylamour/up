"""up review - AI-powered code review.

Provides adversarial review of AI-generated code to catch:
- Logic errors
- Security issues
- Performance problems
- Best practice violations
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from up.ai_cli import check_ai_cli, run_ai_prompt
from up.core.checkpoint import get_checkpoint_manager

console = Console()


@click.command("review")
@click.option("--checkpoint", "-c", help="Review changes since checkpoint")
@click.option("--files", "-f", multiple=True, help="Specific files to review")
@click.option("--focus", type=click.Choice(["security", "performance", "logic", "style", "all"]), 
              default="all", help="Focus area for review")
@click.option("--strict", is_flag=True, help="Strict mode - fail on any issue")
@click.option("--model", "-m", help="AI model to use (claude, cursor)")
def review_cmd(checkpoint: str, files: tuple, focus: str, strict: bool, model: str):
    """AI-powered adversarial code review.
    
    Reviews recent AI-generated changes for potential issues.
    Use after 'up start' to verify AI work before committing.
    
    \b
    Examples:
      up review                    # Review all changes
      up review --checkpoint cp-1  # Review since checkpoint
      up review --focus security   # Security-focused review
      up review --files src/auth.py --strict
    """
    cwd = Path.cwd()
    
    # Get diff to review
    if files:
        # Review specific files
        diff_content = _get_files_diff(cwd, list(files))
        files_reviewed = list(files)
    elif checkpoint:
        # Review since checkpoint
        diff_content = _get_checkpoint_diff(cwd, checkpoint)
        files_reviewed = _get_changed_files(cwd, checkpoint)
    else:
        # Review all uncommitted changes
        diff_content = _get_uncommitted_diff(cwd)
        files_reviewed = _get_uncommitted_files(cwd)
    
    if not diff_content or diff_content.strip() == "":
        console.print("[dim]No changes to review[/]")
        return
    
    console.print(Panel.fit(
        "[bold blue]AI Code Review[/]",
        border_style="blue"
    ))
    
    console.print(f"Files to review: [cyan]{len(files_reviewed)}[/]")
    for f in files_reviewed[:5]:
        console.print(f"  • {f}")
    if len(files_reviewed) > 5:
        console.print(f"  ... and {len(files_reviewed) - 5} more")
    
    # Check AI availability
    cli_name = model
    if not cli_name:
        cli_name, available = check_ai_cli()
        if not available:
            console.print("\n[red]Error:[/] No AI CLI available")
            console.print("Install Claude CLI or Cursor Agent for AI review")
            return
    
    console.print(f"\n[yellow]Running review with {cli_name}...[/]")
    
    # Build review prompt
    prompt = _build_review_prompt(diff_content, focus, strict)
    
    # Run AI review
    result = run_ai_prompt(cwd, prompt, cli_name, timeout=180)
    
    if not result:
        console.print("[red]Review failed - no response from AI[/]")
        return
    
    # Display results
    console.print("\n")
    console.print(Panel(
        Markdown(result),
        title="Review Results",
        border_style="yellow" if "issue" in result.lower() or "problem" in result.lower() else "green"
    ))
    
    # Check for issues in strict mode
    if strict:
        issue_indicators = ["issue", "problem", "bug", "error", "vulnerability", "critical", "warning"]
        has_issues = any(indicator in result.lower() for indicator in issue_indicators)
        
        if has_issues:
            console.print("\n[red]⚠ Issues found in strict mode[/]")
            console.print("Consider fixing issues before committing.")
            sys.exit(1)
        else:
            console.print("\n[green]✓ No issues found[/]")


def _get_uncommitted_diff(cwd: Path) -> str:
    """Get diff of uncommitted changes."""
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout if result.returncode == 0 else ""


def _get_uncommitted_files(cwd: Path) -> list:
    """Get list of uncommitted changed files."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return [f for f in result.stdout.strip().split("\n") if f]
    return []


def _get_checkpoint_diff(cwd: Path, checkpoint: str) -> str:
    """Get diff since checkpoint."""
    manager = get_checkpoint_manager(cwd)
    return manager.diff_from_checkpoint(checkpoint)


def _get_changed_files(cwd: Path, checkpoint: str) -> list:
    """Get files changed since checkpoint."""
    tag_name = f"up-checkpoint/{checkpoint}"
    result = subprocess.run(
        ["git", "diff", "--name-only", tag_name, "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return [f for f in result.stdout.strip().split("\n") if f]
    return []


def _get_files_diff(cwd: Path, files: list) -> str:
    """Get diff for specific files."""
    result = subprocess.run(
        ["git", "diff", "HEAD", "--"] + files,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout if result.returncode == 0 else ""


def _build_review_prompt(diff: str, focus: str, strict: bool) -> str:
    """Build the review prompt."""
    # Truncate large diffs
    max_chars = 15000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n\n[... diff truncated ...]"
    
    focus_instructions = {
        "security": """Focus on security issues:
- SQL injection, XSS, CSRF vulnerabilities
- Hardcoded secrets or credentials
- Insecure data handling
- Authentication/authorization flaws
- Input validation issues""",
        
        "performance": """Focus on performance issues:
- O(n²) or worse algorithms
- Memory leaks or inefficient memory use
- Missing caching opportunities
- Unnecessary database queries
- Blocking operations in async code""",
        
        "logic": """Focus on logic issues:
- Off-by-one errors
- Race conditions
- Null/undefined handling
- Edge cases not covered
- Incorrect state management""",
        
        "style": """Focus on code style:
- Naming conventions
- Function/class organization
- Code duplication
- Missing documentation
- Type annotations""",
        
        "all": """Review comprehensively for:
1. Security vulnerabilities
2. Logic errors and bugs
3. Performance issues
4. Code style and best practices"""
    }
    
    severity_note = ""
    if strict:
        severity_note = "\n\nIMPORTANT: This is a strict review. Flag ALL potential issues, even minor ones."
    
    return f"""You are a senior code reviewer conducting an adversarial review of AI-generated code.

{focus_instructions.get(focus, focus_instructions["all"])}
{severity_note}

Review the following diff and provide:

1. **Critical Issues** - Must fix before merging (security, data loss, crashes)
2. **Warnings** - Should fix (bugs, performance, logic errors)  
3. **Suggestions** - Nice to have (style, refactoring)
4. **Summary** - Overall assessment (APPROVE / NEEDS CHANGES / REJECT)

Be specific. Reference line numbers. Suggest fixes.

```diff
{diff}
```

Provide your review:"""
