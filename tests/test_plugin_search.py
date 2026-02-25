"""Tests for plugin search command (US-005)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from up.commands.plugin import plugin_group


class TestPluginSearch:
    @patch("up.commands.plugin._get_registry")
    @patch("up.plugins.marketplace.Marketplace.load")
    @patch("up.plugins.marketplace.Marketplace.search")
    def test_search_no_results(self, mock_search, mock_load, mock_reg):
        mock_search.return_value = []
        mock_reg.return_value = MagicMock(get_all_entries=lambda: [])
        runner = CliRunner()
        result = runner.invoke(plugin_group, ["search", "nonexistent"])
        assert "No plugins matching" in result.output

    @patch("up.commands.plugin._get_registry")
    @patch("up.plugins.marketplace.Marketplace.load")
    @patch("up.plugins.marketplace.Marketplace.search")
    def test_search_with_results(self, mock_search, mock_load, mock_reg):
        from up.plugins.marketplace import MarketplaceEntry
        mock_search.return_value = [
            MarketplaceEntry(name="code-review", description="Review code", version="1.0.0"),
        ]
        mock_reg.return_value = MagicMock(get_all_entries=lambda: [])
        runner = CliRunner()
        result = runner.invoke(plugin_group, ["search", "code"])
        assert result.exit_code == 0
        assert "code-review" in result.output
