#!/usr/bin/env python3
"""
Unit tests for export_cursor_history.py
"""

import json
import os
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from export_cursor_history import (
    format_timestamp,
    extract_from_rich_text,
    extract_text_from_bubble,
    extract_project_from_paths,
    get_db_path,
    get_workspace_path,
    export_to_json,
    export_to_markdown,
    export_to_csv,
    export_to_text,
)


class TestFormatTimestamp(unittest.TestCase):
    """Tests for format_timestamp function."""

    def test_valid_timestamp(self):
        """Test formatting a valid timestamp in milliseconds."""
        # 2024-01-15 10:30:00 UTC
        ts = 1705315800000
        result = format_timestamp(ts)
        # Check it contains expected date parts
        self.assertIn("2024", result)
        self.assertIn("01", result)
        self.assertIn("15", result)

    def test_none_timestamp(self):
        """Test handling None timestamp."""
        result = format_timestamp(None)
        self.assertEqual(result, "Unknown")

    def test_invalid_timestamp(self):
        """Test handling invalid timestamp."""
        result = format_timestamp("invalid")
        self.assertEqual(result, "invalid")

    def test_zero_timestamp(self):
        """Test handling zero timestamp."""
        result = format_timestamp(0)
        # Should return a valid date (epoch)
        self.assertIn("1970", result)


class TestExtractFromRichText(unittest.TestCase):
    """Tests for extract_from_rich_text function."""

    def test_simple_text(self):
        """Test extracting simple text."""
        children = [{"type": "text", "text": "Hello World"}]
        result = extract_from_rich_text(children)
        self.assertEqual(result, "Hello World")

    def test_multiple_text_nodes(self):
        """Test extracting multiple text nodes."""
        children = [
            {"type": "text", "text": "Hello "},
            {"type": "text", "text": "World"}
        ]
        result = extract_from_rich_text(children)
        self.assertEqual(result, "Hello World")

    def test_code_block(self):
        """Test extracting code block."""
        children = [
            {"type": "code", "children": [{"type": "text", "text": "print('hi')"}]}
        ]
        result = extract_from_rich_text(children)
        self.assertIn("```", result)
        self.assertIn("print('hi')", result)

    def test_nested_children(self):
        """Test extracting nested children."""
        children = [
            {
                "type": "paragraph",
                "children": [{"type": "text", "text": "Nested text"}]
            }
        ]
        result = extract_from_rich_text(children)
        self.assertEqual(result, "Nested text")

    def test_empty_children(self):
        """Test handling empty children list."""
        result = extract_from_rich_text([])
        self.assertEqual(result, "")


class TestExtractTextFromBubble(unittest.TestCase):
    """Tests for extract_text_from_bubble function."""

    def test_plain_text(self):
        """Test extracting plain text."""
        bubble = {"text": "Hello World"}
        result = extract_text_from_bubble(bubble)
        self.assertEqual(result, "Hello World")

    def test_empty_bubble(self):
        """Test handling empty bubble."""
        bubble = {}
        result = extract_text_from_bubble(bubble)
        self.assertEqual(result, "")

    def test_rich_text_fallback(self):
        """Test falling back to richText when text is empty."""
        rich_text = json.dumps({
            "root": {
                "children": [{"type": "text", "text": "Rich content"}]
            }
        })
        bubble = {"text": "", "richText": rich_text}
        result = extract_text_from_bubble(bubble)
        self.assertEqual(result, "Rich content")

    def test_code_blocks(self):
        """Test extracting code blocks."""
        bubble = {
            "text": "Some text",
            "codeBlocks": [
                {"content": "print('hello')", "language": "python"}
            ]
        }
        result = extract_text_from_bubble(bubble)
        self.assertIn("Some text", result)
        self.assertIn("```python", result)
        self.assertIn("print('hello')", result)


class TestExtractProjectFromPaths(unittest.TestCase):
    """Tests for extract_project_from_paths function."""

    def test_single_file_path(self):
        """Test extracting project from single file path."""
        paths = ["/Users/test/projects/myapp/src/main.py"]
        result = extract_project_from_paths(paths)
        self.assertEqual(result, "/Users/test/projects/myapp/src")

    def test_multiple_paths_common_prefix(self):
        """Test extracting common project from multiple paths."""
        paths = [
            "/Users/test/myproject/src/app.py",
            "/Users/test/myproject/src/utils.py",
            "/Users/test/myproject/tests/test_app.py"
        ]
        result = extract_project_from_paths(paths)
        self.assertEqual(result, "/Users/test/myproject")

    def test_empty_paths(self):
        """Test handling empty paths list."""
        result = extract_project_from_paths([])
        self.assertIsNone(result)

    def test_none_in_paths(self):
        """Test handling None values in paths."""
        paths = [None, "", "/Users/test/project/file.py"]
        result = extract_project_from_paths(paths)
        self.assertIsNotNone(result)

    def test_non_absolute_paths_filtered(self):
        """Test that non-absolute paths are filtered out."""
        paths = ["relative/path.py", "another/path.py"]
        result = extract_project_from_paths(paths)
        self.assertIsNone(result)


class TestExportToJson(unittest.TestCase):
    """Tests for export_to_json function."""

    def test_basic_export(self):
        """Test basic JSON export."""
        conversations = [
            {
                "id": "test123",
                "title": "Test Conv",
                "project": "/test/project",
                "created_at": 1705315800000,
                "messages": [{"role": "user", "content": "Hello"}]
            }
        ]
        result = export_to_json(conversations, None)
        data = json.loads(result)
        self.assertIn("conversations", data)
        self.assertEqual(len(data["conversations"]), 1)

    def test_empty_conversations(self):
        """Test exporting empty conversations."""
        result = export_to_json([], None)
        data = json.loads(result)
        self.assertEqual(data["conversations"], [])


class TestExportToMarkdown(unittest.TestCase):
    """Tests for export_to_markdown function."""

    def test_basic_export(self):
        """Test basic markdown export."""
        conversations = [
            {
                "id": "test123",
                "title": "Test Conv",
                "project": "/test/project",
                "created_at": 1705315800000,
                "updated_at": 1705315900000,
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": 1705315800000}
                ]
            }
        ]
        result = export_to_markdown(conversations, None)
        self.assertIn("# Cursor Chat History Export", result)
        self.assertIn("Test Conv", result)
        self.assertIn("User", result)

    def test_includes_project(self):
        """Test that project is included in output."""
        conversations = [
            {
                "id": "abc",
                "title": "Test",
                "project": "/my/project",
                "messages": []
            }
        ]
        result = export_to_markdown(conversations, None)
        self.assertIn("/my/project", result)


class TestExportToCsv(unittest.TestCase):
    """Tests for export_to_csv function."""

    def test_basic_export(self):
        """Test basic CSV export."""
        conversations = [
            {
                "id": "test123",
                "title": "Test Conv",
                "project": "/test/project",
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": 1705315800000}
                ]
            }
        ]
        result = export_to_csv(conversations, None)
        self.assertIn("conversation_id", result)
        self.assertIn("test123", result)
        self.assertIn("Hello", result)

    def test_includes_project_column(self):
        """Test that project column is included."""
        conversations = [
            {
                "id": "abc",
                "title": "Test",
                "project": "/my/project",
                "messages": [{"role": "user", "content": "Hi", "timestamp": None}]
            }
        ]
        result = export_to_csv(conversations, None)
        self.assertIn("project", result)


class TestExportToText(unittest.TestCase):
    """Tests for export_to_text function."""

    def test_basic_export(self):
        """Test basic text export."""
        conversations = [
            {
                "id": "test123",
                "title": "Test Conv",
                "project": "/test/project",
                "created_at": 1705315800000,
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": 1705315800000}
                ]
            }
        ]
        result = export_to_text(conversations, None)
        self.assertIn("CURSOR CHAT HISTORY EXPORT", result)
        self.assertIn("Test Conv", result)
        self.assertIn("USER", result)


class TestGetDbPath(unittest.TestCase):
    """Tests for get_db_path function."""

    @patch('platform.system')
    def test_macos_path(self, mock_system):
        """Test macOS database path."""
        mock_system.return_value = "Darwin"
        result = get_db_path()
        self.assertIn("Library/Application Support/Cursor", str(result))

    @patch('platform.system')
    def test_windows_path(self, mock_system):
        """Test Windows database path."""
        mock_system.return_value = "Windows"
        result = get_db_path()
        self.assertIn("AppData/Roaming/Cursor", str(result))

    @patch('platform.system')
    def test_linux_path(self, mock_system):
        """Test Linux database path."""
        mock_system.return_value = "Linux"
        result = get_db_path()
        self.assertIn(".config/Cursor", str(result))


if __name__ == "__main__":
    unittest.main()
