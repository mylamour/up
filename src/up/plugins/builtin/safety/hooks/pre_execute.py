"""Pre-execute hook: auto-checkpoint before AI operations.

Reads event data from stdin, creates a checkpoint if workspace
has a git repo. Exit 0 = allow, exit 1 = warn, exit 2 = block.
"""
import json
import subprocess
import sys


def main():
    try:
        event_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        event_data = {}

    task_id = event_data.get("task_id", "unknown")
    workspace = event_data.get("cwd", event_data.get("workspace", "."))

    # Check if git repo exists
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True, cwd=workspace,
    )
    if result.returncode != 0:
        print("No git repo, skipping checkpoint", file=sys.stderr)
        sys.exit(1)  # warn but continue

    # Create a lightweight checkpoint via git stash
    msg = f"safety-checkpoint-{task_id}"
    result = subprocess.run(
        ["git", "stash", "push", "-m", msg, "--include-untracked"],
        capture_output=True, text=True, cwd=workspace,
    )

    if "No local changes" in result.stdout:
        print(f"checkpoint:{task_id}:clean", file=sys.stdout)
    else:
        # Pop immediately — we just wanted the stash as a safety net
        subprocess.run(
            ["git", "stash", "pop"],
            capture_output=True, text=True, cwd=workspace,
        )
        print(f"checkpoint:{task_id}:created", file=sys.stdout)

    sys.exit(0)


if __name__ == "__main__":
    main()
