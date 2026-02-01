#!/usr/bin/env python3
"""
Learning System - Analysis Module

Analyzes research findings and extracts patterns.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Pattern:
    """An extracted design pattern."""
    name: str
    source: str
    description: str
    implementation: str
    applicability: str
    priority: str = "medium"


@dataclass
class GapAnalysis:
    """A gap between current and best practice."""
    name: str
    current_state: str
    best_practice: str
    impact: str
    effort: str
    recommendation: str


class AnalysisEngine:
    """Analyzes research and extracts insights."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()
        self.skill_dir = self.workspace / ".claude/skills/learning-system"
        self.insights_dir = self.skill_dir / "insights"
        self.insights_dir.mkdir(parents=True, exist_ok=True)

    def save_patterns(self, patterns: list[Pattern]) -> Path:
        """Save extracted patterns to markdown."""
        filepath = self.insights_dir / "patterns.md"

        content = f"""# Extracted Design Patterns

> Generated: {datetime.now().isoformat()}
> Patterns: {len(patterns)}

"""
        for p in patterns:
            content += f"""## Pattern: {p.name}

- **Source**: {p.source}
- **Priority**: {p.priority}

### Description
{p.description}

### Implementation
{p.implementation}

### Applicability
{p.applicability}

---

"""
        filepath.write_text(content)
        return filepath

    def save_gap_analysis(self, gaps: list[GapAnalysis]) -> Path:
        """Save gap analysis to markdown."""
        filepath = self.insights_dir / "gap-analysis.md"

        content = f"""# Gap Analysis

> Generated: {datetime.now().isoformat()}
> Gaps Identified: {len(gaps)}

"""
        for g in gaps:
            content += f"""## Gap: {g.name}

| Aspect | Details |
|--------|---------|
| **Current State** | {g.current_state} |
| **Best Practice** | {g.best_practice} |
| **Impact** | {g.impact} |
| **Effort** | {g.effort} |

### Recommendation
{g.recommendation}

---

"""
        filepath.write_text(content)
        return filepath
