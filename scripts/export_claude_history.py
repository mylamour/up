#!/usr/bin/env python3
"""
Claude Code Chat History Exporter

Export chat history from Claude Code projects to various formats.
Supports: JSON, Markdown, CSV, and plain text.

Usage:
    python export_claude_history.py <project_path> [options]

Examples:
    python export_claude_history.py /Users/mour/AI/AgenticaSoC --format markdown
    python export_claude_history.py /Users/mour/AI/AgenticaSoC --format json --output export.json
    python export_claude_history.py /Users/mour/AI/AgenticaSoC --list-sessions
"""

import argparse
import json
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_claude_project_path(project_path: str) -> Path:
    """Convert a project path to its Claude storage path."""
    claude_base = Path.home() / ".claude" / "projects"
    # Convert path: /Users/mour/AI/AgenticaSoC -> -Users-mour-AI-AgenticaSoC
    normalized = project_path.replace("/", "-")
    if not normalized.startswith("-"):
        normalized = "-" + normalized
    return claude_base / normalized


def validate_output_path(output_file: Optional[str]) -> None:
    """Validate that output path is not in Claude data directories.

    Raises ValueError if output would write to data source.
    """
    if not output_file:
        return

    output_path = Path(output_file).resolve()
    home = Path.home()

    # Protected directory (Claude data source)
    protected_dir = home / ".claude"

    if protected_dir.exists():
        try:
            output_path.relative_to(protected_dir)
            raise ValueError(
                f"Cannot write to Claude data directory: {output_file}\n"
                f"This would modify the data source. Choose a different output path."
            )
        except ValueError as e:
            if "Cannot write" in str(e):
                raise
            # Not relative to this path, OK
            pass


def get_all_project_paths() -> list:
    """Get all Claude project directories."""
    claude_base = Path.home() / ".claude" / "projects"
    if not claude_base.exists():
        return []
    return sorted([p for p in claude_base.iterdir() if p.is_dir()])


def get_related_project_paths(project_path: str) -> list:
    """Find all related project directories (e.g., -backend, -MetaBrain variants).

    Smart matching: If given a subfolder path like AgenticaSoC-backend,
    it will find the base project (AgenticaSoC) and all its variants.
    """
    claude_base = Path.home() / ".claude" / "projects"
    normalized = project_path.replace("/", "-")
    if not normalized.startswith("-"):
        normalized = "-" + normalized

    if not claude_base.exists():
        return []

    # First, find all potential matches (both directions)
    all_projects = [p for p in claude_base.iterdir() if p.is_dir()]

    # Find projects where: input starts with project OR project starts with input
    candidates = []
    for p in all_projects:
        if p.name.startswith(normalized) or normalized.startswith(p.name):
            candidates.append(p.name)

    if not candidates:
        return []

    # Find the base project (shortest common prefix among candidates)
    base_project = min(candidates, key=len)

    # Now find all projects that start with the base
    related = [p for p in all_projects if p.name.startswith(base_project)]

    return sorted(related)


def load_sessions_index(project_dir: Path) -> list:
    """Load the sessions index file."""
    index_file = project_dir / "sessions-index.json"
    if not index_file.exists():
        return []
    with open(index_file, "r") as f:
        data = json.load(f)
        return data.get("entries", [])


def load_session_messages(session_file: Path) -> list:
    """Load messages from a session JSONL file."""
    messages = []
    if not session_file.exists():
        return messages
    with open(session_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return str(ts) if ts else "Unknown"


def get_message_content(msg: dict) -> str:
    """Extract message content, handling various formats."""
    message = msg.get("message", {})
    content = message.get("content", "")

    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # Handle content blocks (text, tool_use, etc.)
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    parts.append(f"[Tool: {block.get('name', 'unknown')}]")
                elif block.get("type") == "tool_result":
                    parts.append(f"[Tool Result]")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def export_to_json(sessions_data: list, output_file: Optional[str], pretty: bool = True) -> str:
    """Export to JSON format."""
    indent = 2 if pretty else None
    result = json.dumps(sessions_data, indent=indent, ensure_ascii=False)
    if output_file:
        with open(output_file, "w") as f:
            f.write(result)
    return result


def export_to_markdown(sessions_data: list, output_file: Optional[str], no_truncate: bool = False) -> str:
    """Export to Markdown format."""
    lines = ["# Claude Code Chat History Export\n"]
    lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"Total Sessions: {len(sessions_data)}\n")
    lines.append("---\n")

    for session in sessions_data:
        meta = session.get("metadata", {})
        lines.append(f"\n## Session: {meta.get('sessionId', 'Unknown')[:8]}...\n")
        lines.append(f"- **First Prompt**: {meta.get('firstPrompt', 'N/A')[:100]}")
        lines.append(f"- **Created**: {format_timestamp(meta.get('created'))}")
        lines.append(f"- **Messages**: {meta.get('messageCount', 0)}")
        lines.append(f"- **Git Branch**: {meta.get('gitBranch', 'N/A')}\n")
        lines.append("### Conversation\n")

        for msg in session.get("messages", []):
            msg_type = msg.get("type", "unknown")
            timestamp = format_timestamp(msg.get("timestamp"))
            content = get_message_content(msg)

            if msg_type == "user":
                lines.append(f"#### 👤 User ({timestamp})\n")
            elif msg_type == "assistant":
                lines.append(f"#### 🤖 Assistant ({timestamp})\n")
            else:
                lines.append(f"#### {msg_type} ({timestamp})\n")

            # Truncate very long messages unless --no-truncate
            if not no_truncate and len(content) > 5000:
                content = content[:5000] + "\n\n... [truncated]"
            lines.append(f"{content}\n")
            lines.append("---\n")

    result = "\n".join(lines)
    if output_file:
        with open(output_file, "w") as f:
            f.write(result)
    return result


def export_to_csv(sessions_data: list, output_file: Optional[str], no_truncate: bool = False) -> str:
    """Export to CSV format."""
    rows = []
    headers = ["session_id", "timestamp", "type", "git_branch", "content"]

    for session in sessions_data:
        meta = session.get("metadata", {})
        session_id = meta.get("sessionId", "")
        git_branch = meta.get("gitBranch", "")

        for msg in session.get("messages", []):
            content = get_message_content(msg)
            # Truncate for CSV unless --no-truncate
            if not no_truncate and len(content) > 1000:
                content = content[:1000] + "..."
            rows.append({
                "session_id": session_id[:8],
                "timestamp": format_timestamp(msg.get("timestamp")),
                "type": msg.get("type", "unknown"),
                "git_branch": git_branch,
                "content": content.replace("\n", " ")
            })

    if output_file:
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    # Return as string
    import io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_to_text(sessions_data: list, output_file: Optional[str], no_truncate: bool = False) -> str:
    """Export to plain text format."""
    lines = ["CLAUDE CODE CHAT HISTORY EXPORT", "=" * 50, ""]

    for session in sessions_data:
        meta = session.get("metadata", {})
        lines.append(f"SESSION: {meta.get('sessionId', 'Unknown')[:8]}")
        lines.append(f"Created: {format_timestamp(meta.get('created'))}")
        lines.append("-" * 40)

        for msg in session.get("messages", []):
            msg_type = msg.get("type", "unknown").upper()
            timestamp = format_timestamp(msg.get("timestamp"))
            content = get_message_content(msg)

            # Truncate unless --no-truncate
            if not no_truncate and len(content) > 3000:
                content = content[:3000] + "\n... [truncated]"

            lines.append(f"\n[{msg_type}] {timestamp}")
            lines.append(content)
            lines.append("")

        lines.append("=" * 50)
        lines.append("")

    result = "\n".join(lines)
    if output_file:
        with open(output_file, "w") as f:
            f.write(result)
    return result


def list_sessions(project_dir: Path) -> None:
    """List all sessions in a project."""
    sessions = load_sessions_index(project_dir)
    if not sessions:
        print("No sessions found.")
        return

    print(f"\nFound {len(sessions)} sessions:\n")
    print(f"{'ID':<10} {'Messages':<10} {'Created':<20} {'First Prompt':<50}")
    print("-" * 90)

    for s in sorted(sessions, key=lambda x: x.get("created", ""), reverse=True):
        sid = s.get("sessionId", "")[:8]
        msg_count = s.get("messageCount", 0)
        created = format_timestamp(s.get("created"))
        first_prompt = s.get("firstPrompt", "N/A")[:47]
        if len(s.get("firstPrompt", "")) > 47:
            first_prompt += "..."
        print(f"{sid:<10} {msg_count:<10} {created:<20} {first_prompt:<50}")


def show_stats(project_dirs: list) -> None:
    """Show chat count analysis and statistics with visualization."""
    stats = {
        "total_sessions": 0,
        "total_messages": 0,
        "user_messages": 0,
        "assistant_messages": 0,
        "by_project": {},
        "by_month": {},
    }

    for project_dir in project_dirs:
        project_name = project_dir.name
        sessions = load_sessions_index(project_dir)
        project_stats = {"sessions": 0, "messages": 0, "user": 0, "assistant": 0}

        for entry in sessions:
            session_file = project_dir / f"{entry.get('sessionId', '')}.jsonl"
            messages = load_session_messages(session_file)

            project_stats["sessions"] += 1
            project_stats["messages"] += len(messages)

            for msg in messages:
                msg_type = msg.get("type", "")
                if msg_type == "user":
                    project_stats["user"] += 1
                elif msg_type == "assistant":
                    project_stats["assistant"] += 1

                # Track by month
                ts = msg.get("timestamp", "")
                if ts:
                    month = ts[:7]  # YYYY-MM
                    stats["by_month"][month] = stats["by_month"].get(month, 0) + 1

        stats["by_project"][project_name] = project_stats
        stats["total_sessions"] += project_stats["sessions"]
        stats["total_messages"] += project_stats["messages"]
        stats["user_messages"] += project_stats["user"]
        stats["assistant_messages"] += project_stats["assistant"]

    _print_stats(stats)


def _print_stats(stats: dict) -> None:
    """Print formatted statistics with ASCII visualization."""
    print("\n" + "=" * 60)
    print("CLAUDE CODE CHAT STATISTICS")
    print("=" * 60)

    # Summary
    print(f"\n{'SUMMARY':^60}")
    print("-" * 60)
    print(f"  Total Sessions:    {stats['total_sessions']:>10}")
    print(f"  Total Messages:    {stats['total_messages']:>10}")
    print(f"  User Messages:     {stats['user_messages']:>10}")
    print(f"  Assistant Messages:{stats['assistant_messages']:>10}")

    # By Project
    if stats["by_project"]:
        print(f"\n{'MESSAGES BY PROJECT':^60}")
        print("-" * 60)
        max_msgs = max(p["messages"] for p in stats["by_project"].values()) or 1
        bar_width = 30

        for name, data in sorted(stats["by_project"].items()):
            short_name = name[-35:] if len(name) > 35 else name
            bar_len = int((data["messages"] / max_msgs) * bar_width)
            bar = "#" * bar_len
            print(f"  {short_name}")
            print(f"    [{bar:<{bar_width}}] {data['messages']:>5} msgs, {data['sessions']:>3} sessions")

    # By Month
    if stats["by_month"]:
        print(f"\n{'ACTIVITY BY MONTH':^60}")
        print("-" * 60)
        sorted_months = sorted(stats["by_month"].items())
        max_monthly = max(stats["by_month"].values()) or 1

        for month, count in sorted_months:
            bar_len = int((count / max_monthly) * bar_width)
            bar = "#" * bar_len
            print(f"  {month}  [{bar:<{bar_width}}] {count:>5}")

    print("\n" + "=" * 60)


def load_project_data(project_dir: Path, session_id: Optional[str] = None,
                      role_filter: Optional[str] = None) -> list:
    """Load all session data from a project.

    Args:
        project_dir: Path to the Claude project directory
        session_id: Optional session ID prefix to filter
        role_filter: Optional role filter ('user', 'assistant', or None for all)
    """
    sessions_index = load_sessions_index(project_dir)
    sessions_data = []

    for entry in sessions_index:
        sid = entry.get("sessionId", "")

        # Filter by session ID if specified
        if session_id and not sid.startswith(session_id):
            continue

        session_file = project_dir / f"{sid}.jsonl"
        messages = load_session_messages(session_file)

        # Filter messages by role if specified
        if role_filter:
            messages = [m for m in messages if m.get("type") == role_filter]

        # Add project name to metadata for multi-project exports
        entry_copy = entry.copy()
        entry_copy["projectDir"] = project_dir.name

        sessions_data.append({
            "metadata": entry_copy,
            "messages": messages
        })

    return sessions_data


def main():
    parser = argparse.ArgumentParser(
        description="Export Claude Code chat history to various formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all -f json -o all_history.json           # Export ALL projects
  %(prog)s --all --stats                               # Stats for all projects
  %(prog)s /Users/mour/AI/AgenticaSoC -l                    # List all sessions
  %(prog)s /Users/mour/AI/AgenticaSoC -f markdown -o out.md # Export to markdown
  %(prog)s /Users/mour/AI/AgenticaSoC -f json -o out.json   # Export to JSON
  %(prog)s /Users/mour/AI/AgenticaSoC -r user -o prompts.md # User prompts only
  %(prog)s /Users/mour/AI/AgenticaSoC -s abc123             # Specific session
  %(prog)s /Users/mour/AI/AgenticaSoC --no-related          # Exact project only
        """
    )

    parser.add_argument(
        "project_path",
        nargs="?",
        default=None,
        help="Path to the project (e.g., /Users/mour/AI/AgenticaSoC). Optional if --all is used."
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Export ALL projects (no project path required)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "markdown", "csv", "text"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "-s", "--session",
        help="Export only a specific session (by ID prefix)"
    )
    parser.add_argument(
        "-l", "--list-sessions",
        action="store_true",
        help="List all sessions in the project"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show chat count analysis and statistics"
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Don't truncate long messages"
    )
    parser.add_argument(
        "-r", "--role",
        choices=["user", "assistant"],
        help="Filter by role: 'user' for prompts only, 'assistant' for responses only"
    )
    parser.add_argument(
        "--no-related",
        action="store_true",
        help="Only export the exact project, not related variants (default: include all related)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.all and not args.project_path:
        parser.error("Either project_path or --all is required")

    # Get project directories
    if args.all:
        project_dirs = get_all_project_paths()
        if not project_dirs:
            print("Error: No Claude projects found.", file=sys.stderr)
            projects_base = Path.home() / ".claude" / "projects"
            print(f"Expected location: {projects_base}", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(project_dirs)} project(s) total", file=sys.stderr)
    elif args.no_related:
        project_dir = get_claude_project_path(args.project_path)
        if not project_dir.exists():
            print(f"Error: Project directory not found: {project_dir}", file=sys.stderr)
            print(f"\nAvailable projects:", file=sys.stderr)
            projects_base = Path.home() / ".claude" / "projects"
            if projects_base.exists():
                for p in sorted(projects_base.iterdir()):
                    if p.is_dir():
                        print(f"  {p.name}", file=sys.stderr)
            sys.exit(1)
        project_dirs = [project_dir]
    else:
        project_dirs = get_related_project_paths(args.project_path)
        if not project_dirs:
            print(f"Error: No matching projects found for: {args.project_path}", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(project_dirs)} related project(s):", file=sys.stderr)
        for pd in project_dirs:
            print(f"  - {pd.name}", file=sys.stderr)

    # List sessions mode
    if args.list_sessions:
        for pd in project_dirs:
            print(f"\n=== {pd.name} ===", file=sys.stderr)
            list_sessions(pd)
        return

    # Stats mode
    if args.stats:
        show_stats(project_dirs)
        return

    # Load session data from all project directories
    sessions_data = []
    for pd in project_dirs:
        print(f"Loading sessions from: {pd.name}", file=sys.stderr)
        data = load_project_data(pd, args.session, args.role)
        sessions_data.extend(data)

    if not sessions_data:
        print("No sessions found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(sessions_data)} session(s)", file=sys.stderr)

    # Export based on format
    output_file = args.output

    # Validate output path is not in data source directories
    validate_output_path(output_file)

    result = ""

    if args.format == "json":
        result = export_to_json(sessions_data, output_file)
    elif args.format == "markdown":
        result = export_to_markdown(sessions_data, output_file, args.no_truncate)
    elif args.format == "csv":
        result = export_to_csv(sessions_data, output_file, args.no_truncate)
    elif args.format == "text":
        result = export_to_text(sessions_data, output_file, args.no_truncate)

    # Print to stdout if no output file specified
    if not output_file:
        print(result)
    else:
        print(f"Exported to: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
