#!/usr/bin/env python3
"""Auto-record hook: save errors after consecutive failures.

Triggers on TASK_FAILED when consecutive_failures >= threshold.
Also triggers on TASK_COMPLETE after previous failures to record the solution.

Exit codes:
  0 = allow (recorded or skipped)
  1 = warn (recorded to memory)
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


def _load_config(workspace):
    """Load auto_record config from .up/config.json."""
    config_path = os.path.join(workspace, ".up", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            mem_cfg = cfg.get("automation", {}).get("memory", {})
            return {
                "enabled": mem_cfg.get("auto_record", True),
                "threshold": mem_cfg.get("auto_record_threshold", 2),
            }
        except (json.JSONDecodeError, OSError):
            pass
    return {"enabled": True, "threshold": 2}


def _error_signature(error_text):
    """Generate a dedup signature from error text."""
    from up.memory.patterns import ErrorPatternExtractor

    extractor = ErrorPatternExtractor()
    keywords = extractor.extract(error_text)
    sig_input = " ".join(keywords) if keywords else error_text[:200]
    return hashlib.md5(sig_input.encode()).hexdigest()


def _is_duplicate(manager, signature, hours=24):
    """Check if an identical error signature was recorded recently."""
    results = manager.search(signature, limit=5, entry_type="error")
    if not results:
        return False
    cutoff = datetime.now() - timedelta(hours=hours)
    for entry in results:
        meta = entry.metadata if hasattr(entry, "metadata") else {}
        if isinstance(meta, dict) and meta.get("error_signature") == signature:
            ts = entry.timestamp if hasattr(entry, "timestamp") else ""
            try:
                entry_time = datetime.fromisoformat(ts)
                if entry_time > cutoff:
                    return True
            except (ValueError, TypeError):
                pass
    return False


def main():
    event_data = json.loads(sys.stdin.read())
    workspace = Path(os.getcwd())

    config = _load_config(workspace)
    if not config["enabled"]:
        sys.exit(0)

    event_type = event_data.get("event_type", "")
    consecutive_failures = event_data.get("consecutive_failures", 0)
    threshold = config["threshold"]

    try:
        from up.events import emit_error

        # TASK_COMPLETE after previous failures → record the solution
        if event_type == "task_complete":
            prev_error = event_data.get("previous_error", "")
            solution = event_data.get("solution", "") or event_data.get("output", "")
            if prev_error and solution:
                emit_error(prev_error[:500], solution[:500], source="auto_record")
                hint = {"recorded": "solution", "error": prev_error[:100]}
                print(json.dumps(hint))
                print(
                    f"Memory record: saved solution for '{prev_error[:60]}'",
                    file=sys.stderr,
                )
                sys.exit(1)
            sys.exit(0)

        # TASK_FAILED → record error if threshold met
        if event_type == "task_failed":
            if consecutive_failures < threshold:
                sys.exit(0)

            error_output = event_data.get("error", "") or event_data.get("output", "")
            if not error_output:
                sys.exit(0)

            signature = _error_signature(error_output)

            # We still need MemoryManager to check for duplicates
            from up.memory import MemoryManager
            manager = MemoryManager(workspace, use_vectors=False)
            if _is_duplicate(manager, signature):
                sys.exit(0)

            task_id = event_data.get("task_id", "unknown")
            
            emit_error(error_output[:500], source="auto_record")

            hint = {
                "recorded": "error",
                "signature": signature,
                "task_id": task_id,
            }
            print(json.dumps(hint))
            print(
                f"Memory record: saved error for task '{task_id}' "
                f"(failures: {consecutive_failures})",
                file=sys.stderr,
            )
            sys.exit(1)

    except Exception as e:
        print(f"auto_record error: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
