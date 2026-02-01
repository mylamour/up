#!/usr/bin/env python3
"""
Learning System - Research Agent

Fetches and analyzes open source projects and blogs to extract
design patterns and best practices.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ResearchSource:
    """A source to research."""
    name: str
    url: str
    category: str
    topics: list[str] = field(default_factory=list)


@dataclass
class ResearchFinding:
    """A finding from research."""
    source: str
    title: str
    summary: str
    patterns: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    code_snippets: list[dict[str, str]] = field(default_factory=list)
    relevance: str = "medium"  # low, medium, high
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ResearchAgent:
    """Agent for researching open source projects and blogs."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()
        self.skill_dir = self.workspace / ".claude/skills/learning-system"
        self.research_dir = self.skill_dir / "research"
        self.insights_dir = self.skill_dir / "insights"

        # Create directories
        self.research_dir.mkdir(parents=True, exist_ok=True)
        self.insights_dir.mkdir(parents=True, exist_ok=True)

    def load_sources(self) -> dict[str, Any]:
        """Load research sources from config."""
        sources_file = self.skill_dir / "sources.json"
        if sources_file.exists():
            return json.loads(sources_file.read_text())
        return {"projects": [], "blogs": [], "research_topics": []}

    def save_finding(self, finding: ResearchFinding, topic: str) -> Path:
        """Save a research finding to markdown."""
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date}-{topic.lower().replace(' ', '-')}.md"
        filepath = self.research_dir / filename

        content = f"""# Research: {finding.title}

> Source: {finding.source}
> Date: {finding.timestamp}
> Relevance: {finding.relevance}

## Summary

{finding.summary}

## Key Patterns

"""
        for pattern in finding.patterns:
            content += f"- {pattern}\n"

        content += "\n## Insights\n\n"
        for insight in finding.insights:
            content += f"- {insight}\n"

        if finding.code_snippets:
            content += "\n## Code Examples\n\n"
            for snippet in finding.code_snippets:
                lang = snippet.get("language", "")
                code = snippet.get("code", "")
                desc = snippet.get("description", "")
                content += f"### {desc}\n\n```{lang}\n{code}\n```\n\n"

        filepath.write_text(content)
        return filepath

    def get_research_files(self) -> list[Path]:
        """Get all research files."""
        return sorted(self.research_dir.glob("*.md"))
