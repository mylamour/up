"""Tests for ExploreStrategy dataclass and default strategies (US-001)."""

from pathlib import Path

from up.parallel.explore import (
    ExploreStrategy,
    get_default_strategies,
)


class TestExploreStrategy:
    def test_dataclass_fields(self):
        s = ExploreStrategy(
            name="test",
            description="A test strategy",
            prompt_template="Do {problem}",
        )
        assert s.name == "test"
        assert s.description == "A test strategy"
        assert s.constraints == []

    def test_dataclass_with_constraints(self):
        s = ExploreStrategy(
            name="x",
            description="",
            prompt_template="",
            constraints=["a", "b"],
        )
        assert s.constraints == ["a", "b"]

    def test_default_strategies_count(self):
        defaults = get_default_strategies()
        assert len(defaults) == 3

    def test_default_strategy_names(self):
        names = [s.name for s in get_default_strategies()]
        assert names == ["minimal", "clean", "pragmatic"]

    def test_default_strategies_have_placeholders(self):
        for s in get_default_strategies():
            assert "{problem}" in s.prompt_template
            assert "{codebase_context}" in s.prompt_template
            assert "{constraints}" in s.prompt_template

    def test_default_strategies_have_constraints(self):
        for s in get_default_strategies():
            assert len(s.constraints) > 0

    def test_default_strategies_have_descriptions(self):
        for s in get_default_strategies():
            assert s.description
