"""Tests for CLAUDE.md renderer."""

from up.sync.claude_md import ClaudeMdRenderer, HEADER
from up.sync.renderer import TemplateContext, CommandInfo, HookSummary


class TestClaudeMdRenderer:
    def setup_method(self):
        self.renderer = ClaudeMdRenderer()

    def test_filename(self):
        assert self.renderer.filename == "CLAUDE.md"

    def test_header_comment(self):
        ctx = TemplateContext(project_name="test")
        output = self.renderer.render(ctx)
        assert output.startswith(HEADER)

    def test_project_name(self):
        ctx = TemplateContext(project_name="my-app")
        output = self.renderer.render(ctx)
        assert "# my-app" in output

    def test_default_project_name(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        assert "# Project" in output

    def test_quick_start_section(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        assert "## Quick Start" in output

    def test_commands_table(self):
        ctx = TemplateContext(commands=[
            CommandInfo(name="deploy", description="Deploy app", plugin="ops"),
            CommandInfo(name="lint", description="Run linter", plugin="quality"),
        ])
        output = self.renderer.render(ctx)
        assert "## Commands" in output
        assert "| `deploy` | Deploy app | ops |" in output
        assert "| `lint` | Run linter | quality |" in output

    def test_no_commands_section_when_empty(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        assert "## Commands" not in output

    def test_safety_rules(self):
        ctx = TemplateContext(safety_rules=["Never commit secrets", "Validate inputs"])
        output = self.renderer.render(ctx)
        assert "## Safety Rules" in output
        assert "- Never commit secrets" in output
        assert "- Validate inputs" in output

    def test_no_safety_section_when_empty(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        assert "## Safety Rules" not in output

    def test_memory_protocol_enabled(self):
        ctx = TemplateContext(memory_protocol=True)
        output = self.renderer.render(ctx)
        assert "## Memory Protocol" in output
        assert "Auto-index commits" in output

    def test_memory_protocol_disabled(self):
        ctx = TemplateContext(memory_protocol=False)
        output = self.renderer.render(ctx)
        assert "## Memory Protocol" not in output

    def test_hooks_summary(self):
        ctx = TemplateContext(hooks_summary=[
            HookSummary(event="pre_execute", plugin="safety", action="python check.py"),
        ])
        output = self.renderer.render(ctx)
        assert "## Active Hooks" in output
        assert "pre_execute" in output

    def test_auto_triggers(self):
        ctx = TemplateContext()
        output = self.renderer.render(ctx)
        assert "## Auto-Triggers" in output

    def test_ai_rules(self):
        ctx = TemplateContext(ai_rules=["Always lint before commit"])
        output = self.renderer.render(ctx)
        assert "## AI Rules" in output
        assert "- Always lint before commit" in output
