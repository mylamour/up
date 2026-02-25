"""Tests for custom strategy loading via Markdown (US-007)."""

from pathlib import Path

import pytest

from up.parallel.explore import (
    ExploreStrategy,
    get_strategies,
    load_custom_strategies,
    _parse_strategy_file,
)


SAMPLE_STRATEGY_MD = """\
---
name: security-first
description: Prioritize security
constraints:
  - Validate all inputs
  - Use parameterized queries
---
You are solving with a SECURITY-FIRST approach.
Problem:
{problem}

Context:
{codebase_context}

{constraints}
"""


class TestParseStrategyFile:
    def test_parse_valid_strategy(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text(SAMPLE_STRATEGY_MD)
        s = _parse_strategy_file(f)
        assert s is not None
        assert s.name == "security-first"
        assert s.description == "Prioritize security"
        assert len(s.constraints) == 2
        assert "Validate all inputs" in s.constraints

    def test_parse_no_frontmatter(self, tmp_path):
        f = tmp_path / "bad.md"
        f.write_text("Just some text")
        assert _parse_strategy_file(f) is None

    def test_parse_no_name(self, tmp_path):
        f = tmp_path / "noname.md"
        f.write_text("---\ndescription: test\n---\nbody")
        assert _parse_strategy_file(f) is None

    def test_parse_missing_file(self, tmp_path):
        f = tmp_path / "missing.md"
        assert _parse_strategy_file(f) is None


class TestLoadCustomStrategies:
    def test_loads_from_plugin_dir(self, tmp_path):
        strat_dir = tmp_path / ".up" / "plugins" / "installed" / "my-plugin" / "strategies"
        strat_dir.mkdir(parents=True)
        (strat_dir / "sec.md").write_text(SAMPLE_STRATEGY_MD)

        result = load_custom_strategies(tmp_path)
        assert len(result) == 1
        assert result[0].name == "security-first"

    def test_empty_when_no_plugins(self, tmp_path):
        assert load_custom_strategies(tmp_path) == []


class TestGetStrategies:
    def test_defaults_when_no_custom(self, tmp_path):
        strats = get_strategies(tmp_path)
        assert len(strats) == 3
        names = [s.name for s in strats]
        assert "minimal" in names

    def test_filter_by_name(self, tmp_path):
        strats = get_strategies(tmp_path, names=["minimal", "clean"])
        assert len(strats) == 2

    def test_custom_overrides_default(self, tmp_path):
        # Create a custom "minimal" strategy
        strat_dir = tmp_path / ".up" / "plugins" / "installed" / "x" / "strategies"
        strat_dir.mkdir(parents=True)
        (strat_dir / "minimal.md").write_text(
            "---\nname: minimal\ndescription: Custom minimal\n---\nCustom {problem}\n{codebase_context}\n{constraints}"
        )

        strats = get_strategies(tmp_path)
        minimal = [s for s in strats if s.name == "minimal"][0]
        assert minimal.description == "Custom minimal"
