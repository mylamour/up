#!/usr/bin/env python3
"""Provenance auto-record hook: track AI operations.

Triggers on TASK_COMPLETE and TASK_FAILED events. Records provenance
entries with Merkle chain integrity using ProvenanceManager.

Exit codes:
  0 = allow (recorded or skipped)
  1 = warn (recorded to provenance)
"""

import json
import sys
import os
from pathlib import Path


def main():
    event_data = json.loads(sys.stdin.read())
    workspace = Path(os.getcwd())

    event_type = event_data.get("event_type", "")
    if event_type not in ("task_complete", "task_failed"):
        sys.exit(0)

    task_id = event_data.get("task_id", "")
    task_title = event_data.get("task_title", task_id)
    if not task_id:
        sys.exit(0)

    try:
        from up.core.provenance import get_provenance_manager

        manager = get_provenance_manager(workspace)

        # Check if entry already exists for this task
        existing = manager.get_entry_for_task(task_id)
        if existing and existing.status != "pending":
            sys.exit(0)

        ai_model = event_data.get("ai_model", "unknown")
        prompt = event_data.get("prompt", "")
        context_files = event_data.get("context_files", [])
        files_modified = event_data.get("files_modified", [])

        if existing and existing.status == "pending":
            # Complete existing entry
            status = "accepted" if event_type == "task_complete" else "rejected"
            entry = manager.complete_operation(
                entry_id=existing.id,
                files_modified=files_modified,
                tests_passed=event_data.get("tests_passed"),
                lint_passed=event_data.get("lint_passed"),
                type_check_passed=event_data.get("type_check_passed"),
                status=status,
            )
        else:
            # Create new entry
            entry = manager.start_operation(
                task_id=task_id,
                task_title=task_title,
                prompt=prompt or f"Task: {task_title}",
                ai_model=ai_model,
                context_files=context_files,
            )

            status = "accepted" if event_type == "task_complete" else "rejected"
            reason = event_data.get("error", "") if event_type == "task_failed" else ""

            if event_type == "task_failed":
                manager.reject_operation(entry.id, reason=reason[:500])
            else:
                manager.complete_operation(
                    entry_id=entry.id,
                    files_modified=files_modified,
                    tests_passed=event_data.get("tests_passed"),
                    lint_passed=event_data.get("lint_passed"),
                    type_check_passed=event_data.get("type_check_passed"),
                    status="accepted",
                )

        hint = {
            "provenance_id": entry.id,
            "parent_id": entry.parent_id,
            "status": status,
        }
        print(json.dumps(hint))
        print(
            f"Provenance: recorded {status} for task '{task_id}' "
            f"(chain: {entry.parent_id[:8]}..{entry.id[:8]})",
            file=sys.stderr,
        )
        sys.exit(1)  # warn: recorded

    except Exception as e:
        print(f"provenance auto_record error: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
