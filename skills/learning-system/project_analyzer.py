#!/usr/bin/env python3
"""
Project Analyzer - Automatically identifies improvement areas in the codebase.

Scans the current project to:
1. Detect technologies and patterns in use
2. Identify potential improvement areas
3. Generate research topics for the learning system
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectProfile:
    """Profile of the current project."""
    name: str
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    patterns_detected: list[str] = field(default_factory=list)
    improvement_areas: list[str] = field(default_factory=list)
    research_topics: list[str] = field(default_factory=list)


class ProjectAnalyzer:
    """Analyzes project to identify improvement opportunities."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or Path.cwd()

    def analyze(self) -> ProjectProfile:
        """Analyze the project and return a profile."""
        profile = ProjectProfile(name=self.workspace.name)

        # Detect languages
        profile.languages = self._detect_languages()

        # Detect frameworks
        profile.frameworks = self._detect_frameworks()

        # Detect patterns
        profile.patterns_detected = self._detect_patterns()

        # Identify improvement areas
        profile.improvement_areas = self._identify_improvements(profile)

        # Generate research topics
        profile.research_topics = self._generate_topics(profile)

        return profile

    def _detect_languages(self) -> list[str]:
        """Detect programming languages in the project."""
        extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".rb": "Ruby",
        }

        found = set()
        for root, dirs, files in os.walk(self.workspace):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in {
                ".git", "node_modules", "__pycache__", ".venv",
                "venv", "build", "dist", ".cache"
            }]

            for f in files:
                ext = Path(f).suffix.lower()
                if ext in extensions:
                    found.add(extensions[ext])

        return sorted(found)

    def _detect_frameworks(self) -> list[str]:
        """Detect frameworks and tools in use."""
        frameworks = []

        # Check for Python frameworks
        pyproject = self.workspace / "pyproject.toml"
        requirements = self.workspace / "requirements.txt"

        py_indicators = {
            "langgraph": "LangGraph",
            "langchain": "LangChain",
            "flask": "Flask",
            "django": "Django",
            "fastapi": "FastAPI",
            "tree-sitter": "Tree-sitter",
            "semgrep": "Semgrep",
            "qdrant": "Qdrant",
        }

        for f in [pyproject, requirements]:
            if f.exists():
                content = f.read_text().lower()
                for key, name in py_indicators.items():
                    if key in content:
                        frameworks.append(name)

        # Check for package.json
        pkg_json = self.workspace / "package.json"
        if pkg_json.exists():
            frameworks.append("Node.js")

        return list(set(frameworks))

    def _detect_patterns(self) -> list[str]:
        """Detect code patterns in use."""
        patterns = []

        # Pattern indicators to search for
        pattern_indicators = {
            r"class.*Coordinator": "Coordinator Pattern",
            r"class.*State\(TypedDict\)": "TypedDict State",
            r"def.*_node\(.*state": "LangGraph Nodes",
            r"taint|dataflow": "Taint Analysis",
            r"tree_sitter|TreeSitter": "AST Parsing",
            r"class.*Protocol": "Protocol Pattern",
            r"async def": "Async/Await",
            r"@dataclass": "Dataclasses",
        }

        src_dir = self.workspace / "src"
        if not src_dir.exists():
            src_dir = self.workspace

        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text()
                for pattern, name in pattern_indicators.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        patterns.append(name)
            except Exception:
                continue

        return list(set(patterns))

    def _identify_improvements(self, profile: ProjectProfile) -> list[str]:
        """Identify areas that could be improved."""
        improvements = []

        # Based on detected patterns, suggest improvements
        if "Taint Analysis" in profile.patterns_detected:
            improvements.append("taint-analysis-optimization")

        if "LangGraph Nodes" in profile.patterns_detected:
            improvements.append("workflow-optimization")

        if "AST Parsing" in profile.patterns_detected:
            improvements.append("parser-enhancement")

        # Check for missing best practices
        if "Python" in profile.languages:
            if "Protocol Pattern" not in profile.patterns_detected:
                improvements.append("interface-design")

        # Check code metrics
        improvements.extend(self._check_code_metrics())

        return list(set(improvements))

    def _check_code_metrics(self) -> list[str]:
        """Check code metrics for improvement areas."""
        improvements = []

        src_dir = self.workspace / "src"
        if not src_dir.exists():
            src_dir = self.workspace

        large_files = 0
        complex_functions = 0

        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text()
                lines = content.splitlines()

                # Check file size
                if len(lines) > 500:
                    large_files += 1

                # Check function complexity (simple heuristic)
                func_count = len(re.findall(r"^\s*def\s+", content, re.MULTILINE))
                if func_count > 20:
                    complex_functions += 1

            except Exception:
                continue

        if large_files > 3:
            improvements.append("code-modularization")

        if complex_functions > 2:
            improvements.append("function-decomposition")

        return improvements

    def _generate_topics(self, profile: ProjectProfile) -> list[str]:
        """Generate research topics based on profile."""
        topics = []

        # Map improvements to research topics
        topic_map = {
            "taint-analysis-optimization": "taint analysis best practices",
            "workflow-optimization": "LangGraph workflow patterns",
            "parser-enhancement": "tree-sitter advanced parsing",
            "interface-design": "Python Protocol patterns",
            "code-modularization": "code organization patterns",
            "function-decomposition": "function design patterns",
        }

        for improvement in profile.improvement_areas:
            if improvement in topic_map:
                topics.append(topic_map[improvement])

        # Add framework-specific topics
        for framework in profile.frameworks:
            topics.append(f"{framework} best practices")

        return topics[:5]  # Limit to top 5 topics

    def save_profile(self, profile: ProjectProfile) -> Path:
        """Save profile to JSON file."""
        skill_dir = self.workspace / ".claude/skills/learning-system"
        filepath = skill_dir / "project_profile.json"

        data = {
            "name": profile.name,
            "languages": profile.languages,
            "frameworks": profile.frameworks,
            "patterns_detected": profile.patterns_detected,
            "improvement_areas": profile.improvement_areas,
            "research_topics": profile.research_topics,
        }

        filepath.write_text(json.dumps(data, indent=2))
        return filepath


if __name__ == "__main__":
    analyzer = ProjectAnalyzer()
    profile = analyzer.analyze()

    print(f"Project: {profile.name}")
    print(f"Languages: {', '.join(profile.languages)}")
    print(f"Frameworks: {', '.join(profile.frameworks)}")
    print(f"Patterns: {', '.join(profile.patterns_detected)}")
    print(f"Improvements: {', '.join(profile.improvement_areas)}")
    print(f"Topics: {', '.join(profile.research_topics)}")
