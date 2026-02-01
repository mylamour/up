#!/usr/bin/env python3
"""
Learning System - Planning Module

Generates improvement PRDs from gap analysis.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class UserStory:
    """A user story for the PRD."""
    id: str
    title: str
    description: str
    acceptanceCriteria: list[str]
    priority: int
    passes: bool = False
    notes: str = ""


class PlanningEngine:
    """Generates improvement plans from analysis."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()

    def generate_prd(
        self,
        project_name: str,
        stories: list[UserStory],
        branch_name: str | None = None,
    ) -> Path:
        """Generate PRD JSON file."""
        if not branch_name:
            date = datetime.now().strftime("%Y%m%d")
            branch_name = f"feature/learning-{date}"

        prd = {
            "project": project_name,
            "branchName": branch_name,
            "description": f"Improvements from learning system - {datetime.now().date()}",
            "userStories": [asdict(s) for s in stories],
        }

        filepath = self.workspace / "prd.json"
        filepath.write_text(json.dumps(prd, indent=2))
        return filepath

    def create_story(
        self,
        id: str,
        title: str,
        description: str,
        criteria: list[str],
        priority: int,
    ) -> UserStory:
        """Create a user story."""
        return UserStory(
            id=id,
            title=title,
            description=description,
            acceptanceCriteria=criteria,
            priority=priority,
        )
