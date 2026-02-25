"""Tests for custom strategy loading via Markdown (US-007)."""

from pathlib import Path

import pytest

from up.parallel.explore import (
    ExploreStrategy,
    get_default_strategies,
    get_strategies,
    load_custom_strategies,
    _parse_strategy_file,
)


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


class TestParseStrategyFile:
    def test_valid_strategy(self, tmp_path):
        md = tmp_path / "strat.md"
        md.write_text(
            "---\n"
            "name: my-strat\n"
            "description: A custom one\n"
            "constraints:\n"
            "  - Do X\n"
            "  - Avoid Y\n"
            "---\n"
            "Solve {problem} with {codebase_context} and {constraints}\n"
        )
        s = _parse_strategy_file(md)
        assert s is not None
        assert s.name == "my-strat"
        assert s.description == "A custom one"
        assert len(s.constraints) == 2
        assert "{problem}" in s.prompt_template

    def test_missing_name_returns_none(self, tmp_path):
        md = tmp_path / "bad.md"
        md.write_text("---\ndescription: no name\n---\nbody\n")
        assert _parse_strategy_file(md) is None

    def test_no_frontmatter_returns_none(self, tmp_path):
        md = tmp_path / "plain.md"
        md.write_text("Just plain text")
        assert _parse_strategy_file(md) is None

    def test_missing_file_returns_none(self, tmp_path):
        assert _parse_strategy_file(tmp_path / "nope.md") is None


class TestLoadCustomStrategies:
    def test_no_plugins_dir(self, workspace):
        result = load_custom_strategies(workspace)
        assert result == []

    def test_loads_from_plugin_strategies_dir(self, workspace):
        strat_dir = workspace / ".up" / "plugins" / "installed" / "my-plugin" / "strategies"
        strat_dir.mkdir(parents=True)
        (strat_dir / "fast.md").write_text(
            "---\nname: fast\ndescription: Go fast\n---\n{problem}\n{codebase_context}\n{constraints}\n"
        )
        result = load_custom_strategies(workspace)
        assert len(result) == 1
        assert result[0].name == "fast"


class TestGetStrategies:
    def test_defaults_only(self, workspace):
        strats = get_strategies(workspace)
        names = [s.name for s in strats]
        assert "minimal" in names
        assert "clean" in names
        assert "pragmatic" in names

    def test_filter_by_name(self, workspace):
        strats = get_strategies(workspace, names=["minimal"])
        assert len(strats) == 1
        assert strats[0].name == "minimal"

    def test_custom_overrides_default(self, workspace):
        strat_dir = workspace / ".up" / "plugins" / "builtin" / "x" / "strategies"
        strat_dir.mkdir(parents=True)
        (strat_dir / "minimal.md").write_text(
            "---\nname: minimal\ndescription: Custom minimal\n---\n{problem}\n{codebase_context}\n{constraints}\n"
        )
        strats = get_strategies(workspace, names=["minimal"])
        assert len(strats) == 1
        assert strats[0].description == "Custom minimal"
