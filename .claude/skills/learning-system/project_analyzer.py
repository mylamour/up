#!/usr/bin/env python3
"""
Project Analyzer - Automatically identifies improvement areas in the codebase.

Usage:
    python project_analyzer.py [--workspace /path/to/project]
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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

    # File extension to language mapping
    EXTENSIONS = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".jsx": "JavaScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
    }
    
    # Framework indicators
    FRAMEWORK_INDICATORS = {
        # Python
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "pytest": "pytest",
        "sqlalchemy": "SQLAlchemy",
        # JavaScript/TypeScript
        "react": "React",
        "next": "Next.js",
        "vue": "Vue.js",
        "express": "Express",
        "nestjs": "NestJS",
        # Others
        "spring": "Spring",
        "rails": "Rails",
    }
    
    # Pattern indicators (regex patterns)
    PATTERN_INDICATORS = {
        r"class.*Repository": "Repository Pattern",
        r"class.*Factory": "Factory Pattern",
        r"class.*Service": "Service Layer",
        r"@dataclass": "Dataclasses",
        r"class.*Protocol": "Protocol Pattern",
        r"async def": "Async/Await",
        r"useEffect|useState": "React Hooks",
        r"def test_": "Unit Tests",
    }

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()

    def analyze(self) -> ProjectProfile:
        """Analyze the project and return a profile."""
        profile = ProjectProfile(name=self.workspace.name)
        
        profile.languages = self._detect_languages()
        profile.frameworks = self._detect_frameworks()
        profile.patterns_detected = self._detect_patterns()
        profile.improvement_areas = self._identify_improvements(profile)
        profile.research_topics = self._generate_topics(profile)
        
        return profile

    def _detect_languages(self) -> list[str]:
        """Detect programming languages in the project."""
        found = set()
        skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist"}
        
        for root, dirs, files in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in self.EXTENSIONS:
                    found.add(self.EXTENSIONS[ext])
        
        return sorted(found)

    def _detect_frameworks(self) -> list[str]:
        """Detect frameworks and tools in use."""
        frameworks = []
        
        # Check common config files
        config_files = [
            self.workspace / "pyproject.toml",
            self.workspace / "requirements.txt",
            self.workspace / "package.json",
            self.workspace / "Cargo.toml",
            self.workspace / "go.mod",
        ]
        
        for config in config_files:
            if config.exists():
                try:
                    content = config.read_text().lower()
                    for key, name in self.FRAMEWORK_INDICATORS.items():
                        if key in content:
                            frameworks.append(name)
                except Exception:
                    pass
        
        return list(set(frameworks))

    def _detect_patterns(self) -> list[str]:
        """Detect code patterns in use."""
        patterns = set()
        skip_dirs = {".git", "node_modules", "__pycache__", ".venv"}
        
        src_dir = self.workspace / "src"
        if not src_dir.exists():
            src_dir = self.workspace
        
        code_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java"}
        
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for f in files:
                if Path(f).suffix.lower() not in code_extensions:
                    continue
                    
                filepath = Path(root) / f
                try:
                    content = filepath.read_text()
                    for pattern, name in self.PATTERN_INDICATORS.items():
                        if re.search(pattern, content, re.IGNORECASE):
                            patterns.add(name)
                except Exception:
                    continue
        
        return sorted(patterns)

    def _identify_improvements(self, profile: ProjectProfile) -> list[str]:
        """Identify areas that could be improved."""
        improvements = []
        
        # Check for missing patterns
        if "Python" in profile.languages:
            if "Unit Tests" not in profile.patterns_detected:
                improvements.append("add-unit-tests")
            if "Protocol Pattern" not in profile.patterns_detected:
                improvements.append("add-interfaces")
        
        if "TypeScript" in profile.languages:
            if "Unit Tests" not in profile.patterns_detected:
                improvements.append("add-unit-tests")
        
        # Check for optimization opportunities
        if any(f in profile.frameworks for f in ["FastAPI", "Django", "Flask"]):
            improvements.append("add-caching")
            improvements.append("optimize-queries")
        
        if "React" in profile.frameworks:
            improvements.append("optimize-renders")
        
        return list(set(improvements))

    def _generate_topics(self, profile: ProjectProfile) -> list[str]:
        """Generate research topics based on profile."""
        topics = []
        
        # Map improvements to research topics
        topic_map = {
            "add-unit-tests": "testing best practices",
            "add-interfaces": "Python Protocol and ABC patterns",
            "add-caching": "caching strategies",
            "optimize-queries": "database query optimization",
            "optimize-renders": "React performance optimization",
        }
        
        for improvement in profile.improvement_areas:
            if improvement in topic_map:
                topics.append(topic_map[improvement])
        
        # Add framework-specific topics
        for framework in profile.frameworks[:2]:  # Limit to 2
            topics.append(f"{framework} best practices")
        
        return topics[:5]  # Limit to 5 topics

    def save_profile(self, profile: ProjectProfile) -> Path:
        """Save profile to JSON file."""
        filepath = self.workspace / ".claude/skills/learning-system/project_profile.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
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


def main():
    import sys
    
    workspace = None
    if len(sys.argv) > 2 and sys.argv[1] == "--workspace":
        workspace = Path(sys.argv[2])
    
    analyzer = ProjectAnalyzer(workspace)
    profile = analyzer.analyze()
    
    print(f"Project: {profile.name}")
    print(f"Languages: {', '.join(profile.languages) or 'None detected'}")
    print(f"Frameworks: {', '.join(profile.frameworks) or 'None detected'}")
    print(f"Patterns: {', '.join(profile.patterns_detected) or 'None detected'}")
    print(f"Improvements: {', '.join(profile.improvement_areas) or 'None identified'}")
    print(f"Topics: {', '.join(profile.research_topics) or 'None generated'}")
    
    # Save profile
    path = analyzer.save_profile(profile)
    print(f"\nProfile saved to: {path}")


if __name__ == "__main__":
    main()
