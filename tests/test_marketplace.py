"""Tests for plugin marketplace registry (US-004)."""

from pathlib import Path
import json

import pytest

from up.plugins.marketplace import Marketplace, MarketplaceEntry


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


class TestMarketplaceEntry:
    def test_to_dict(self):
        e = MarketplaceEntry(name="test", description="A test")
        d = e.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "A test"

    def test_from_dict(self):
        e = MarketplaceEntry.from_dict({"name": "x", "version": "1.0.0"})
        assert e.name == "x"
        assert e.version == "1.0.0"

    def test_from_dict_ignores_extra(self):
        e = MarketplaceEntry.from_dict({"name": "x", "extra": "ignored"})
        assert e.name == "x"


class TestMarketplace:
    def test_empty_marketplace(self, workspace):
        mp = Marketplace(workspace)
        mp.load()
        assert mp.list_all() == []

    def test_add_and_get(self, workspace):
        mp = Marketplace(workspace)
        mp.load()
        mp.add(MarketplaceEntry(name="foo", description="A foo plugin"))
        assert mp.get("foo") is not None
        assert mp.get("foo").description == "A foo plugin"

    def test_remove(self, workspace):
        mp = Marketplace(workspace)
        mp.load()
        mp.add(MarketplaceEntry(name="bar"))
        assert mp.remove("bar") is True
        assert mp.get("bar") is None
        assert mp.remove("bar") is False

    def test_search_by_name(self, workspace):
        mp = Marketplace(workspace)
        mp.load()
        mp.add(MarketplaceEntry(name="code-review", description="Review code"))
        mp.add(MarketplaceEntry(name="security", description="Security checks"))
        results = mp.search("code")
        assert len(results) == 1
        assert results[0].name == "code-review"

    def test_search_by_description(self, workspace):
        mp = Marketplace(workspace)
        mp.load()
        mp.add(MarketplaceEntry(name="x", description="Lint your code"))
        results = mp.search("lint")
        assert len(results) == 1

    def test_search_by_category(self, workspace):
        mp = Marketplace(workspace)
        mp.load()
        mp.add(MarketplaceEntry(name="a", category="safety"))
        mp.add(MarketplaceEntry(name="b", category="productivity"))
        results = mp.search_by_category("safety")
        assert len(results) == 1
        assert results[0].name == "a"

    def test_save_and_reload(self, workspace):
        (workspace / ".up" / "plugins").mkdir(parents=True)
        mp = Marketplace(workspace)
        mp.load()
        mp.add(MarketplaceEntry(name="persist-test", version="2.0.0"))
        mp.save()

        mp2 = Marketplace(workspace)
        mp2.load()
        e = mp2.get("persist-test")
        assert e is not None
        assert e.version == "2.0.0"

    def test_scan_local_plugins(self, workspace):
        plugin_dir = workspace / "src" / "up" / "plugins" / "builtin" / "my-plug"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(json.dumps({
            "name": "my-plug", "version": "1.0.0",
            "description": "Test", "category": "safety",
        }))
        mp = Marketplace(workspace)
        mp.load()
        e = mp.get("my-plug")
        assert e is not None
        assert e.source == "builtin"
