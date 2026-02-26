#!/usr/bin/env python3
"""Auto-recall hook: search memory on task failure.

Triggers on TASK_FAILED and VERIFY_FAIL events. Uses ErrorPatternExtractor
to get search keywords, then searches memory for past solutions.

Exit codes:
  0 = allow (hint found or no match)
  1 = warn (hint found, logged to stderr)
"""

import json
import sys
import os
from pathlib import Path


def _load_config(workspace):
    """Load auto_recall config from .up/config.json."""
    config_path = os.path.join(workspace, ".up", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            return cfg.get("automation", {}).get("memory", {}).get("auto_recall", True)
        except (json.JSONDecodeError, OSError):
            pass
    return True


def main():
    event_data = json.loads(sys.stdin.read())
    workspace = Path(os.getcwd())

    if not _load_config(workspace):
        sys.exit(0)

    error_output = event_data.get("error", "") or event_data.get("output", "")
    if not error_output:
        sys.exit(0)

    try:
        from up.memory.patterns import ErrorPatternExtractor
        from up.memory import MemoryManager

        extractor = ErrorPatternExtractor()
        keywords = extractor.extract(error_output)
        if not keywords:
            sys.exit(0)

        query = " ".join(keywords)
        manager = MemoryManager(workspace, use_vectors=False)
        results = manager.search(query, limit=3, entry_type="error")

        if results:
            best = results[0]
            content = best.content if hasattr(best, "content") else str(best)
            hint = {"memory_hint": content, "hint_query": query}
            print(json.dumps(hint))
            print(f"Memory recall: found past solution for '{query}'", file=sys.stderr)
            sys.exit(1)  # warn: hint found
    except Exception as e:
        print(f"auto_recall error: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
