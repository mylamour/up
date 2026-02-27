#!/usr/bin/env python3
"""Session priming hook: inject relevant memories when a task starts.

Triggers on TASK_START events. Queries memory for context relevant to
the current task description, recent decisions, and known error patterns.

Exit codes:
  0 = allow (no relevant context)
  1 = warn (context found, injected as hint)
"""

import json
import os
import sys
from pathlib import Path


def _load_config(workspace):
    """Load session_prime config from .up/config.json."""
    config_path = os.path.join(workspace, ".up", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            return cfg.get("automation", {}).get("memory", {}).get("session_prime", True)
        except (json.JSONDecodeError, OSError):
            pass
    return True


def main():
    event_data = json.loads(sys.stdin.read())
    workspace = Path(os.getcwd())

    if not _load_config(workspace):
        sys.exit(0)

    task_id = event_data.get("task_id", "")
    task_title = event_data.get("task", "") or event_data.get("task_title", "")

    if not task_title:
        sys.exit(0)

    try:
        from up.memory import MemoryManager

        manager = MemoryManager(workspace, use_vectors=False)
        hints = []

        # Search for relevant past context based on task description
        results = manager.search(task_title, limit=3)
        for r in results:
            content = r.content if hasattr(r, "content") else str(r)
            entry_type = r.type if hasattr(r, "type") else "unknown"
            if content.strip():
                hints.append({"type": entry_type, "content": content.strip()[:300]})

        # Get recent decisions (always useful context)
        decisions = manager.store.get_by_type("decision", limit=3)
        for d in decisions:
            content = d.content if hasattr(d, "content") else str(d)
            if content.strip() and not any(h["content"] == content.strip()[:300] for h in hints):
                hints.append({"type": "decision", "content": content.strip()[:300]})

        if hints:
            output = {
                "session_context": hints[:5],
                "task_id": task_id,
            }
            print(json.dumps(output))
            print(
                f"Session prime: {len(hints)} relevant memories for '{task_title[:40]}'",
                file=sys.stderr,
            )
            sys.exit(1)  # warn: context found

    except Exception as e:
        print(f"session_prime error: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
