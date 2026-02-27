"""Error pattern extractor for memory auto-hooks.

Extracts searchable error signatures from task failures, verification
output, and exception traces. Used by auto-recall to find past solutions.
"""

import re

# ANSI escape code pattern
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Timestamp patterns (ISO, syslog, etc.)
_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*[Z]?"
    r"|\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}"
)

# File path with line number
_FILE_LINE_RE = re.compile(r'(?:File ")([^"]+)"(?:, line \d+)?')

# Python traceback exception line
_TRACEBACK_RE = re.compile(r"^(\w+(?:\.\w+)*(?:Error|Exception|Warning)): (.+)$", re.MULTILINE)

# Pytest failure: FAILED test_file.py::test_name
_PYTEST_FAIL_RE = re.compile(r"FAILED\s+([\w/._]+::[\w_]+)")

# Pytest assertion: AssertionError: assert ...
_ASSERT_RE = re.compile(r"(?:AssertionError|assert)\s*:?\s*(.+)", re.IGNORECASE)

# Lint error: file.py:10:5: E501 line too long
_LINT_RE = re.compile(r"[\w/._]+:\d+:\d+:\s+([A-Z]\d+)\s+(.+)")

# Generic error keyword line
_ERROR_LINE_RE = re.compile(r"^.*(?:error|Error|ERROR|failed|FAILED|FAILURE).*$", re.MULTILINE)


def _clean(text: str) -> str:
    """Strip ANSI codes, timestamps, and excess whitespace."""
    text = _ANSI_RE.sub("", text)
    text = _TIMESTAMP_RE.sub("", text)
    return text.strip()


class ErrorPatternExtractor:
    """Extracts searchable keywords from error output.

    Returns 1-3 keywords suitable for memory search queries.
    """

    def extract(self, error_output: str) -> list[str]:
        """Extract search keywords from error text.

        Tries extractors in priority order:
        1. Python tracebacks
        2. Pytest test failures
        3. Lint errors
        4. Generic error lines
        """
        if not error_output or not error_output.strip():
            return []

        cleaned = _clean(error_output)

        keywords = (
            self._from_traceback(cleaned)
            or self._from_pytest(cleaned)
            or self._from_lint(cleaned)
            or self._from_generic(cleaned)
        )

        return keywords[:3]

    def _from_traceback(self, text: str) -> list[str]:
        """Extract from Python tracebacks."""
        matches = _TRACEBACK_RE.findall(text)
        if not matches:
            return []
        exc_class, message = matches[-1]  # last exception is most relevant
        # Truncate long messages
        msg = message.strip()[:80]
        return [exc_class, msg]

    def _from_pytest(self, text: str) -> list[str]:
        """Extract from pytest failure output."""
        keywords = []
        # FAILED test path
        fail_match = _PYTEST_FAIL_RE.search(text)
        if fail_match:
            test_path = fail_match.group(1)
            # Extract just test name from path::test_name
            parts = test_path.split("::")
            keywords.append(parts[-1] if len(parts) > 1 else test_path)

        # Assertion message
        assert_match = _ASSERT_RE.search(text)
        if assert_match:
            keywords.append(assert_match.group(1).strip()[:80])

        return keywords if keywords else []

    def _from_lint(self, text: str) -> list[str]:
        """Extract from lint/type-check errors."""
        matches = _LINT_RE.findall(text)
        if not matches:
            return []
        # Take first unique rule codes + messages
        seen = set()
        keywords = []
        for code, msg in matches:
            if code not in seen:
                seen.add(code)
                keywords.append(f"{code} {msg.strip()}")
            if len(keywords) >= 3:
                break
        return keywords

    def _from_generic(self, text: str) -> list[str]:
        """Extract from generic error output."""
        matches = _ERROR_LINE_RE.findall(text)
        if not matches:
            # Fallback: first non-empty line
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and len(stripped) > 5:
                    return [stripped[:80]]
            return []
        # Take first meaningful error line
        line = matches[0].strip()[:80]
        return [line]
