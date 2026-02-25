"""Tests for error pattern extractor."""

from up.memory.patterns import ErrorPatternExtractor


class TestErrorPatternExtractor:
    def setup_method(self):
        self.extractor = ErrorPatternExtractor()

    def test_empty_input(self):
        assert self.extractor.extract("") == []
        assert self.extractor.extract("   ") == []
        assert self.extractor.extract(None) == []

    def test_python_traceback(self):
        error = """Traceback (most recent call last):
  File "src/app.py", line 42, in main
    result = process(data)
  File "src/core.py", line 10, in process
    return data["key"]
KeyError: 'key'"""
        keywords = self.extractor.extract(error)
        assert len(keywords) >= 1
        assert "KeyError" in keywords[0]

    def test_import_error(self):
        error = """Traceback (most recent call last):
  File "main.py", line 1, in <module>
    import nonexistent
ModuleNotFoundError: No module named 'nonexistent'"""
        keywords = self.extractor.extract(error)
        assert "ModuleNotFoundError" in keywords[0]
        assert any("nonexistent" in k for k in keywords)

    def test_pytest_failure(self):
        error = """FAILED tests/test_auth.py::test_login_invalid - AssertionError: assert 401 == 200"""
        keywords = self.extractor.extract(error)
        assert any("test_login_invalid" in k for k in keywords)

    def test_lint_error(self):
        error = """src/app.py:10:5: E501 line too long (120 > 88 characters)
src/app.py:15:1: F401 'os' imported but unused"""
        keywords = self.extractor.extract(error)
        assert len(keywords) >= 1
        assert any("E501" in k for k in keywords)

    def test_strips_ansi_codes(self):
        error = "\x1b[31mKeyError\x1b[0m: \x1b[33m'missing'\x1b[0m"
        keywords = self.extractor.extract(error)
        assert len(keywords) >= 1
        # Should not contain ANSI codes
        for k in keywords:
            assert "\x1b" not in k

    def test_generic_error(self):
        error = """Something went wrong
error: compilation failed with exit code 1"""
        keywords = self.extractor.extract(error)
        assert len(keywords) >= 1

    def test_max_three_keywords(self):
        error = """E501 line too long
E502 something
F401 unused import
W291 trailing whitespace
src/a.py:1:1: E501 x
src/b.py:2:1: F401 y
src/c.py:3:1: W291 z
src/d.py:4:1: E302 w"""
        keywords = self.extractor.extract(error)
        assert len(keywords) <= 3

    def test_strips_timestamps(self):
        error = "2026-02-25T10:30:00Z ERROR: connection refused"
        keywords = self.extractor.extract(error)
        for k in keywords:
            assert "2026" not in k
