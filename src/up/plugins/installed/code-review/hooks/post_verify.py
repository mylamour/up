#!/usr/bin/env python3
"""Post-verify hook: adversarial code review of changed files.

Reads event data from stdin, reviews changed files, and reports
findings with confidence >= 80.

Exit codes: 0 = no issues, 1 = warnings found.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def _load_config(workspace: Path) -> dict:
    """Load review config from .up/config.json."""
    config_path = workspace / ".up" / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            return data.get("review", {})
        except Exception:
            pass
    return {}


def _get_changed_files(workspace: Path) -> list[str]:
    """Get files changed in the last commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            capture_output=True, text=True, cwd=workspace,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        pass
    return []


def _basic_review(filepath: str, workspace: Path) -> list[dict]:
    """Run basic pattern-based review on a file."""
    findings = []
    full_path = workspace / filepath

    if not full_path.exists():
        return findings

    try:
        content = full_path.read_text()
    except Exception:
        return findings

    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check for common issues
        if "TODO" in stripped and "FIXME" not in stripped:
            findings.append({
                "file": filepath, "line": i,
                "severity": "low", "confidence": 60,
                "description": "TODO comment found",
            })

        if "except:" in stripped and "except Exception" not in stripped:
            findings.append({
                "file": filepath, "line": i,
                "severity": "medium", "confidence": 85,
                "description": "Bare except clause catches all exceptions",
            })

        if "password" in stripped.lower() and "=" in stripped:
            if not stripped.startswith("#") and not stripped.startswith("//"):
                findings.append({
                    "file": filepath, "line": i,
                    "severity": "high", "confidence": 90,
                    "description": "Possible hardcoded password",
                })

    return findings


def main():
    """Run post-verify review hook."""
    workspace = Path(os.getcwd())
    config = _load_config(workspace)

    if not config.get("enabled", False):
        sys.exit(0)

    try:
        event_data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    event_type = event_data.get("event_type", "")
    if event_type not in ("post_verify", "post_execute"):
        sys.exit(0)

    changed = _get_changed_files(workspace)
    if not changed:
        sys.exit(0)

    all_findings = []
    min_confidence = config.get("min_confidence", 80)

    for filepath in changed:
        findings = _basic_review(filepath, workspace)
        high_conf = [f for f in findings if f["confidence"] >= min_confidence]
        all_findings.extend(high_conf)

    if all_findings:
        output = {
            "review_findings": all_findings,
            "total": len(all_findings),
            "files_reviewed": len(changed),
        }
        print(json.dumps(output))
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
