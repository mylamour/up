"""Tests for hook pipeline runner (US-006)."""

import json
import os
import stat
import tempfile
from pathlib import Path

import pytest

from up.plugins.hooks import HookSpec, HookResult, HookRunner, load_hooks_from_json


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


@pytest.fixture
def runner(workspace):
    return HookRunner(workspace=workspace)


class TestHookSpec:
    def test_matches_no_matcher(self):
        spec = HookSpec(type="command", command="echo ok")
        assert spec.matches({"tool_name": "anything"}) is True

    def test_matches_tool_name(self):
        spec = HookSpec(type="command", command="echo ok", matcher="Edit|Write")
        assert spec.matches({"tool_name": "Edit"}) is True
        assert spec.matches({"tool_name": "Read"}) is False

    def test_matches_event_type(self):
        spec = HookSpec(type="command", command="echo ok", matcher="pre_tool")
        assert spec.matches({"event_type": "pre_tool_use"}) is True

    def test_matches_invalid_regex(self):
        spec = HookSpec(type="command", command="echo ok", matcher="[invalid")
        assert spec.matches({"tool_name": "test"}) is False


class TestHookRunner:
    def test_run_hook_allow(self, runner):
        spec = HookSpec(type="command", command="echo ok")
        result = runner.run_hook(spec, {"test": True})
        assert result.allowed is True
        assert result.exit_code == 0
        assert result.output == "ok"

    def test_run_hook_warn(self, runner):
        spec = HookSpec(type="command", command="echo 'warning msg' >&2; exit 1")
        result = runner.run_hook(spec, {})
        assert result.allowed is True
        assert result.exit_code == 1
        assert "warning msg" in result.message

    def test_run_hook_block(self, runner):
        spec = HookSpec(type="command", command="echo 'blocked!' >&2; exit 2")
        result = runner.run_hook(spec, {})
        assert result.allowed is False
        assert result.exit_code == 2
        assert "blocked!" in result.message

    def test_run_hook_receives_json_stdin(self, runner, workspace):
        script = workspace / "check_stdin.sh"
        script.write_text('#!/bin/bash\ncat\n')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

        spec = HookSpec(type="command", command=str(script))
        event_data = {"tool_name": "Edit", "file": "test.py"}
        result = runner.run_hook(spec, event_data)

        assert result.allowed is True
        parsed = json.loads(result.output)
        assert parsed["tool_name"] == "Edit"

    def test_run_hook_timeout(self, runner):
        spec = HookSpec(type="command", command="sleep 10", timeout=1)
        result = runner.run_hook(spec, {})
        assert result.allowed is True  # timeouts don't block
        assert "timeout" in result.message

    def test_run_hook_command_not_found(self, runner):
        spec = HookSpec(type="command", command="/nonexistent/command")
        result = runner.run_hook(spec, {})
        assert result.allowed is True  # errors don't block
        assert result.exit_code == -1

    def test_run_hook_skips_non_matching(self, runner):
        spec = HookSpec(type="command", command="exit 2", matcher="Write")
        result = runner.run_hook(spec, {"tool_name": "Read"})
        assert result.allowed is True
        assert "skipped" in result.message

    def test_run_hooks_multiple(self, runner):
        specs = [
            HookSpec(type="command", command="echo ok"),
            HookSpec(type="command", command="echo 'warn' >&2; exit 1"),
            HookSpec(type="command", command="echo ok2"),
        ]
        results = runner.run_hooks(specs, {})
        assert len(results) == 3
        assert all(r.allowed for r in results)

    def test_run_hooks_with_block(self, runner):
        specs = [
            HookSpec(type="command", command="echo ok"),
            HookSpec(type="command", command="exit 2"),
        ]
        results = runner.run_hooks(specs, {})
        assert runner.is_blocked(results) is True
        assert len(runner.get_block_messages(results)) == 1

    def test_python_hook_script(self, runner, workspace):
        script = workspace / "hook.py"
        script.write_text(
            'import sys, json\n'
            'data = json.load(sys.stdin)\n'
            'if data.get("dangerous"):\n'
            '    print("blocked: dangerous op", file=sys.stderr)\n'
            '    sys.exit(2)\n'
            'print("ok")\n'
        )

        spec = HookSpec(type="command", command=f"python3 {script}")

        # Safe operation
        result = runner.run_hook(spec, {"dangerous": False})
        assert result.allowed is True

        # Dangerous operation
        result = runner.run_hook(spec, {"dangerous": True})
        assert result.allowed is False
        assert result.exit_code == 2


class TestLoadHooksFromJson:
    def test_load_valid(self, tmp_path):
        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(json.dumps({
            "hooks": [
                {"type": "command", "command": "echo ok", "matcher": ".*"},
                {"type": "command", "command": "python3 check.py", "timeout": 30},
            ]
        }))
        specs = load_hooks_from_json(hooks_file)
        assert len(specs) == 2
        assert specs[0].matcher == ".*"
        assert specs[1].timeout == 30

    def test_load_missing_file(self, tmp_path):
        specs = load_hooks_from_json(tmp_path / "nope.json")
        assert specs == []

    def test_load_invalid_json(self, tmp_path):
        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text("not json")
        specs = load_hooks_from_json(hooks_file)
        assert specs == []
