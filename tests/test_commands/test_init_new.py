"""Tests for up init and up new commands."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from up.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestInitCommand:
    """Tests for up init."""

    def test_init_creates_docs_structure(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--no-hooks", "--no-memory"])
            assert result.exit_code == 0
            assert Path("docs/CONTEXT.md").exists()
            assert Path("docs/INDEX.md").exists()
            assert Path("docs/handoff/LATEST.md").exists()
            assert Path("docs/roadmap/vision/PRODUCT_VISION.md").exists()

    def test_init_creates_claude_md(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--ai", "claude", "--no-hooks", "--no-memory"])
            assert result.exit_code == 0
            assert Path("CLAUDE.md").exists()
            assert Path(".claude/skills").exists()

    def test_init_creates_cursor_rules(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--ai", "cursor", "--no-hooks", "--no-memory"])
            assert result.exit_code == 0
            assert Path(".cursorrules").exists()
            assert Path(".cursor/rules/main.md").exists()
            assert Path(".cursor/rules/python.md").exists()

    def test_init_creates_up_state(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--no-hooks", "--no-memory"])
            assert result.exit_code == 0
            assert Path(".up/state.json").exists()
            state = json.loads(Path(".up/state.json").read_text())
            assert state["version"] == "2.0"

    def test_init_specific_systems(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                main, ["init", "-s", "docs", "--no-hooks", "--no-memory"]
            )
            assert result.exit_code == 0
            assert Path("docs/CONTEXT.md").exists()
            # learn/loop skills should NOT exist since only docs was requested
            assert not Path(".claude/skills/learning-system/SKILL.md").exists()


class TestNewCommand:
    """Tests for up new."""

    def test_new_creates_project_directory(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["new", "myproj"])
            assert result.exit_code == 0
            assert Path("myproj").is_dir()
            assert Path("myproj/docs/CONTEXT.md").exists()
            assert Path("myproj/CLAUDE.md").exists()

    def test_new_minimal_template(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["new", "minproj", "--template", "minimal"])
            assert result.exit_code == 0
            assert Path("minproj/docs/CONTEXT.md").exists()
            # minimal should not create learn/loop skills
            assert not Path("minproj/.claude/skills/product-loop/SKILL.md").exists()

    def test_new_fails_if_exists(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("existing").mkdir()
            result = runner.invoke(main, ["new", "existing"])
            assert result.exit_code != 0

    def test_list_templates(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["new", "x", "--list-templates"])
            assert result.exit_code == 0
            assert "minimal" in result.output
            assert "standard" in result.output
            assert "fastapi" in result.output
