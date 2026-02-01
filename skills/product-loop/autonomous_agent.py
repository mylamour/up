#!/usr/bin/env python3
"""
Autonomous AI Agent for Product Development

Uses Claude CLI (the `claude` command you already have) to run autonomously.
NO API keys needed - just uses your existing Claude CLI setup.

Usage:
    # Run in background (fully autonomous)
    nohup python autonomous_agent.py > agent.log 2>&1 &
    
    # Or use the start script
    ./start-autonomous.sh start
    
    # Monitor progress
    tail -f agent.log
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# =============================================================================
# Configuration
# =============================================================================

MAX_ITERATIONS = 200
SLEEP_BETWEEN = 10  # seconds between iterations
WORKSPACE = Path(__file__).parent.parent.parent.parent.resolve()
LOG_FILE = WORKSPACE / "agent.log"

# Files to track state
STATE_FILES = [
    "TODO.md",
    "docs/todo/V1_RELEASE_CHECKLIST.md",
    "docs/todo/DESIGN_IMPROVEMENTS.md",
    "CHANGELOG.md",
]

# =============================================================================
# Logging
# =============================================================================

def log(msg: str, level: str = "INFO"):
    """Log message with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    sys.stdout.flush()

# =============================================================================
# File Operations
# =============================================================================

def read_file(path: str) -> str:
    """Read a file relative to workspace."""
    full_path = WORKSPACE / path
    try:
        return full_path.read_text()
    except Exception as e:
        return f"[Error reading {path}: {e}]"

# =============================================================================
# State Analysis
# =============================================================================

def get_next_task() -> Optional[str]:
    """Find the next uncompleted task."""
    
    # Check V1 Release Checklist first
    checklist = read_file("docs/todo/V1_RELEASE_CHECKLIST.md")
    unchecked = re.findall(r'^- \[ \] (.+)$', checklist, re.MULTILINE)
    if unchecked:
        return f"From V1_RELEASE_CHECKLIST.md: {unchecked[0]}"
    
    # Check TODO.md for 🔴 items
    todo = read_file("TODO.md")
    red_items = re.findall(r'### 🔴 (?:Feature|Bug): (.+)', todo)
    if red_items:
        return f"From TODO.md: {red_items[0]}"
    
    return None

def is_complete() -> bool:
    """Check if all tasks are done."""
    checklist = read_file("docs/todo/V1_RELEASE_CHECKLIST.md")
    unchecked = re.findall(r'^- \[ \] ', checklist, re.MULTILINE)
    
    todo = read_file("TODO.md")
    red_items = re.findall(r'### 🔴 ', todo)
    
    return len(unchecked) == 0 and len(red_items) == 0

# =============================================================================
# Claude CLI
# =============================================================================

def call_claude(prompt: str, timeout: int = 900) -> tuple[bool, str]:
    """
    Call Claude CLI with a prompt.
    Returns (success, output).
    """
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=timeout  # 15 min timeout
        )
        return True, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Claude CLI timed out after 15 minutes"
    except FileNotFoundError:
        return False, "Claude CLI not found. Make sure 'claude' command is in PATH"
    except Exception as e:
        return False, f"Error calling Claude CLI: {e}"

# =============================================================================
# Main Loop
# =============================================================================

def run_agent(max_iterations: int):
    """Run the autonomous agent loop using Claude CLI."""
    log("=" * 60)
    log("AUTONOMOUS AGENT STARTED (using Claude CLI)")
    log(f"Workspace: {WORKSPACE}")
    log(f"Max iterations: {max_iterations}")
    log("=" * 60)
    
    # Verify Claude CLI exists
    success, output = call_claude("echo 'test'", timeout=30)
    if not success and "not found" in output:
        log("ERROR: Claude CLI not found!", "ERROR")
        log("Make sure the 'claude' command is installed and in your PATH")
        return False
    
    for i in range(1, max_iterations + 1):
        log(f"\n{'='*60}")
        log(f"ITERATION {i}/{max_iterations}")
        log("=" * 60)
        
        # Check if already complete
        if is_complete():
            log("🎉 PRODUCT BUILD COMPLETE! 🎉")
            log("All checklist items are done!")
            return True
        
        # Find next task
        task = get_next_task()
        if not task:
            log("No more tasks found!")
            log("🎉 PRODUCT BUILD COMPLETE! 🎉")
            return True
        
        log(f"Next task: {task}")
        
        # Build prompt for Claude CLI
        prompt = f"""/product-loop

Focus on this specific task: {task}

Instructions:
1. Implement this ONE task
2. Update the checklist to mark it [x] complete
3. Run tests to verify
4. If you finish, check for more tasks
"""
        
        # Call Claude CLI
        log("Calling Claude CLI...")
        log("(This may take 10-15 minutes per iteration)")
        
        success, output = call_claude(prompt)
        
        if not success:
            log(f"Claude CLI error: {output}", "ERROR")
            log("Waiting 60 seconds before retry...")
            time.sleep(60)
            continue
        
        # Log output summary
        output_lines = output.strip().split('\n')
        log(f"Claude output: {len(output_lines)} lines")
        
        # Show last few lines
        if output_lines:
            log("Last 10 lines of output:")
            for line in output_lines[-10:]:
                log(f"  {line[:100]}")
        
        # Check for completion marker
        if "PRODUCT BUILD COMPLETE" in output:
            log("🎉 PRODUCT BUILD COMPLETE! 🎉")
            return True
        
        # Check for DEV LOOP COMPLETE (from nested skill)
        if "DEV LOOP COMPLETE" in output:
            log("Dev loop iteration complete, continuing...")
        
        # Brief pause before next iteration
        log(f"Sleeping {SLEEP_BETWEEN} seconds...")
        time.sleep(SLEEP_BETWEEN)
    
    log(f"Reached max iterations ({max_iterations})")
    return False

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous AI Agent using Claude CLI"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Maximum iterations (default: {MAX_ITERATIONS})"
    )
    args = parser.parse_args()
    
    success = run_agent(args.max_iterations)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
