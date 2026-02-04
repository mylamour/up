"""Project analysis for the learning system."""

import os
import re
from pathlib import Path
from typing import Optional

from rich.console import Console

from up.learn.utils import find_skill_dir, display_profile, save_profile, load_profile, record_to_memory

console = Console()


def analyze_project(workspace: Path) -> dict:
    """Analyze project and return profile."""
    profile = {
        "name": workspace.name,
        "languages": [],
        "frameworks": [],
        "patterns_detected": [],
        "improvement_areas": [],
        "research_topics": [],
    }
    
    # Extension to language mapping
    extensions = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".rb": "Ruby",
    }
    
    # Framework indicators
    framework_indicators = {
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "react": "React",
        "next": "Next.js",
        "vue": "Vue.js",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "express": "Express",
        "pytest": "pytest",
    }
    
    # Detect languages
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist"}
    found_languages = set()
    
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in extensions:
                found_languages.add(extensions[ext])
    
    profile["languages"] = sorted(found_languages)
    
    # Detect frameworks
    config_files = [
        workspace / "pyproject.toml",
        workspace / "requirements.txt",
        workspace / "package.json",
    ]
    
    found_frameworks = set()
    for config in config_files:
        if config.exists():
            try:
                content = config.read_text().lower()
                for key, name in framework_indicators.items():
                    if key in content:
                        found_frameworks.add(name)
            except Exception:
                pass
    
    profile["frameworks"] = sorted(found_frameworks)
    
    # Detect patterns
    pattern_indicators = {
        r"class.*Repository": "Repository Pattern",
        r"class.*Service": "Service Layer",
        r"@dataclass": "Dataclasses",
        r"async def": "Async/Await",
        r"def test_": "Unit Tests",
        r"Protocol\)": "Protocol Pattern",
    }
    
    src_dir = workspace / "src"
    if not src_dir.exists():
        src_dir = workspace
    
    found_patterns = set()
    for py_file in src_dir.rglob("*.py"):
        try:
            content = py_file.read_text()
            for pattern, name in pattern_indicators.items():
                if re.search(pattern, content, re.IGNORECASE):
                    found_patterns.add(name)
        except Exception:
            continue
    
    profile["patterns_detected"] = sorted(found_patterns)
    
    # Identify improvements
    improvements = []
    if "Python" in profile["languages"]:
        if "Unit Tests" not in profile["patterns_detected"]:
            improvements.append("add-unit-tests")
        if "Protocol Pattern" not in profile["patterns_detected"]:
            improvements.append("add-interfaces")
    
    if any(f in profile["frameworks"] for f in ["FastAPI", "Django", "Flask"]):
        improvements.append("add-caching")
    
    profile["improvement_areas"] = improvements
    
    # Generate research topics
    topic_map = {
        "add-unit-tests": "testing best practices",
        "add-interfaces": "Python Protocol patterns",
        "add-caching": "caching strategies",
    }
    
    topics = [topic_map[i] for i in improvements if i in topic_map]
    for fw in profile["frameworks"][:2]:
        topics.append(f"{fw} best practices")
    
    profile["research_topics"] = topics[:5]
    
    return profile


def analyze_project_structure(project_path: Path) -> list:
    """Analyze project directory structure for insights."""
    insights = []
    
    good_patterns = {
        "src": "Source code organization in src/ directory",
        "tests": "Dedicated tests/ directory",
        "docs": "Documentation directory present",
        ".github": "GitHub workflows/CI present",
        "scripts": "Automation scripts directory",
        "__init__.py": "Proper Python package structure",
        "pyproject.toml": "Modern Python packaging (PEP 517)",
        "Makefile": "Make-based automation",
        "docker-compose": "Docker containerization",
    }
    
    for pattern, description in good_patterns.items():
        if (project_path / pattern).exists() or any(project_path.glob(f"**/{pattern}")):
            insights.append(description)
    
    return insights[:5]


def learn_self_improvement(workspace: Path, use_ai: bool = True) -> dict:
    """Analyze current project for self-improvement opportunities."""
    from rich.panel import Panel
    
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Self-Improvement Analysis",
        border_style="blue"
    ))
    
    profile = analyze_project(workspace)
    if not profile:
        return {}
    
    # Load existing profile to track improvements
    old_profile = load_profile(workspace)
    
    # Identify what changed
    improvements = {
        "new_patterns": [],
        "new_frameworks": [],
        "addressed_improvements": [],
        "remaining_improvements": [],
    }
    
    old_patterns = set(old_profile.get("patterns_detected", []))
    new_patterns = set(profile.get("patterns_detected", []))
    improvements["new_patterns"] = list(new_patterns - old_patterns)
    
    old_frameworks = set(old_profile.get("frameworks", []))
    new_frameworks = set(profile.get("frameworks", []))
    improvements["new_frameworks"] = list(new_frameworks - old_frameworks)
    
    old_areas = set(old_profile.get("improvement_areas", []))
    new_areas = set(profile.get("improvement_areas", []))
    improvements["addressed_improvements"] = list(old_areas - new_areas)
    improvements["remaining_improvements"] = list(new_areas)
    
    # Display results
    display_profile(profile)
    
    if improvements["new_patterns"]:
        console.print("\n[green]✓ New Patterns Adopted:[/]")
        for p in improvements["new_patterns"]:
            console.print(f"  • {p}")
    
    if improvements["addressed_improvements"]:
        console.print("\n[green]✓ Improvements Addressed:[/]")
        for a in improvements["addressed_improvements"]:
            console.print(f"  • {a}")
    
    if improvements["remaining_improvements"]:
        console.print("\n[yellow]○ Areas for Improvement:[/]")
        for r in improvements["remaining_improvements"]:
            console.print(f"  • {r}")
    
    # Save updated profile
    save_path = save_profile(workspace, profile)
    console.print(f"\n[green]✓[/] Profile updated: [cyan]{save_path}[/]")
    
    # Record to memory
    content = f"Self-improvement analysis: Found {len(profile.get('patterns_detected', []))} patterns, "
    content += f"{len(improvements.get('new_patterns', []))} new patterns adopted"
    record_to_memory(workspace, content)
    
    return improvements
