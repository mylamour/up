"""Tests for provenance verify and export commands (US-003, US-004)."""

import json
from pathlib import Path
from click.testing import CliRunner

import pytest

from up.commands.provenance import provenance
from up.core.provenance import ProvenanceManager


@pytest.fixture
def prov_workspace(tmp_path):
    """Create workspace with provenance entries."""
    prov_dir = tmp_path / ".up" / "provenance"
    prov_dir.mkdir(parents=True)
    return tmp_path


def _create_chain(workspace, count=3):
    """Create a chain of provenance entries."""
    mgr = ProvenanceManager(workspace)
    entries = []
    for i in range(count):
        e = mgr.start_operation(
            task_id=f"US-{i+1:03d}",
            task_title=f"Task {i+1}",
            prompt=f"Implement task {i+1}",
            ai_model="claude",
        )
        mgr.complete_operation(
            entry_id=e.id,
            files_modified=[f"src/file{i}.py"],
            tests_passed=True,
            status="accepted",
        )
        entries.append(e)
    return entries


class TestVerifyCommand:
    def test_verify_empty(self, prov_workspace, monkeypatch):
        monkeypatch.chdir(prov_workspace)
        runner = CliRunner()
        result = runner.invoke(provenance, ["verify"])
        assert result.exit_code == 0
        assert "No provenance records" in result.output

    def test_verify_valid_chain(self, prov_workspace, monkeypatch):
        monkeypatch.chdir(prov_workspace)
        _create_chain(prov_workspace, 3)
        runner = CliRunner()
        result = runner.invoke(provenance, ["verify"])
        assert result.exit_code == 0
        assert "PASS" in result.output


class TestExportCommand:
    def test_export_empty(self, prov_workspace, monkeypatch):
        monkeypatch.chdir(prov_workspace)
        runner = CliRunner()
        result = runner.invoke(provenance, ["export"])
        assert "No provenance records" in result.output

    def test_export_json(self, prov_workspace, monkeypatch):
        monkeypatch.chdir(prov_workspace)
        _create_chain(prov_workspace, 2)
        runner = CliRunner()
        result = runner.invoke(provenance, ["export", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_export_csv(self, prov_workspace, monkeypatch):
        monkeypatch.chdir(prov_workspace)
        _create_chain(prov_workspace, 2)
        runner = CliRunner()
        result = runner.invoke(provenance, ["export", "--format", "csv"])
        assert result.exit_code == 0
        assert "id,task_id" in result.output

    def test_export_to_file(self, prov_workspace, monkeypatch):
        monkeypatch.chdir(prov_workspace)
        _create_chain(prov_workspace, 1)
        out_file = str(prov_workspace / "report.json")
        runner = CliRunner()
        result = runner.invoke(provenance, ["export", "-o", out_file])
        assert result.exit_code == 0
        assert Path(out_file).exists()
        data = json.loads(Path(out_file).read_text())
        assert len(data) == 1
