"""Tests for Cursorrules renderer."""

from up.sync.cursorrules import CursorrulesRenderer, HEADER
from up.sync.renderer import TemplateContext, CommandInfo


class TestCursorrulesRenderer:
    def setup_method(self):
        self.renderer = CursorrulesRenderer()

    def test_filename(self):
        assert self.renderer.filename == ".cursorrules"

    def test_header_comment(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        assert output.startswith(HEADER)

    def test_project_overview(self):
        ctx = TemplateContext(project_name="my-app")
        output = self.renderer.render(ctx)
        assert "# my-app" in output

    def test_code_style_rules(self):
        ctx = TemplateContext(ai_rules=["Use type hints", "Follow PEP 8"])
        output = self.renderer.render(ctx)
        assert "# Code Style & Rules" in output
        assert "- Use type hints" in output
        assert "- Follow PEP 8" in output

    def test_no_code_style_when_empty(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        assert "# Code Style" not in output

    def test_command_reference(self):
        ctx = TemplateContext(commands=[
            CommandInfo(name="deploy", description="Deploy app", plugin="ops"),
        ])
        output = self.renderer.render(ctx)
        assert "# Available Commands" in output
        assert "`deploy`" in output

    def test_safety_rules(self):
        ctx = TemplateContext(safety_rules=["No secrets in code"])
        output = self.renderer.render(ctx)
        assert "# Safety Rules" in output
        assert "- No secrets in code" in output

    def test_no_safety_when_empty(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        assert "# Safety Rules" not in output
