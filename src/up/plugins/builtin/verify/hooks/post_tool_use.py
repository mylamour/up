"""Post-tool-use hook: run verification with confidence scoring.

After file modifications, runs configured test/lint/typecheck commands
and produces a confidence score (0-100).

Exit 0 = above threshold, exit 1 = below threshold (warn), exit 2 = block.
"""
import json
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, workspace):
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=120, cwd=workspace,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def main():
    try:
        event_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        event_data = {}

    workspace = Path(event_data.get("cwd", event_data.get("workspace", ".")))
    tool_name = event_data.get("tool_name", "")

    # Only verify after file-modifying tools
    if tool_name not in ("Edit", "Write", "Bash"):
        print(json.dumps({"confidence": 100, "skipped": True}))
        sys.exit(0)

    # Load config
    config_file = workspace / ".up" / "config.json"
    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    verify_config = config.get("verify", {})
    test_cmd = verify_config.get("test_cmd", "")
    lint_cmd = verify_config.get("lint_cmd", "")
    typecheck_cmd = verify_config.get("typecheck_cmd", "")
    min_confidence = verify_config.get("min_confidence", 70)

    # Calculate confidence score
    score = 100
    results = {}

    if test_cmd:
        ok, output = run_cmd(test_cmd, str(workspace))
        results["tests"] = ok
        if not ok:
            score -= 60  # test failures are severe

    if lint_cmd:
        ok, output = run_cmd(lint_cmd, str(workspace))
        results["lint"] = ok
        if not ok:
            score -= 20  # lint warnings reduce confidence

    if typecheck_cmd:
        ok, output = run_cmd(typecheck_cmd, str(workspace))
        results["typecheck"] = ok
        if not ok:
            score -= 20  # type errors reduce confidence

    score = max(0, score)
    results["confidence"] = score
    results["threshold"] = min_confidence

    output_json = json.dumps(results)
    print(output_json)

    if score < min_confidence:
        print(
            f"Confidence {score}% below threshold {min_confidence}%",
            file=sys.stderr,
        )
        sys.exit(1)  # warn, don't block

    sys.exit(0)


if __name__ == "__main__":
    main()
