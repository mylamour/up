"""Tests for context capture hook (US-002)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from up.plugins.builtin.provenance.hooks.context_capture import (
    _detect_context_files,
    _hash_prompt,
)


class TestContextCapture:
    def test_hash_prompt_deterministic(self):
        h1 = _hash_prompt("hello world")
        h2 = _hash_prompt("hello world")
        assert h1 == h2

    def test_hash_prompt_differs(self):
        h1 = _hash_prompt("prompt A")
        h2 = _hash_prompt("prompt B")
        assert h1 != h2

    def test_detect_files_in_prompt(self):
        prompt = "Please fix src/app.py and update tests/test_app.py"
        files = _detect_context_files(prompt)
        assert "src/app.py" in files
        assert "tests/test_app.py" in files

    def test_detect_no_files(self):
        files = _detect_context_files("Just a plain prompt with no files")
        assert len(files) == 0

    def test_caps_at_20_files(self):
        prompt = " ".join(f"src/file{i}.py" for i in range(30))
        files = _detect_context_files(prompt)
        assert len(files) <= 20
