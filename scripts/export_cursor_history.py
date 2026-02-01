#!/usr/bin/env python3
"""
Cursor Chat History Exporter

Export chat history from Cursor AI to various formats.
Supports: JSON, Markdown, CSV, and plain text.

Usage:
    python export_cursor_history.py [options]

Examples:
    python export_cursor_history.py --format markdown
    python export_cursor_history.py --format json --output export.json
    python export_cursor_history.py --list-sessions
    python export_cursor_history.py --stats
"""

import argparse
import json
import csv
import io
import os
import sys
import sqlite3
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


def get_db_path() -> Path:
    """Get Cursor main database path based on platform."""
    home = Path.home()
    system = platform.system()

    if system == "Darwin":  # macOS
        return home / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
    elif system == "Windows":
        return home / "AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
    else:  # Linux
        # Check for SSH remote first
        ssh_path = home / ".cursor-server/data/User/globalStorage/state.vscdb"
        if ssh_path.exists():
            return ssh_path
        return home / ".config/Cursor/User/globalStorage/state.vscdb"


def get_all_db_paths() -> List[Path]:
    """Find all Cursor database files (global + workspace)."""
    db_paths = []
    home = Path.home()
    system = platform.system()

    # Determine base paths based on platform
    if system == "Darwin":
        base = home / "Library/Application Support/Cursor/User"
    elif system == "Windows":
        base = home / "AppData/Roaming/Cursor/User"
    else:
        base = home / ".config/Cursor/User"
        # Also check SSH remote path
        ssh_base = home / ".cursor-server/data/User"
        if ssh_base.exists():
            base = ssh_base

    # Add global database
    global_db = base / "globalStorage/state.vscdb"
    if global_db.exists():
        db_paths.append(global_db)

    # Add workspace databases
    workspace_dir = base / "workspaceStorage"
    if workspace_dir.exists():
        for ws in workspace_dir.iterdir():
            if ws.is_dir():
                ws_db = ws / "state.vscdb"
                if ws_db.exists():
                    db_paths.append(ws_db)

    return db_paths


def get_workspace_path() -> Path:
    """Get Cursor workspace storage path."""
    home = Path.home()
    system = platform.system()

    if system == "Darwin":
        return home / "Library/Application Support/Cursor/User/workspaceStorage"
    elif system == "Windows":
        return home / "AppData/Roaming/Cursor/User/workspaceStorage"
    else:
        return home / ".config/Cursor/User/workspaceStorage"


def validate_output_path(output_file: Optional[str]) -> None:
    """Validate that output path is not in Cursor data directories.

    Raises ValueError if output would write to data source.
    """
    if not output_file:
        return

    output_path = Path(output_file).resolve()
    home = Path.home()

    # Protected directories (Cursor data sources)
    protected_dirs = [
        home / "Library/Application Support/Cursor",
        home / "AppData/Roaming/Cursor",
        home / ".config/Cursor",
        home / ".cursor-server",
    ]

    for protected in protected_dirs:
        if protected.exists():
            try:
                output_path.relative_to(protected)
                raise ValueError(
                    f"Cannot write to Cursor data directory: {output_file}\n"
                    f"This would modify the data source. Choose a different output path."
                )
            except ValueError as e:
                if "Cannot write" in str(e):
                    raise
                # Not relative to this path, continue checking
                pass


def extract_absolute_path(value) -> Optional[str]:
    """Extract absolute path from various formats (string, dict, JSON string)."""
    if not value:
        return None

    # If it's already an absolute path string
    if isinstance(value, str):
        if value.startswith("/"):
            return value
        # Try to parse as JSON
        try:
            parsed = json.loads(value)
            return extract_absolute_path(parsed)
        except (json.JSONDecodeError, TypeError):
            return None

    # If it's a dict, look for path fields
    if isinstance(value, dict):
        # Try common path fields
        for key in ["absPath", "rootPath", "path", "fsPath", "filePath"]:
            path = value.get(key)
            if path:
                result = extract_absolute_path(path)
                if result:
                    return result
        # Check nested listDirV2Result
        list_dir = value.get("listDirV2Result", {})
        if list_dir:
            tree_root = list_dir.get("directoryTreeRoot", {})
            abs_path = tree_root.get("absPath")
            if abs_path and abs_path.startswith("/"):
                return abs_path

    return None


def load_context_map(cursor: sqlite3.Cursor) -> Dict[str, Dict]:
    """Load messageRequestContext data to extract project info."""
    context_map = {}
    cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'messageRequestContext:%'")

    for key, value in cursor.fetchall():
        if value is None:
            continue
        parts = key.split(":")
        if len(parts) >= 2:
            chat_id = parts[1]
            try:
                data = json.loads(value)
                # Extract project path from projectLayouts
                project_layouts = data.get("projectLayouts", [])
                for layout in project_layouts:
                    # Use extract_absolute_path to handle various formats
                    root_path = extract_absolute_path(layout)
                    if root_path:
                        if chat_id not in context_map:
                            context_map[chat_id] = {"projects": set()}
                        context_map[chat_id]["projects"].add(root_path)
            except (json.JSONDecodeError, TypeError):
                pass

    return context_map


def extract_project_from_paths(paths: List) -> Optional[str]:
    """Extract common project root from file paths."""
    if not paths:
        return None

    # Extract string paths from various formats (string, dict, etc.)
    string_paths = []
    for p in paths:
        if isinstance(p, str):
            string_paths.append(p)
        elif isinstance(p, dict):
            # Try common keys for file paths
            path = p.get("uri") or p.get("path") or p.get("fsPath") or p.get("filePath")
            if path and isinstance(path, str):
                # Handle file:// URIs
                if path.startswith("file://"):
                    path = path[7:]
                string_paths.append(path)

    # Filter valid absolute paths
    valid_paths = [p for p in string_paths if p and p.startswith("/")]
    if not valid_paths:
        return None

    # Find common prefix
    if len(valid_paths) == 1:
        # Return parent directory for single file
        parts = valid_paths[0].split("/")
        if len(parts) > 2:
            return "/".join(parts[:-1])
        return valid_paths[0]

    # Find common path prefix
    common = os.path.commonpath(valid_paths)
    return common if common and common != "/" else None


def detect_project_for_conversation(conv_data: Dict, bubble_map: Dict[str, Dict],
                                    context_map: Dict[str, Dict]) -> Optional[str]:
    """Detect project path for a conversation using multiple methods."""
    conv_id = conv_data.get("composerId", "")

    # Method 1: Check messageRequestContext for projectLayouts
    if conv_id in context_map:
        projects = context_map[conv_id].get("projects", set())
        if projects:
            return list(projects)[0]  # Return first project found

    # Method 2: Check newlyCreatedFiles in composerData
    new_files = conv_data.get("newlyCreatedFiles", [])
    if new_files:
        project = extract_project_from_paths(new_files)
        if project:
            return project

    # Method 3: Check codeBlockData for file paths
    code_block_data = conv_data.get("codeBlockData", {})
    if code_block_data:
        file_paths = []
        for block_id, block in code_block_data.items():
            if isinstance(block, dict):
                file_path = block.get("filePath") or block.get("uri")
                if file_path:
                    # Handle file:// URIs
                    if file_path.startswith("file://"):
                        file_path = file_path[7:]
                    file_paths.append(file_path)
        if file_paths:
            project = extract_project_from_paths(file_paths)
            if project:
                return project

    # Method 4: Check bubble relevantFiles
    headers = conv_data.get("fullConversationHeadersOnly", [])
    all_files = []
    for header in headers:
        bubble_id = header.get("bubbleId")
        bubble = bubble_map.get(bubble_id, {})

        # Check relevantFiles
        relevant = bubble.get("relevantFiles", [])
        if relevant:
            all_files.extend(relevant)

        # Check attachedFileCodeChunksUris
        attached = bubble.get("attachedFileCodeChunksUris", [])
        if attached:
            for uri in attached:
                # Handle both string and dict formats
                if isinstance(uri, str):
                    if uri.startswith("file://"):
                        all_files.append(uri[7:])
                    else:
                        all_files.append(uri)
                elif isinstance(uri, dict):
                    # Try to extract path from dict
                    path = uri.get("uri") or uri.get("path") or uri.get("fsPath")
                    if path and isinstance(path, str):
                        if path.startswith("file://"):
                            all_files.append(path[7:])
                        else:
                            all_files.append(path)

    if all_files:
        project = extract_project_from_paths(all_files)
        if project:
            return project

    return None


def format_timestamp(ts: Any) -> str:
    """Format timestamp (milliseconds) to readable format."""
    if ts is None:
        return "Unknown"
    try:
        # Cursor uses milliseconds
        dt = datetime.fromtimestamp(ts / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return str(ts) if ts else "Unknown"


def extract_from_rich_text(children: List[Dict]) -> str:
    """Recursively extract text from richText children."""
    text = ""
    for child in children:
        if child.get("type") == "text":
            text += child.get("text", "")
        elif child.get("type") == "code":
            text += "\n```\n"
            text += extract_from_rich_text(child.get("children", []))
            text += "\n```\n"
        elif "children" in child:
            text += extract_from_rich_text(child["children"])
    return text


def extract_text_from_bubble(bubble: Dict) -> str:
    """Extract text from a bubble object."""
    text = ""

    # Try plain text first
    if bubble.get("text", "").strip():
        text = bubble["text"]
    # Try richText as fallback
    elif bubble.get("richText"):
        try:
            rich = json.loads(bubble["richText"])
            text = extract_from_rich_text(rich.get("root", {}).get("children", []))
        except json.JSONDecodeError:
            pass

    # Append code blocks if present
    if bubble.get("codeBlocks"):
        for block in bubble["codeBlocks"]:
            if block.get("content"):
                lang = block.get("language", "")
                text += f"\n\n```{lang}\n{block['content']}\n```"

    return text


def load_bubble_map(cursor: sqlite3.Cursor) -> Dict[str, Dict]:
    """Load all bubbles into a dictionary."""
    bubble_map = {}
    cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")

    for key, value in cursor.fetchall():
        if value is None:
            continue
        parts = key.split(":")
        if len(parts) >= 3:
            bubble_id = parts[2]
            try:
                bubble_map[bubble_id] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass

    return bubble_map


def load_conversations(cursor: sqlite3.Cursor, bubble_map: Dict[str, Dict],
                       context_map: Dict[str, Dict]) -> List[Dict]:
    """Load all conversations with their messages and project info."""
    conversations = []

    cursor.execute("""
        SELECT key, value FROM cursorDiskKV
        WHERE key LIKE 'composerData:%'
        AND value LIKE '%fullConversationHeadersOnly%'
        AND value NOT LIKE '%fullConversationHeadersOnly\":[]%'
    """)

    for key, value in cursor.fetchall():
        if value is None:
            continue
        composer_id = key.split(":")[1]

        try:
            data = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            continue

        # Add composerId to data for project detection
        data["composerId"] = composer_id

        # Detect project for this conversation
        project = detect_project_for_conversation(data, bubble_map, context_map)

        # Build messages from headers
        messages = []
        for header in data.get("fullConversationHeadersOnly", []):
            bubble_id = header.get("bubbleId")
            bubble = bubble_map.get(bubble_id, {})

            msg_type = header.get("type")
            role = "user" if msg_type == 1 else "assistant"
            content = extract_text_from_bubble(bubble)
            timestamp = bubble.get("timestamp")

            if content.strip():
                messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": timestamp
                })

        if messages:
            conversations.append({
                "id": composer_id,
                "title": data.get("name") or "Untitled",
                "project": project,
                "created_at": data.get("createdAt"),
                "updated_at": data.get("lastUpdatedAt"),
                "message_count": len(messages),
                "messages": messages
            })

    return conversations


def load_all_data(session_id: Optional[str] = None,
                  role_filter: Optional[str] = None,
                  project_filter: Optional[str] = None) -> List[Dict]:
    """Load all conversation data from all Cursor databases."""
    db_paths = get_all_db_paths()

    if not db_paths:
        raise FileNotFoundError(f"No Cursor databases found. Expected at: {get_db_path()}")

    all_conversations = []
    seen_ids = set()  # Avoid duplicates across databases

    for db_path in db_paths:
        try:
            # Open database in read-only mode to prevent any modifications
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            try:
                bubble_map = load_bubble_map(cursor)
                context_map = load_context_map(cursor)
                conversations = load_conversations(cursor, bubble_map, context_map)

                # Add unique conversations
                for conv in conversations:
                    if conv["id"] not in seen_ids:
                        seen_ids.add(conv["id"])
                        all_conversations.append(conv)
            finally:
                conn.close()
        except sqlite3.Error as e:
            # Suppress "no such table" warnings - expected for some workspace DBs
            if "no such table" not in str(e):
                print(f"Warning: Could not read {db_path}: {e}", file=sys.stderr)
            continue

    conversations = all_conversations

    # Filter by session ID if specified
    if session_id:
        conversations = [c for c in conversations if c["id"].startswith(session_id)]

    # Filter by project if specified
    if project_filter:
        filtered = []
        for c in conversations:
            project = c.get("project", "")
            if project and project_filter.lower() in project.lower():
                filtered.append(c)
        conversations = filtered

    # Filter messages by role if specified
    if role_filter:
        for conv in conversations:
            conv["messages"] = [m for m in conv["messages"] if m["role"] == role_filter]
        # Remove empty conversations
        conversations = [c for c in conversations if c["messages"]]

    return conversations


def export_to_json(conversations: List[Dict], output_file: Optional[str],
                   pretty: bool = True) -> str:
    """Export to JSON format."""
    indent = 2 if pretty else None
    result = json.dumps({"conversations": conversations}, indent=indent, ensure_ascii=False)
    if output_file:
        with open(output_file, "w") as f:
            f.write(result)
    return result


def export_to_markdown(conversations: List[Dict], output_file: Optional[str], no_truncate: bool = False) -> str:
    """Export to Markdown format."""
    lines = ["# Cursor Chat History Export\n"]
    lines.append(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"Total Conversations: {len(conversations)}\n")
    lines.append("---\n")

    for conv in conversations:
        lines.append(f"\n## {conv.get('title', 'Untitled')}\n")
        lines.append(f"- **ID**: {conv.get('id', 'Unknown')[:8]}...")
        lines.append(f"- **Project**: {conv.get('project') or 'Unknown'}")
        lines.append(f"- **Created**: {format_timestamp(conv.get('created_at'))}")
        lines.append(f"- **Updated**: {format_timestamp(conv.get('updated_at'))}")
        lines.append(f"- **Messages**: {len(conv.get('messages', []))}\n")
        lines.append("### Conversation\n")

        for msg in conv.get("messages", []):
            role = msg.get("role", "unknown")
            timestamp = format_timestamp(msg.get("timestamp"))
            content = msg.get("content", "")

            if role == "user":
                lines.append(f"#### 👤 User ({timestamp})\n")
            else:
                lines.append(f"#### 🤖 Assistant ({timestamp})\n")

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


def export_to_csv(conversations: List[Dict], output_file: Optional[str], no_truncate: bool = False) -> str:
    """Export to CSV format."""
    rows = []
    headers = ["conversation_id", "title", "project", "timestamp", "role", "content"]

    for conv in conversations:
        conv_id = conv.get("id", "")
        title = conv.get("title", "")
        project = conv.get("project") or ""

        for msg in conv.get("messages", []):
            content = msg.get("content", "")
            # Truncate for CSV unless --no-truncate
            if not no_truncate and len(content) > 1000:
                content = content[:1000] + "..."
            rows.append({
                "conversation_id": conv_id[:8],
                "title": title[:50],
                "project": Path(project).name if project else "",
                "timestamp": format_timestamp(msg.get("timestamp")),
                "role": msg.get("role", "unknown"),
                "content": content.replace("\n", " ")
            })

    if output_file:
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    # Return as string
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_to_text(conversations: List[Dict], output_file: Optional[str], no_truncate: bool = False) -> str:
    """Export to plain text format."""
    lines = ["CURSOR CHAT HISTORY EXPORT", "=" * 50, ""]

    for conv in conversations:
        lines.append(f"CONVERSATION: {conv.get('title', 'Untitled')}")
        lines.append(f"ID: {conv.get('id', 'Unknown')[:8]}")
        lines.append(f"Project: {conv.get('project') or 'Unknown'}")
        lines.append(f"Created: {format_timestamp(conv.get('created_at'))}")
        lines.append("-" * 40)

        for msg in conv.get("messages", []):
            role = msg.get("role", "unknown").upper()
            timestamp = format_timestamp(msg.get("timestamp"))
            content = msg.get("content", "")

            # Truncate unless --no-truncate
            if not no_truncate and len(content) > 3000:
                content = content[:3000] + "\n... [truncated]"

            lines.append(f"\n[{role}] {timestamp}")
            lines.append(content)
            lines.append("")

        lines.append("=" * 50)
        lines.append("")

    result = "\n".join(lines)
    if output_file:
        with open(output_file, "w") as f:
            f.write(result)
    return result


def list_sessions(project_filter: Optional[str] = None) -> None:
    """List all conversations with project info."""
    try:
        conversations = load_all_data(project_filter=project_filter)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    if not conversations:
        print("No conversations found.")
        return

    print(f"\nFound {len(conversations)} conversations:\n")
    print(f"{'ID':<10} {'Msgs':<6} {'Created':<20} {'Project':<30} {'Title':<30}")
    print("-" * 100)

    for c in sorted(conversations, key=lambda x: x.get("created_at") or 0, reverse=True):
        cid = c.get("id", "")[:8]
        msg_count = len(c.get("messages", []))
        created = format_timestamp(c.get("created_at"))

        # Get project name (last component of path)
        project_path = c.get("project", "")
        if project_path:
            project_name = Path(project_path).name[:27]
            if len(Path(project_path).name) > 27:
                project_name += "..."
        else:
            project_name = "-"

        title = c.get("title", "Untitled")[:27]
        if len(c.get("title", "")) > 27:
            title += "..."
        print(f"{cid:<10} {msg_count:<6} {created:<20} {project_name:<30} {title:<30}")


def show_stats() -> None:
    """Show chat statistics with visualization."""
    try:
        conversations = load_all_data()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    stats = {
        "total_conversations": len(conversations),
        "total_messages": 0,
        "user_messages": 0,
        "assistant_messages": 0,
        "by_month": {},
    }

    for conv in conversations:
        for msg in conv.get("messages", []):
            stats["total_messages"] += 1
            role = msg.get("role", "")
            if role == "user":
                stats["user_messages"] += 1
            elif role == "assistant":
                stats["assistant_messages"] += 1

            # Track by month
            ts = msg.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromtimestamp(ts / 1000)
                    month = dt.strftime("%Y-%m")
                    stats["by_month"][month] = stats["by_month"].get(month, 0) + 1
                except (ValueError, TypeError, OSError):
                    pass

    _print_stats(stats)


def _print_stats(stats: Dict) -> None:
    """Print formatted statistics with ASCII visualization."""
    print("\n" + "=" * 60)
    print("CURSOR CHAT STATISTICS")
    print("=" * 60)

    # Summary
    print(f"\n{'SUMMARY':^60}")
    print("-" * 60)
    print(f"  Total Conversations: {stats['total_conversations']:>10}")
    print(f"  Total Messages:      {stats['total_messages']:>10}")
    print(f"  User Messages:       {stats['user_messages']:>10}")
    print(f"  Assistant Messages:  {stats['assistant_messages']:>10}")

    # By Month
    if stats["by_month"]:
        print(f"\n{'ACTIVITY BY MONTH':^60}")
        print("-" * 60)
        sorted_months = sorted(stats["by_month"].items())
        max_monthly = max(stats["by_month"].values()) or 1
        bar_width = 30

        for month, count in sorted_months:
            bar_len = int((count / max_monthly) * bar_width)
            bar = "#" * bar_len
            print(f"  {month}  [{bar:<{bar_width}}] {count:>5}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Export Cursor chat history to various formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -l                              # List all conversations
  %(prog)s -f markdown -o out.md           # Export to markdown
  %(prog)s -f json -o out.json             # Export to JSON
  %(prog)s -r user -o prompts.md           # User prompts only
  %(prog)s -s abc123                       # Specific conversation
  %(prog)s -p myproject                    # Filter by project name
  %(prog)s --stats                         # Show statistics
        """
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
        help="Export only a specific conversation (by ID prefix)"
    )
    parser.add_argument(
        "-l", "--list-sessions",
        action="store_true",
        help="List all conversations"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show chat statistics"
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
        "-p", "--project",
        help="Filter by project path or name (partial match supported)"
    )
    parser.add_argument(
        "--db-path",
        help="Custom database path (overrides auto-detection)"
    )
    parser.add_argument(
        "--list-dbs",
        action="store_true",
        help="List all found database files"
    )

    args = parser.parse_args()

    # List databases mode
    if args.list_dbs:
        db_paths = get_all_db_paths()
        if db_paths:
            print(f"\nFound {len(db_paths)} database(s):\n")
            for db in db_paths:
                size = db.stat().st_size / 1024 / 1024  # MB
                print(f"  {db} ({size:.2f} MB)")
        else:
            print("No databases found.")
        return

    # List sessions mode
    if args.list_sessions:
        list_sessions(args.project)
        return

    # Stats mode
    if args.stats:
        show_stats()
        return

    # Load data
    try:
        conversations = load_all_data(args.session, args.role, args.project)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"\nExpected database location: {get_db_path()}", file=sys.stderr)
        sys.exit(1)

    if not conversations:
        print("No conversations found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(conversations)} conversation(s)", file=sys.stderr)

    # Export based on format
    output_file = args.output

    # Validate output path is not in data source directories
    validate_output_path(output_file)

    result = ""

    if args.format == "json":
        result = export_to_json(conversations, output_file)
    elif args.format == "markdown":
        result = export_to_markdown(conversations, output_file, args.no_truncate)
    elif args.format == "csv":
        result = export_to_csv(conversations, output_file, args.no_truncate)
    elif args.format == "text":
        result = export_to_text(conversations, output_file, args.no_truncate)

    # Print to stdout if no output file specified
    if not output_file:
        print(result)
    else:
        print(f"Exported to: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
