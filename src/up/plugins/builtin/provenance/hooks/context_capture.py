#!/usr/bin/env python3
"""Context capture hook: record prompt hash and context files.

PRE_EXECUTE: captures prompt hash and context files.
POST_EXECUTE: links context to completion record with duration.

Exit codes:
  0 = allow (captured or skipped)
  1 = warn (context captured)
"""

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

# File path patterns to detect in prompts
_FILE_PATH_RE = re.compile(
    r"(?:^|\s)([a-zA-Z0-9_./-]+\.(?:py|js|ts|tsx|go|rs|java|rb|md|json|yaml|yml|toml))"
    r"(?:\s|$|:|\))",
)

# State file for linking pre/post execute
_STATE_FILE = ".up/provenance/_context_state.json"


def _detect_context_files(prompt_text):
    """Scan prompt for file path patterns."""
    matches = _FILE_PATH_RE.findall(prompt_text)
    # Deduplicate and filter obvious non-paths
    seen = set()
    files = []
    for m in matches:
        if m not in seen and "/" in m or m.count(".") <= 2:
            seen.add(m)
            files.append(m)
    return files[:20]  # Cap at 20


def _hash_prompt(prompt_text):
    """SHA-256 hash of prompt text."""
    return hashlib.sha256(prompt_text.encode()).hexdigest()


def main():
    event_data = json.loads(sys.stdin.read())
    workspace = Path(os.getcwd())
    event_type = event_data.get("event_type", "")

    try:
        if event_type == "pre_execute":
            _handle_pre_execute(workspace, event_data)
        elif event_type == "post_execute":
            _handle_post_execute(workspace, event_data)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"context_capture error: {e}", file=sys.stderr)
        sys.exit(0)


def _handle_pre_execute(workspace, event_data):
    """Capture prompt hash and context files before execution."""
    prompt = event_data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    prompt_hash = _hash_prompt(prompt)
    context_files = _detect_context_files(prompt)
    task_id = event_data.get("task_id", "unknown")

    # Save state for post_execute to pick up
    state_path = workspace / _STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({
        "task_id": task_id,
        "prompt_hash": prompt_hash,
        "context_files": context_files,
        "start_time": time.time(),
    }))

    hint = {
        "prompt_hash": prompt_hash,
        "context_files": context_files,
    }
    print(json.dumps(hint))
    print(
        f"Context capture: hash={prompt_hash[:12]}.. "
        f"files={len(context_files)}",
        file=sys.stderr,
    )
    sys.exit(1)


def _handle_post_execute(workspace, event_data):
    """Link pre-execute context to completion record."""
    state_path = workspace / _STATE_FILE
    if not state_path.exists():
        sys.exit(0)

    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    start_time = state.get("start_time", 0)
    duration = time.time() - start_time if start_time else 0

    hint = {
        "prompt_hash": state.get("prompt_hash", ""),
        "context_files": state.get("context_files", []),
        "duration_seconds": round(duration, 1),
    }
    print(json.dumps(hint))
    print(
        f"Context capture: duration={duration:.1f}s",
        file=sys.stderr,
    )

    # Clean up state file
    try:
        state_path.unlink()
    except OSError:
        pass

    sys.exit(1)


if __name__ == "__main__":
    main()
