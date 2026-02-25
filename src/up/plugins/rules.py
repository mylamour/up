"""Markdown rules engine.

Parses Markdown rule files (YAML frontmatter + body) and converts
them into hook-like event handlers. Rules are the simplest extension
point — no code required.

Rule file format:
    ---
    name: no-force-push
    event: pre_tool_use
    pattern: "git push.*--force"
    action: block
    confidence: 95
    ---
    Do not force push to protected branches.
    This can destroy commit history for other contributors.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from up.plugins.hooks import HookResult

logger = logging.getLogger(__name__)


@dataclass
class RuleSpec:
    """A parsed rule from a Markdown file."""
    name: str
    event: str  # e.g. "pre_tool_use", "post_execute"
    pattern: str  # regex to match against event data
    action: str  # "block", "warn", or "allow"
    confidence: int  # 0-100
    message: str  # from markdown body
    source_file: Optional[Path] = None


def parse_rule(path: Path) -> Optional[RuleSpec]:
    """Parse a Markdown rule file with YAML frontmatter.

    Expected format:
        ---
        name: rule-name
        event: pre_tool_use
        pattern: "regex"
        action: block|warn|allow
        confidence: 0-100
        ---
        Human-readable message body.
    """
    try:
        content = path.read_text()
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Could not read rule file %s: %s", path, e)
        return None

    # Split YAML frontmatter from body
    frontmatter, body = _split_frontmatter(content)
    if frontmatter is None:
        logger.warning("No YAML frontmatter in %s", path)
        return None

    meta = _parse_yaml_simple(frontmatter)
    if not meta.get("name"):
        logger.warning("Rule missing 'name' in %s", path)
        return None

    return RuleSpec(
        name=meta.get("name", path.stem),
        event=meta.get("event", "all"),
        pattern=meta.get("pattern", ".*"),
        action=meta.get("action", "warn"),
        confidence=int(meta.get("confidence", 50)),
        message=body.strip(),
        source_file=path,
    )


def _split_frontmatter(content: str) -> tuple[Optional[str], str]:
    """Split YAML frontmatter from markdown body.

    Returns (frontmatter_text, body_text). If no frontmatter found,
    returns (None, full_content).
    """
    if not content.startswith("---"):
        return None, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content

    return parts[1].strip(), parts[2].strip()


def _parse_yaml_simple(text: str) -> dict:
    """Parse simple YAML key-value pairs without requiring PyYAML.

    Handles: key: value (strings, ints, quoted strings).
    Does NOT handle nested structures, lists, etc.
    """
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def evaluate(rule: RuleSpec, event_data: dict) -> HookResult:
    """Evaluate a rule against event data.

    Applies the rule's regex pattern against string values in event_data.
    Returns a HookResult based on the rule's action.
    """
    # Check event type match
    event_type = event_data.get("event_type", "")
    if rule.event != "all" and rule.event != event_type:
        return HookResult(
            allowed=True,
            message=f"rule {rule.name}: skipped (event mismatch)",
            exit_code=0,
            hook_name=f"rule:{rule.name}",
        )

    # Apply pattern against event data values
    matched = False
    try:
        pattern = re.compile(rule.pattern)
        for value in event_data.values():
            if isinstance(value, str) and pattern.search(value):
                matched = True
                break
    except re.error:
        logger.warning("Invalid pattern in rule %s: %s", rule.name, rule.pattern)
        return HookResult(
            allowed=True, message=f"rule {rule.name}: invalid pattern",
            exit_code=0, hook_name=f"rule:{rule.name}",
        )

    if not matched:
        return HookResult(
            allowed=True,
            message=f"rule {rule.name}: no match",
            exit_code=0,
            hook_name=f"rule:{rule.name}",
        )

    # Pattern matched — apply action
    if rule.action == "block":
        return HookResult(
            allowed=False,
            message=rule.message or f"Blocked by rule: {rule.name}",
            exit_code=2,
            hook_name=f"rule:{rule.name}",
        )
    elif rule.action == "warn":
        return HookResult(
            allowed=True,
            message=rule.message or f"Warning from rule: {rule.name}",
            exit_code=1,
            hook_name=f"rule:{rule.name}",
        )
    else:  # "allow"
        return HookResult(
            allowed=True,
            message=rule.message or f"Allowed by rule: {rule.name}",
            exit_code=0,
            hook_name=f"rule:{rule.name}",
        )


class RulesEngine:
    """Loads and evaluates Markdown rules from plugin directories."""

    def __init__(self):
        self._rules: list[RuleSpec] = []

    @property
    def rules(self) -> list[RuleSpec]:
        return list(self._rules)

    def load_rules(self, plugin_path: Path) -> list[RuleSpec]:
        """Discover and parse all .md rule files in a plugin's rules/ dir."""
        rules_dir = plugin_path / "rules"
        if not rules_dir.is_dir():
            return []

        loaded = []
        for md_file in sorted(rules_dir.glob("*.md")):
            rule = parse_rule(md_file)
            if rule:
                loaded.append(rule)
                self._rules.append(rule)

        return loaded

    def evaluate_all(self, event_data: dict) -> list[HookResult]:
        """Evaluate all loaded rules against event data."""
        return [evaluate(rule, event_data) for rule in self._rules]

    def get_blocking_results(self, event_data: dict) -> list[HookResult]:
        """Return only results that block the operation."""
        return [r for r in self.evaluate_all(event_data) if not r.allowed]

    def clear(self) -> None:
        """Clear all loaded rules."""
        self._rules.clear()
