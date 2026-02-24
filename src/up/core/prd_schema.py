"""Shared PRD schema for learn (writer) and start (reader)."""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class UserStory:
    id: str
    title: str
    description: str = ""
    priority: str = "medium"
    effort: str = "medium"
    phase: str = ""
    passes: bool = False
    completedAt: Optional[str] = None
    acceptanceCriteria: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class PRD:
    userStories: list[UserStory] = field(default_factory=list)
    name: str = ""
    version: str = "1.0.0"
    generated: str = ""
    source: str = ""
    metadata: dict = field(default_factory=dict)

    def pending_tasks(self) -> list[UserStory]:
        return [s for s in self.userStories if not s.passes]

    def next_task(self, completed_ids: set[str] | None = None) -> Optional[UserStory]:
        completed_ids = completed_ids or set()
        for story in self.userStories:
            if story.passes or story.id in completed_ids:
                continue
            return story
        return None

    def mark_complete(self, task_id: str, date: str = "") -> bool:
        for story in self.userStories:
            if story.id == task_id:
                story.passes = True
                if date:
                    story.completedAt = date
                return True
        return False


class PRDValidationError(Exception):
    pass


def load_prd(path: Path) -> PRD:
    """Load and validate a PRD from JSON file."""
    if not path.exists():
        raise PRDValidationError(f"PRD not found: {path}")

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise PRDValidationError(f"Invalid JSON in {path}: {e}")

    stories = []
    for raw in data.get("userStories", []):
        if not isinstance(raw, dict) or "id" not in raw or "title" not in raw:
            logger.warning("Skipping invalid story: %s", raw)
            continue
        stories.append(UserStory(
            id=raw["id"],
            title=raw["title"],
            description=raw.get("description", ""),
            priority=raw.get("priority", "medium"),
            effort=raw.get("effort", "medium"),
            phase=raw.get("phase", ""),
            passes=raw.get("passes", False),
            completedAt=raw.get("completedAt"),
            acceptanceCriteria=raw.get("acceptanceCriteria", []),
            depends_on=raw.get("depends_on", []),
        ))

    return PRD(
        userStories=stories,
        name=data.get("name", ""),
        version=data.get("version", "1.0.0"),
        generated=data.get("generated", ""),
        source=data.get("source", ""),
        metadata=data.get("metadata", {}),
    )


def save_prd(prd: PRD, path: Path) -> None:
    """Save PRD to JSON file."""
    data = {
        "name": prd.name,
        "version": prd.version,
        "generated": prd.generated,
        "source": prd.source,
        "userStories": [asdict(s) for s in prd.userStories],
        "metadata": prd.metadata,
    }
    path.write_text(json.dumps(data, indent=2))
