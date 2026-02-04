"""Research and file learning for the learning system."""

import json
import re
from datetime import date
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from up.ai_cli import check_ai_cli, run_ai_prompt
from up.learn.utils import find_skill_dir, safe_filename, record_to_memory
from up.learn.analyzer import analyze_project, analyze_project_structure

console = Console()


def learn_from_topic(workspace: Path, topic: str, use_ai: bool = True) -> dict:
    """Learn in a specific direction provided by the user."""
    console.print(Panel.fit(
        f"[bold blue]Learning System[/] - Focused Learning: {topic}",
        border_style="blue"
    ))
    
    profile = analyze_project(workspace)
    
    learning = {
        "topic": topic,
        "project_context": {
            "languages": profile.get("languages", []),
            "frameworks": profile.get("frameworks", []),
        },
        "learning_areas": [],
        "action_items": [],
        "ai_research": None,
    }
    
    # Try AI-powered research
    if use_ai:
        cli_name, cli_available = check_ai_cli()
        if cli_available:
            console.print(f"\n[yellow]Researching with {cli_name}...[/]")
            ai_result = _ai_research_topic(workspace, topic, profile, cli_name)
            if ai_result:
                learning["ai_research"] = ai_result
    
    # Map topic to relevant areas (fallback)
    topic_lower = topic.lower()
    categories = {
        "testing": ["test", "testing", "unit test", "integration", "coverage", "pytest", "jest"],
        "architecture": ["architecture", "pattern", "design", "structure", "clean", "solid", "ddd"],
        "performance": ["performance", "speed", "fast", "optimize", "cache", "caching"],
        "security": ["security", "auth", "authentication", "authorization", "jwt", "oauth"],
        "api": ["api", "rest", "graphql", "endpoint", "route"],
        "database": ["database", "db", "sql", "orm", "migration", "query"],
    }
    
    matched_categories = []
    for cat, keywords in categories.items():
        if any(kw in topic_lower for kw in keywords):
            matched_categories.append(cat)
    
    if matched_categories:
        for cat in matched_categories:
            for fw in profile.get("frameworks", []):
                learning["learning_areas"].append(f"{fw} {cat} best practices")
        learning["learning_areas"].append(f"{topic} patterns")
    else:
        learning["learning_areas"].append(f"{topic} implementation")
        for fw in profile.get("frameworks", []):
            learning["learning_areas"].append(f"{topic} in {fw}")
    
    learning["action_items"] = [
        f"Research {topic} best practices",
        f"Review current codebase for {topic} patterns",
        f"Identify gaps in {topic} implementation",
        f"Create improvement plan for {topic}",
    ]
    
    # Display results
    if learning.get("ai_research"):
        console.print("\n[green]✓ AI Research Complete[/]")
        console.print(Panel(learning["ai_research"], title=f"Research: {topic}", border_style="green"))
    else:
        console.print("\n[bold]Learning Focus:[/]")
        console.print(f"  Topic: [cyan]{topic}[/]")
        console.print("\n[bold]Areas to Research:[/]")
        for area in learning["learning_areas"][:5]:
            console.print(f"  • {area}")
    
    # Save research file
    skill_dir = find_skill_dir(workspace, "learning-system")
    research_dir = skill_dir / "research"
    research_dir.mkdir(parents=True, exist_ok=True)
    
    safe_topic = safe_filename(topic)
    research_file = research_dir / f"{date.today().isoformat()}_{safe_topic}.md"
    
    ai_section = ""
    if learning.get("ai_research"):
        ai_section = f"## AI Research\n\n{learning['ai_research']}\n\n---\n\n"
    
    research_content = f"""# Learning: {topic}

**Created**: {date.today().isoformat()}
**Status**: {"✅ Researched" if learning.get("ai_research") else "📋 In Progress"}

## Context

Project languages: {', '.join(profile.get('languages', ['N/A']))}
Project frameworks: {', '.join(profile.get('frameworks', ['N/A']))}

{ai_section}## Learning Areas

{chr(10).join(f'- [ ] {area}' for area in learning['learning_areas'])}

## Action Items

{chr(10).join(f'- [ ] {item}' for item in learning['action_items'])}
"""
    
    research_file.write_text(research_content)
    console.print(f"\n[green]✓[/] Research file created: [cyan]{research_file}[/]")
    
    record_to_memory(workspace, f"Started learning about: {topic}")
    
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  1. Review [cyan]{research_file}[/]")
    console.print("  2. Run [cyan]up learn analyze[/] to process all research")
    console.print("  3. Run [cyan]up learn plan[/] to generate improvement PRD")
    
    return learning


def learn_from_file(workspace: Path, file_path: str, use_ai: bool = True) -> dict:
    """Learn from a single file."""
    source_file = Path(file_path).expanduser().resolve()
    
    if not source_file.exists():
        console.print(f"[red]Error: File not found: {file_path}[/]")
        return {}
    
    console.print(Panel.fit(
        f"[bold blue]Learning System[/] - Learn from File: {source_file.name}",
        border_style="blue"
    ))
    
    try:
        content = source_file.read_text()
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/]")
        return {}
    
    file_ext = source_file.suffix.lower()
    learnings = {
        "source_file": source_file.name,
        "source_path": str(source_file),
        "file_type": file_ext,
        "key_concepts": [],
        "patterns_found": [],
        "best_practices": [],
        "code_snippets": [],
        "ai_analysis": None,
    }
    
    # Try AI analysis
    if use_ai:
        cli_name, cli_available = check_ai_cli()
        if cli_available:
            console.print(f"\n[yellow]Analyzing with {cli_name}...[/]")
            ai_result = _ai_analyze_file(workspace, content, source_file.name, cli_name)
            if ai_result:
                learnings["ai_analysis"] = ai_result
    
    # Basic extraction by file type
    if file_ext in ['.md', '.markdown', '.txt', '.rst']:
        learnings = _analyze_documentation_file(content, learnings)
    elif file_ext in ['.py']:
        learnings = _analyze_python_file(content, learnings)
    elif file_ext in ['.js', '.ts', '.tsx', '.jsx']:
        learnings = _analyze_javascript_file(content, learnings)
    elif file_ext in ['.json', '.yaml', '.yml', '.toml']:
        learnings = _analyze_config_file(content, learnings, file_ext)
    else:
        learnings = _analyze_generic_file(content, learnings)
    
    # Display results
    console.print(f"\n[bold]File:[/] {source_file.name}")
    console.print(f"[bold]Type:[/] {file_ext or 'unknown'}")
    console.print(f"[bold]Size:[/] {len(content)} characters, {len(content.splitlines())} lines")
    
    if learnings.get("ai_analysis"):
        console.print("\n[green]✓ AI Analysis Complete[/]")
        console.print(Panel(learnings["ai_analysis"], title="AI Insights", border_style="green"))
    else:
        if learnings["key_concepts"]:
            console.print("\n[green]📚 Key Concepts:[/]")
            for c in learnings["key_concepts"][:10]:
                console.print(f"  • {c}")
    
    # Save learnings
    skill_dir = find_skill_dir(workspace, "learning-system")
    learnings_dir = skill_dir / "file_learnings"
    learnings_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = safe_filename(source_file.stem)
    summary_file = learnings_dir / f"{date.today().isoformat()}_{safe_name}.md"
    
    ai_section = ""
    if learnings.get("ai_analysis"):
        ai_section = f"## AI Analysis\n\n{learnings['ai_analysis']}\n\n---\n\n"
    
    summary_content = f"""# Learnings from: {source_file.name}

**Analyzed**: {date.today().isoformat()}
**Source**: `{source_file}`
**Type**: {file_ext or 'unknown'}

{ai_section}## Key Concepts

{chr(10).join(f'- {c}' for c in learnings['key_concepts']) or '- None extracted'}

## Patterns Found

{chr(10).join(f'- [ ] {p}' for p in learnings['patterns_found']) or '- None identified'}
"""
    summary_file.write_text(summary_content)
    
    console.print(f"\n[green]✓[/] Learnings saved to: [cyan]{summary_file}[/]")
    record_to_memory(workspace, f"Learned from file: {learnings['source_file']}")
    
    return learnings


def learn_from_project(workspace: Path, project_path: str, use_ai: bool = True) -> dict:
    """Analyze external project for good design patterns."""
    external_project = Path(project_path).expanduser().resolve()
    
    if not external_project.exists():
        console.print(f"[red]Error: Path not found: {project_path}[/]")
        return {}
    
    if external_project.is_file():
        return learn_from_file(workspace, project_path, use_ai=use_ai)
    
    console.print(Panel.fit(
        f"[bold blue]Learning System[/] - Learn from Project: {external_project.name}",
        border_style="blue"
    ))
    
    console.print("\n[bold]Analyzing External Project...[/]")
    external_profile = analyze_project(external_project)
    
    console.print("\n[bold]Analyzing Current Project...[/]")
    current_profile = analyze_project(workspace)
    
    learnings = {
        "source_project": external_project.name,
        "source_path": str(external_project),
        "patterns_to_adopt": [],
        "frameworks_to_consider": [],
        "structure_insights": [],
    }
    
    # Find patterns to adopt
    current_patterns = set(current_profile.get("patterns_detected", []))
    external_patterns = set(external_profile.get("patterns_detected", []))
    learnings["patterns_to_adopt"] = list(external_patterns - current_patterns)
    
    # Find frameworks to consider
    current_frameworks = set(current_profile.get("frameworks", []))
    external_frameworks = set(external_profile.get("frameworks", []))
    common_languages = set(current_profile.get("languages", [])) & set(external_profile.get("languages", []))
    if common_languages:
        learnings["frameworks_to_consider"] = list(external_frameworks - current_frameworks)
    
    learnings["structure_insights"] = analyze_project_structure(external_project)
    
    # Display comparison
    console.print("\n[bold]Comparison:[/]")
    table = Table()
    table.add_column("Aspect", style="cyan")
    table.add_column("Current Project")
    table.add_column("External Project")
    
    table.add_row(
        "Languages",
        ", ".join(current_profile.get("languages", [])) or "None",
        ", ".join(external_profile.get("languages", [])) or "None"
    )
    table.add_row(
        "Frameworks",
        ", ".join(current_profile.get("frameworks", [])) or "None",
        ", ".join(external_profile.get("frameworks", [])) or "None"
    )
    console.print(table)
    
    if learnings["patterns_to_adopt"]:
        console.print("\n[green]✓ Patterns to Consider Adopting:[/]")
        for p in learnings["patterns_to_adopt"]:
            console.print(f"  • {p}")
    
    # Save learnings
    skill_dir = find_skill_dir(workspace, "learning-system")
    learnings_dir = skill_dir / "external_learnings"
    learnings_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = safe_filename(external_project.name)
    summary_file = learnings_dir / f"{date.today().isoformat()}_{safe_name}.md"
    
    summary_content = f"""# Learnings from: {external_project.name}

**Analyzed**: {date.today().isoformat()}
**Source**: `{external_project}`

## Patterns to Adopt

{chr(10).join(f'- [ ] {p}' for p in learnings['patterns_to_adopt']) or '- None identified'}

## Structure Insights

{chr(10).join(f'- {s}' for s in learnings['structure_insights']) or '- None identified'}
"""
    summary_file.write_text(summary_content)
    
    console.print(f"\n[green]✓[/] Learnings saved to: [cyan]{summary_file}[/]")
    record_to_memory(workspace, f"Learned from external project: {learnings['source_project']}")
    
    return learnings


# =============================================================================
# AI Helper Functions
# =============================================================================

def _ai_research_topic(workspace: Path, topic: str, profile: dict, cli_name: str) -> Optional[str]:
    """Use AI to research a topic."""
    languages = ", ".join(profile.get("languages", [])) or "unknown"
    frameworks = ", ".join(profile.get("frameworks", [])) or "none"
    
    prompt = f"""Research the topic "{topic}" for a software project with:
- Languages: {languages}
- Frameworks: {frameworks}

Provide:
1. **Key Concepts** - Main ideas to understand (3-5 items)
2. **Best Practices** - Actionable recommendations (3-5 items)  
3. **Implementation Steps** - How to implement (3-5 steps)
4. **Common Pitfalls** - What to avoid (2-3 items)

Be concise and practical. Format with markdown."""

    return run_ai_prompt(workspace, prompt, cli_name, timeout=120)


def _ai_analyze_file(workspace: Path, content: str, filename: str, cli_name: str) -> Optional[str]:
    """Use AI to analyze a file."""
    max_chars = 12000
    if len(content) > max_chars:
        half = max_chars // 2
        content = content[:half] + "\n\n[... content truncated ...]\n\n" + content[-half:]
        truncated = True
    else:
        truncated = False
    
    prompt = f"""Analyze this file and extract actionable insights:

1. **Key Concepts** - Main ideas and knowledge (5-8 items)
2. **Patterns** - Design patterns, workflows, methodologies
3. **Best Practices** - Actionable recommendations
4. **Implementation Ideas** - How to use these learnings

{"[Note: File was truncated due to size]" if truncated else ""}

File ({filename}):
{content}

Be concise. Format with markdown headers."""

    return run_ai_prompt(workspace, prompt, cli_name, timeout=180)


# =============================================================================
# File Analyzers (Basic Extraction)
# =============================================================================

def _analyze_documentation_file(content: str, learnings: dict) -> dict:
    """Extract insights from markdown/documentation files."""
    lines = content.splitlines()
    
    # Extract headers
    headers = []
    for line in lines:
        if line.startswith('#'):
            header = line.lstrip('#').strip()
            if header and len(header) > 2:
                headers.append(header)
    learnings["key_concepts"] = headers[:15]
    
    # Look for patterns
    pattern_keywords = [
        ('pattern', 'Design pattern mentioned'),
        ('best practice', 'Best practice documented'),
        ('principle', 'Principle defined'),
        ('architecture', 'Architecture concept'),
        ('workflow', 'Workflow described'),
    ]
    
    content_lower = content.lower()
    for keyword, description in pattern_keywords:
        if keyword in content_lower:
            learnings["patterns_found"].append(description)
    
    return learnings


def _analyze_python_file(content: str, learnings: dict) -> dict:
    """Extract patterns from Python code."""
    lines = content.splitlines()
    
    patterns = {
        r'class.*Repository': 'Repository Pattern',
        r'class.*Service': 'Service Layer Pattern',
        r'class.*Factory': 'Factory Pattern',
        r'@dataclass': 'Dataclass usage',
        r'async def': 'Async/Await pattern',
        r'def test_': 'Unit test pattern',
        r'Protocol\)': 'Protocol (interface) pattern',
    }
    
    for pattern, name in patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            learnings["patterns_found"].append(name)
    
    # Extract class and function names
    for line in lines:
        if line.strip().startswith('class '):
            match = re.match(r'class\s+(\w+)', line.strip())
            if match:
                learnings["key_concepts"].append(f"Class: {match.group(1)}")
        elif line.strip().startswith('def '):
            match = re.match(r'def\s+(\w+)', line.strip())
            if match and not match.group(1).startswith('_'):
                learnings["key_concepts"].append(f"Function: {match.group(1)}")
    
    learnings["key_concepts"] = learnings["key_concepts"][:15]
    return learnings


def _analyze_javascript_file(content: str, learnings: dict) -> dict:
    """Extract patterns from JavaScript/TypeScript code."""
    patterns = {
        r'async\s+function': 'Async functions',
        r'await\s+': 'Await usage',
        r'export\s+default': 'Default exports',
        r'interface\s+': 'TypeScript interfaces',
        r'useState': 'React useState hook',
        r'useEffect': 'React useEffect hook',
    }
    
    for pattern, name in patterns.items():
        if re.search(pattern, content):
            learnings["patterns_found"].append(name)
    
    # Extract exports
    for line in content.splitlines():
        if 'export' in line:
            match = re.search(r'export\s+(?:default\s+)?(?:function|const|class)\s+(\w+)', line)
            if match:
                learnings["key_concepts"].append(f"Export: {match.group(1)}")
    
    learnings["key_concepts"] = learnings["key_concepts"][:15]
    return learnings


def _analyze_config_file(content: str, learnings: dict, file_ext: str) -> dict:
    """Extract insights from configuration files."""
    learnings["key_concepts"].append(f"Configuration file ({file_ext})")
    
    if file_ext == '.json':
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                learnings["key_concepts"].extend([f"Config key: {k}" for k in list(data.keys())[:10]])
        except json.JSONDecodeError:
            pass
    elif file_ext in ['.yaml', '.yml']:
        for line in content.splitlines():
            if ':' in line and not line.strip().startswith('#'):
                key = line.split(':')[0].strip()
                if key and not key.startswith('-'):
                    learnings["key_concepts"].append(f"Config: {key}")
                    if len(learnings["key_concepts"]) >= 15:
                        break
    
    return learnings


def _analyze_generic_file(content: str, learnings: dict) -> dict:
    """Generic file analysis."""
    lines = content.splitlines()
    
    for line in lines[:20]:
        line = line.strip()
        if line and len(line) > 10 and len(line) < 100:
            learnings["key_concepts"].append(line[:80])
    
    learnings["key_concepts"] = learnings["key_concepts"][:10]
    return learnings
