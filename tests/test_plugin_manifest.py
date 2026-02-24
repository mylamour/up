"""Tests for PluginManifest schema and validation."""

import json
import pytest
from pathlib import Path

from up.plugins.manifest import (
    PluginManifest,
    PluginCategory,
    ManifestValidationError,
    KEBAB_CASE_RE,
    SEMVER_RE,
)


# ── Regex helpers ──────────────────────────────────────────────


class TestKebabCaseRegex:
    @pytest.mark.parametrize("name", ["my-plugin", "a", "foo-bar-baz", "x1", "a-1b"])
    def test_valid_kebab(self, name):
        assert KEBAB_CASE_RE.match(name)

    @pytest.mark.parametrize("name", [
        "MyPlugin", "my_plugin", "-leading", "trailing-",
        "UPPER", "has space", "", "123start",
    ])
    def test_invalid_kebab(self, name):
        assert not KEBAB_CASE_RE.match(name)


class TestSemverRegex:
    @pytest.mark.parametrize("ver", ["0.1.0", "1.0.0", "12.34.56", "1.0.0-alpha.1"])
    def test_valid_semver(self, ver):
        assert SEMVER_RE.match(ver)

    @pytest.mark.parametrize("ver", ["1.0", "v1.0.0", "1", "1.0.0.0", ""])
    def test_invalid_semver(self, ver):
        assert not SEMVER_RE.match(ver)


# ── Dataclass construction ─────────────────────────────────────


class TestPluginManifestConstruction:
    def test_minimal(self):
        m = PluginManifest(name="my-plugin", version="0.1.0")
        assert m.name == "my-plugin"
        assert m.version == "0.1.0"
        assert m.engines == ["all"]
        assert m.category == PluginCategory.PRODUCTIVITY

    def test_full(self):
        m = PluginManifest(
            name="safety-check",
            version="1.2.3",
            description="A safety plugin",
            author="test",
            engines=["python", "node"],
            category=PluginCategory.SAFETY,
        )
        assert m.description == "A safety plugin"
        assert m.engines == ["python", "node"]
        assert m.category == PluginCategory.SAFETY


# ── Validation ─────────────────────────────────────────────────


class TestPluginManifestValidation:
    def test_valid_manifest(self):
        m = PluginManifest(name="my-plugin", version="1.0.0")
        assert m.validate() == []

    def test_invalid_name(self):
        m = PluginManifest(name="MyPlugin", version="1.0.0")
        errors = m.validate()
        assert len(errors) == 1
        assert "kebab-case" in errors[0]

    def test_invalid_version(self):
        m = PluginManifest(name="my-plugin", version="1.0")
        errors = m.validate()
        assert len(errors) == 1
        assert "semver" in errors[0]

    def test_empty_engines(self):
        m = PluginManifest(name="my-plugin", version="1.0.0", engines=[])
        errors = m.validate()
        assert len(errors) == 1
        assert "engines" in errors[0]

    def test_multiple_errors(self):
        m = PluginManifest(name="BAD", version="nope", engines=[])
        errors = m.validate()
        assert len(errors) == 3


# ── from_json ──────────────────────────────────────────────────


@pytest.fixture
def plugin_dir(tmp_path):
    """Create a temp directory with a valid plugin.json."""
    data = {
        "name": "test-plugin",
        "version": "0.1.0",
        "description": "A test plugin",
        "author": "tester",
        "category": "safety",
    }
    manifest_path = tmp_path / "plugin.json"
    manifest_path.write_text(json.dumps(data))
    return tmp_path


class TestFromJson:
    def test_valid_manifest(self, plugin_dir):
        m = PluginManifest.from_json(plugin_dir / "plugin.json")
        assert m.name == "test-plugin"
        assert m.version == "0.1.0"
        assert m.category == PluginCategory.SAFETY
        assert m.engines == ["all"]

    def test_missing_file(self, tmp_path):
        with pytest.raises(ManifestValidationError, match="not found"):
            PluginManifest.from_json(tmp_path / "nope.json")

    def test_invalid_json(self, tmp_path):
        bad = tmp_path / "plugin.json"
        bad.write_text("{not json")
        with pytest.raises(ManifestValidationError, match="Invalid JSON"):
            PluginManifest.from_json(bad)

    def test_missing_required_fields(self, tmp_path):
        p = tmp_path / "plugin.json"
        p.write_text(json.dumps({"description": "no name or version"}))
        with pytest.raises(ManifestValidationError, match="requires"):
            PluginManifest.from_json(p)

    def test_invalid_category(self, tmp_path):
        p = tmp_path / "plugin.json"
        p.write_text(json.dumps({
            "name": "my-plugin",
            "version": "1.0.0",
            "category": "bogus",
        }))
        with pytest.raises(ManifestValidationError, match="Invalid category"):
            PluginManifest.from_json(p)

    def test_invalid_name_via_from_json(self, tmp_path):
        p = tmp_path / "plugin.json"
        p.write_text(json.dumps({
            "name": "BadName",
            "version": "1.0.0",
        }))
        with pytest.raises(ManifestValidationError, match="kebab-case"):
            PluginManifest.from_json(p)

    def test_defaults_engines(self, plugin_dir):
        m = PluginManifest.from_json(plugin_dir / "plugin.json")
        assert m.engines == ["all"]

    def test_custom_engines(self, tmp_path):
        p = tmp_path / "plugin.json"
        p.write_text(json.dumps({
            "name": "my-plugin",
            "version": "1.0.0",
            "engines": ["python"],
        }))
        m = PluginManifest.from_json(p)
        assert m.engines == ["python"]
