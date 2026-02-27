"""Plugin manifest schema and validation.

Defines the PluginManifest dataclass and validation logic for plugin.json files.
Plugins live in .up/plugins/ with auto-discovery by convention.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginCategory(str, Enum):
    """Plugin categories."""
    SAFETY = "safety"
    PRODUCTIVITY = "productivity"
    QUALITY = "quality"
    LEARNING = "learning"


# Kebab-case: lowercase letters, digits, hyphens, no leading/trailing hyphen
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

# Semver: major.minor.patch with optional pre-release
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")


class ManifestValidationError(Exception):
    """Raised when a plugin manifest fails validation."""


@dataclass
class PluginManifest:
    """Plugin manifest schema (plugin.json).

    Fields:
        name: Kebab-case plugin name (e.g. "my-plugin")
        version: Semver version string (e.g. "1.0.0")
        description: Human-readable description
        author: Plugin author
        engines: List of supported engines (defaults to ["all"])
        category: Plugin category enum
    """
    name: str
    version: str
    description: str = ""
    author: str = ""
    engines: list[str] = field(default_factory=lambda: ["all"])
    category: PluginCategory = PluginCategory.PRODUCTIVITY

    def validate(self) -> list[str]:
        """Validate manifest fields.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        if not KEBAB_CASE_RE.match(self.name):
            errors.append(
                f"name must be kebab-case (got '{self.name}')"
            )

        if not SEMVER_RE.match(self.version):
            errors.append(
                f"version must be semver (got '{self.version}')"
            )

        if not isinstance(self.engines, list) or not self.engines:
            errors.append("engines must be a non-empty list")

        return errors

    @classmethod
    def from_json(cls, path: Path) -> "PluginManifest":
        """Load and validate a PluginManifest from a plugin.json file.

        Args:
            path: Path to plugin.json

        Returns:
            Validated PluginManifest instance

        Raises:
            ManifestValidationError: If file is missing, invalid JSON,
                or fails validation.
        """
        if not path.exists():
            raise ManifestValidationError(f"Manifest not found: {path}")

        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise ManifestValidationError(
                f"Invalid JSON in {path}: {e}"
            )

        if not isinstance(data, dict):
            raise ManifestValidationError(
                f"Manifest must be a JSON object: {path}"
            )

        # Required fields
        name = data.get("name")
        version = data.get("version")
        if not name or not version:
            raise ManifestValidationError(
                "Manifest requires 'name' and 'version' fields"
            )

        # Parse category
        raw_category = data.get("category", "productivity")
        try:
            category = PluginCategory(raw_category)
        except ValueError:
            valid = ", ".join(c.value for c in PluginCategory)
            raise ManifestValidationError(
                f"Invalid category '{raw_category}'. "
                f"Must be one of: {valid}"
            )

        manifest = cls(
            name=name,
            version=version,
            description=data.get("description", ""),
            author=data.get("author", ""),
            engines=data.get("engines", ["all"]),
            category=category,
        )

        errors = manifest.validate()
        if errors:
            raise ManifestValidationError(
                f"Invalid manifest {path}: {'; '.join(errors)}"
            )

        return manifest
