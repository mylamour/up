# Cursor Chat History Extraction Guide

A technical guide for extracting Cursor AI chat history using Python.

## 1. Database Location

Cursor stores chat history in SQLite databases:

| Platform | Path |
|----------|------|
| **macOS** | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |
| **Windows** | `%APPDATA%\Cursor\User\globalStorage\state.vscdb` |
| **Linux** | `~/.config/Cursor/User/globalStorage/state.vscdb` |
| **Linux (SSH)** | `~/.cursor-server/data/User/globalStorage/state.vscdb` |
| **WSL** | `/mnt/c/Users/<USERNAME>/AppData/Roaming/Cursor/User/globalStorage/state.vscdb` |

---

## 2. Database Schema

The database has one key table:

```sql
TABLE: cursorDiskKV
├── key   (TEXT)  -- Key identifier
└── value (TEXT)  -- JSON string
```

---

## 3. Key Patterns

Query these key patterns to extract data:

| Key Pattern | Description | Example Key |
|-------------|-------------|-------------|
| `composerData:<composerId>` | Conversation metadata | `composerData:abc123` |
| `bubbleId:<chatId>:<bubbleId>` | Individual message content | `bubbleId:abc123:msg001` |
| `codeBlockDiff:<chatId>:<diffId>` | Code changes/tool actions | `codeBlockDiff:abc123:diff001` |
| `messageRequestContext:<chatId>:<contextId>` | Context (files, git status) | `messageRequestContext:abc123:ctx001` |

---

## 4. Data Structures

### 4.1 composerData (Conversation Metadata)

```json
{
    "composerId": "abc123-def456",
    "name": "Fix login bug",
    "createdAt": 1704067200000,
    "lastUpdatedAt": 1704153600000,
    "fullConversationHeadersOnly": [
        {
            "bubbleId": "bubble-id-1",
            "type": 1
        },
        {
            "bubbleId": "bubble-id-2",
            "type": 2
        }
    ],
    "newlyCreatedFiles": [],
    "codeBlockData": {}
}
```

**Field descriptions:**
- `composerId`: Unique conversation identifier
- `name`: User-given title (optional, may be null)
- `createdAt`: Creation timestamp in milliseconds
- `lastUpdatedAt`: Last update timestamp in milliseconds
- `fullConversationHeadersOnly`: Array of message references
- `newlyCreatedFiles`: Files created during conversation
- `codeBlockData`: Code block references

### 4.2 bubbleId (Message Content)

```json
{
    "text": "How do I fix this error?",
    "richText": "{\"root\":{...}}",
    "timestamp": 1704067200000,
    "codeBlocks": [
        {
            "content": "def hello(): ...",
            "language": "python"
        }
    ],
    "relevantFiles": ["/path/to/file.py"],
    "context": {
        "fileSelections": []
    }
}
```

**Field descriptions:**
- `text`: Plain text content (primary)
- `richText`: JSON-encoded rich text (fallback)
- `timestamp`: Message timestamp in milliseconds
- `codeBlocks`: Array of code blocks in message
- `relevantFiles`: Referenced file paths
- `context`: Additional context data

### 4.3 Message Type Values

```
In fullConversationHeadersOnly[].type:
  1 = User message
  2 = AI message
```

---

## 5. Extraction Algorithm

```
Step 1: Open database
        └── sqlite3.connect(db_path)

Step 2: Load all bubbles into a map
        └── SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'
        └── Parse: key.split(':')[2] → bubbleId
        └── Store: bubble_map[bubbleId] = json.loads(value)

Step 3: Load all conversations
        └── SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'
        └── Filter: only rows where fullConversationHeadersOnly is not empty

Step 4: For each conversation:
        ├── Get composerId from key.split(':')[1]
        ├── Parse JSON value
        ├── Loop through fullConversationHeadersOnly:
        │   ├── Get bubbleId from header
        │   ├── Look up bubble_map[bubbleId]
        │   ├── Extract text (see Step 5)
        │   └── Determine type: header.type == 1 ? "user" : "ai"
        └── Build conversation object

Step 5: Extract text from bubble:
        ├── If bubble.text exists → use it
        ├── Else if bubble.richText exists:
        │   └── Parse JSON, recursively extract from root.children
        └── Append any codeBlocks content
```

---

## 6. Text Extraction from richText

The `richText` field is a nested JSON structure:

```json
{
    "root": {
        "children": [
            {"type": "text", "text": "Hello"},
            {"type": "code", "children": [{"type": "text", "text": "print()"}]},
            {"type": "paragraph", "children": [...]}
        ]
    }
}
```

Recursive extraction logic:
1. If node type is "text", return the text value
2. If node type is "code", wrap children in code block markers
3. If node has children, recursively process them
4. Concatenate all extracted text

---

## 7. Project Association

To associate conversations with projects, use the workspace storage:

```
Path: ~/Library/Application Support/Cursor/User/workspaceStorage/
      └── <workspace-id>/
          ├── workspace.json    # Contains project folder path
          └── state.vscdb       # Legacy per-workspace data
```

**workspace.json structure:**
```json
{
    "folder": "file:///Users/name/projects/my-project"
}
```

**Association methods (priority order):**
1. Check `messageRequestContext` for `projectLayouts` → contains `rootPath`
2. Check `composerData.newlyCreatedFiles` → file paths indicate project
3. Check `composerData.codeBlockData` → file paths indicate project
4. Check bubble `relevantFiles` or `attachedFileCodeChunksUris`

---

## 8. SQL Queries

### Get all conversations
```sql
SELECT key, value FROM cursorDiskKV
WHERE key LIKE 'composerData:%'
  AND value LIKE '%fullConversationHeadersOnly%'
  AND value NOT LIKE '%fullConversationHeadersOnly":[]%';
```

### Get all message contents
```sql
SELECT key, value FROM cursorDiskKV
WHERE key LIKE 'bubbleId:%';
```

### Get all code changes/tool actions
```sql
SELECT key, value FROM cursorDiskKV
WHERE key LIKE 'codeBlockDiff:%';
```

### Get all context data
```sql
SELECT key, value FROM cursorDiskKV
WHERE key LIKE 'messageRequestContext:%';
```

---

## 9. Python Implementation

```python
import sqlite3
import json
from pathlib import Path
import platform

def get_db_path():
    """Get Cursor database path based on platform."""
    home = Path.home()

    system = platform.system()
    if system == "Darwin":  # macOS
        return home / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
    elif system == "Windows":
        return home / "AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
    else:  # Linux
        return home / ".config/Cursor/User/globalStorage/state.vscdb"


def get_workspace_path():
    """Get Cursor workspace storage path."""
    home = Path.home()

    system = platform.system()
    if system == "Darwin":
        return home / "Library/Application Support/Cursor/User/workspaceStorage"
    elif system == "Windows":
        return home / "AppData/Roaming/Cursor/User/workspaceStorage"
    else:
        return home / ".config/Cursor/User/workspaceStorage"


def extract_from_rich_text(children):
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


def extract_text_from_bubble(bubble):
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


def load_bubble_map(cursor):
    """Load all bubbles into a dictionary."""
    bubble_map = {}
    cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")

    for key, value in cursor.fetchall():
        parts = key.split(":")
        if len(parts) >= 3:
            bubble_id = parts[2]
            try:
                bubble_map[bubble_id] = json.loads(value)
            except json.JSONDecodeError:
                pass

    return bubble_map


def load_conversations(cursor, bubble_map):
    """Load all conversations with their messages."""
    conversations = []

    cursor.execute("""
        SELECT key, value FROM cursorDiskKV
        WHERE key LIKE 'composerData:%'
        AND value LIKE '%fullConversationHeadersOnly%'
        AND value NOT LIKE '%fullConversationHeadersOnly":[]%'
    """)

    for key, value in cursor.fetchall():
        composer_id = key.split(":")[1]

        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            continue

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
                "created_at": data.get("createdAt"),
                "updated_at": data.get("lastUpdatedAt"),
                "messages": messages
            })

    return conversations


def extract_all_conversations():
    """Main extraction function."""
    db_path = get_db_path()

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        bubble_map = load_bubble_map(cursor)
        conversations = load_conversations(cursor, bubble_map)
    finally:
        conn.close()

    return conversations


if __name__ == "__main__":
    conversations = extract_all_conversations()

    # Output as JSON
    output = {"conversations": conversations}
    print(json.dumps(output, indent=2, ensure_ascii=False))
```

---

## 10. Output Format

```json
{
    "conversations": [
        {
            "id": "abc123-def456",
            "title": "Fix login bug",
            "created_at": 1704067200000,
            "updated_at": 1704153600000,
            "messages": [
                {
                    "role": "user",
                    "content": "How do I fix this error?",
                    "timestamp": 1704067200000
                },
                {
                    "role": "assistant",
                    "content": "You can fix it by...",
                    "timestamp": 1704067201000
                }
            ]
        }
    ]
}
```

---

## 11. Usage

```bash
# Run the script
python cursor_history_extractor.py > conversations.json

# Or import as module
python -c "from cursor_history_extractor import extract_all_conversations; print(len(extract_all_conversations()))"
```

---

## 12. Notes

- Timestamps are in **milliseconds** (Unix epoch)
- The database should be opened in **read-only mode** to avoid corruption
- Close Cursor before reading if you encounter lock issues
- Empty conversations (no messages) are filtered out
- Message type `1` = user, type `2` = AI assistant
