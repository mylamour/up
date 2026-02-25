#!/usr/bin/env python3
"""Example hook script.

Reads event data from stdin (JSON), processes it,
and exits with appropriate code.

Exit codes:
  0 = allow (no issues)
  1 = warn (log warning, continue)
  2+ = block (halt operation)
"""

import json
import sys


def main():
    try:
        event_data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    event_type = event_data.get("event_type", "")

    # Add your hook logic here
    # Example: warn on TODO comments in modified files
    files = event_data.get("files_modified", [])
    if files:
        print(json.dumps({"checked_files": len(files)}))

    sys.exit(0)


if __name__ == "__main__":
    main()
