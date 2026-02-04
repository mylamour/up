"""up learn - Learning system CLI commands."""

import json
import os
import re
import sys
from pathlib import Path
from datetime import date

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def check_vision_map_exists(workspace: Path) -> tuple[bool, Path]:
    """Check if vision map is set up (not just template).
    
    Returns:
        (exists_and_configured, vision_path)
    """
    vision_path = workspace / "docs/roadmap/vision/PRODUCT_VISION.md"
    
    if not vision_path.exists():
        return False, vision_path
    
    # Check if it's still just the template (not configured)
    content = vision_path.read_text()
    template_indicators = [
        "One-line vision statement here",
        "Problem 1 | Description",
        "Metric 1 | Value",
    ]
    
    # If any template placeholder still exists, it's not properly configured
    for indicator in template_indicators:
        if indicator in content:
            return False, vision_path
    
    return True, vision_path


def is_valid_path(s: str) -> bool:
    """Check if string looks like a path."""
    # Check if it's an existing path
    if Path(s).exists():
        return True
    
    # Check if it looks like a path pattern
    path_indicators = ['/', '\\', './', '../', '~/', ':', 'C:\\']
    return any(s.startswith(ind) or ind in s for ind in path_indicators)


def learn_self_improvement(workspace: Path) -> dict:
    """Analyze current project for self-improvement opportunities.
    
    This is called when `up learn` is used without arguments.
    """
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Self-Improvement Analysis",
        border_style="blue"
    ))
    
    # First, analyze current state
    profile = analyze_project(workspace)
    if not profile:
        return {}
    
    # Load existing profile if any to track improvements
    skill_dir = find_skill_dir(workspace, "learning-system")
    profile_file = skill_dir / "project_profile.json"
    old_profile = {}
    if profile_file.exists():
        try:
            old_profile = json.loads(profile_file.read_text())
        except json.JSONDecodeError:
            pass
    
    # Identify what changed since last analysis
    improvements = {
        "new_patterns": [],
        "new_frameworks": [],
        "addressed_improvements": [],
        "remaining_improvements": [],
    }
    
    # Check for new patterns
    old_patterns = set(old_profile.get("patterns_detected", []))
    new_patterns = set(profile.get("patterns_detected", []))
    improvements["new_patterns"] = list(new_patterns - old_patterns)
    
    # Check for new frameworks
    old_frameworks = set(old_profile.get("frameworks", []))
    new_frameworks = set(profile.get("frameworks", []))
    improvements["new_frameworks"] = list(new_frameworks - old_frameworks)
    
    # Check addressed improvements
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
    
    # Record learnings to memory
    _record_learning_to_memory(workspace, profile, improvements)
    
    return improvements


def learn_from_topic(workspace: Path, topic: str) -> dict:
    """Learn in a specific direction provided by the user.
    
    This is called when `up learn "topic"` is used.
    """
    console.print(Panel.fit(
        f"[bold blue]Learning System[/] - Focused Learning: {topic}",
        border_style="blue"
    ))
    
    # Check current project profile
    profile = analyze_project(workspace)
    
    # Generate learning plan for the topic
    learning = {
        "topic": topic,
        "project_context": {
            "languages": profile.get("languages", []),
            "frameworks": profile.get("frameworks", []),
        },
        "learning_areas": [],
        "action_items": [],
    }
    
    # Map topic to relevant areas
    topic_lower = topic.lower()
    
    # Categorize the topic
    categories = {
        "testing": ["test", "testing", "unit test", "integration", "coverage", "pytest", "jest"],
        "architecture": ["architecture", "pattern", "design", "structure", "clean", "solid", "ddd"],
        "performance": ["performance", "speed", "fast", "optimize", "cache", "caching"],
        "security": ["security", "auth", "authentication", "authorization", "jwt", "oauth"],
        "api": ["api", "rest", "graphql", "endpoint", "route"],
        "database": ["database", "db", "sql", "orm", "migration", "query"],
        "documentation": ["doc", "documentation", "readme", "comment"],
        "ci_cd": ["ci", "cd", "deploy", "pipeline", "github actions", "jenkins"],
        "error_handling": ["error", "exception", "handling", "logging", "monitoring"],
    }
    
    matched_categories = []
    for cat, keywords in categories.items():
        if any(kw in topic_lower for kw in keywords):
            matched_categories.append(cat)
    
    # Generate learning areas based on categories and frameworks
    if matched_categories:
        for cat in matched_categories:
            for fw in profile.get("frameworks", []):
                learning["learning_areas"].append(f"{fw} {cat} best practices")
        learning["learning_areas"].append(f"{topic} patterns")
    else:
        # General topic
        learning["learning_areas"].append(f"{topic} implementation")
        for fw in profile.get("frameworks", []):
            learning["learning_areas"].append(f"{topic} in {fw}")
    
    # Generate action items
    learning["action_items"] = [
        f"Research {topic} best practices",
        f"Review current codebase for {topic} patterns",
        f"Identify gaps in {topic} implementation",
        f"Create improvement plan for {topic}",
    ]
    
    # Display
    console.print("\n[bold]Learning Focus:[/]")
    console.print(f"  Topic: [cyan]{topic}[/]")
    
    console.print("\n[bold]Areas to Research:[/]")
    for area in learning["learning_areas"][:5]:
        console.print(f"  • {area}")
    
    console.print("\n[bold]Action Items:[/]")
    for item in learning["action_items"]:
        console.print(f"  □ {item}")
    
    # Save learning plan
    skill_dir = find_skill_dir(workspace, "learning-system")
    skill_dir.mkdir(parents=True, exist_ok=True)
    research_dir = skill_dir / "research"
    research_dir.mkdir(exist_ok=True)
    
    # Create research file
    safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(' ', '_').lower()
    research_file = research_dir / f"{date.today().isoformat()}_{safe_topic}.md"
    
    research_content = f"""# Learning: {topic}

**Created**: {date.today().isoformat()}
**Status**: 📋 In Progress

## Context

Project languages: {', '.join(profile.get('languages', ['N/A']))}
Project frameworks: {', '.join(profile.get('frameworks', ['N/A']))}

## Learning Areas

{chr(10).join(f'- [ ] {area}' for area in learning['learning_areas'])}

## Research Notes

*Add your research notes here*

## Action Items

{chr(10).join(f'- [ ] {item}' for item in learning['action_items'])}

## Learnings

*Document what you learn*

## Applied Changes

*Track changes made based on learnings*
"""
    
    research_file.write_text(research_content)
    console.print(f"\n[green]✓[/] Research file created: [cyan]{research_file}[/]")
    
    # Record to memory
    _record_topic_learning(workspace, learning)
    
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  1. Edit [cyan]{research_file}[/] to add your research")
    console.print("  2. Run [cyan]up learn analyze[/] to extract patterns")
    console.print("  3. Run [cyan]up learn plan[/] to generate improvement PRD")
    
    return learning


def learn_from_file(workspace: Path, file_path: str) -> dict:
    """Learn from a single file (markdown, code, config, etc.).
    
    This extracts insights, patterns, and knowledge from individual files.
    """
    source_file = Path(file_path).expanduser().resolve()
    
    if not source_file.exists():
        console.print(f"[red]Error: File not found: {file_path}[/]")
        return {}
    
    console.print(Panel.fit(
        f"[bold blue]Learning System[/] - Learn from File: {source_file.name}",
        border_style="blue"
    ))
    
    # Read file content
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
        "action_items": [],
    }
    
    # Analyze based on file type
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
    
    if learnings["key_concepts"]:
        console.print("\n[green]📚 Key Concepts:[/]")
        for c in learnings["key_concepts"][:10]:
            console.print(f"  • {c}")
    
    if learnings["patterns_found"]:
        console.print("\n[blue]🔷 Patterns Found:[/]")
        for p in learnings["patterns_found"][:10]:
            console.print(f"  • {p}")
    
    if learnings["best_practices"]:
        console.print("\n[yellow]✨ Best Practices:[/]")
        for b in learnings["best_practices"][:10]:
            console.print(f"  • {b}")
    
    if learnings["code_snippets"]:
        console.print("\n[cyan]💻 Notable Code Patterns:[/]")
        for s in learnings["code_snippets"][:5]:
            console.print(f"  • {s}")
    
    # Save learnings
    skill_dir = find_skill_dir(workspace, "learning-system")
    skill_dir.mkdir(parents=True, exist_ok=True)
    learnings_dir = skill_dir / "file_learnings"
    learnings_dir.mkdir(exist_ok=True)
    
    safe_name = re.sub(r'[^\w\s-]', '', source_file.stem).strip().replace(' ', '_').lower()
    learning_file = learnings_dir / f"{date.today().isoformat()}_{safe_name}.json"
    learning_file.write_text(json.dumps(learnings, indent=2))
    
    # Create markdown summary
    summary_file = learnings_dir / f"{date.today().isoformat()}_{safe_name}.md"
    summary_content = f"""# Learnings from: {source_file.name}

**Analyzed**: {date.today().isoformat()}
**Source**: `{source_file}`
**Type**: {file_ext or 'unknown'}

## Key Concepts

{chr(10).join(f'- {c}' for c in learnings['key_concepts']) or '- None extracted'}

## Patterns Found

{chr(10).join(f'- [ ] {p}' for p in learnings['patterns_found']) or '- None identified'}

## Best Practices

{chr(10).join(f'- [ ] {b}' for b in learnings['best_practices']) or '- None identified'}

## Code Snippets / Examples

{chr(10).join(f'- {s}' for s in learnings['code_snippets']) or '- None extracted'}

## Action Items

- [ ] Review extracted concepts
- [ ] Apply relevant patterns to current project
- [ ] Document learnings in project docs

## Original Content Summary

```
{content[:500]}{'...' if len(content) > 500 else ''}
```
"""
    summary_file.write_text(summary_content)
    
    console.print(f"\n[green]✓[/] Learnings saved to: [cyan]{summary_file}[/]")
    
    # Record to memory
    _record_file_learning(workspace, learnings)
    
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  1. Review [cyan]{summary_file}[/]")
    console.print("  2. Apply relevant learnings to your project")
    console.print("  3. Run [cyan]up learn[/] to track improvements")
    
    return learnings


def _analyze_documentation_file(content: str, learnings: dict) -> dict:
    """Extract insights from markdown/documentation files."""
    lines = content.splitlines()
    
    # Extract headers as key concepts
    headers = []
    for line in lines:
        if line.startswith('#'):
            header = line.lstrip('#').strip()
            if header and len(header) > 2:
                headers.append(header)
    learnings["key_concepts"] = headers[:15]
    
    # Look for patterns in content
    pattern_keywords = [
        ('pattern', 'Design pattern mentioned'),
        ('best practice', 'Best practice documented'),
        ('principle', 'Principle defined'),
        ('architecture', 'Architecture concept'),
        ('workflow', 'Workflow described'),
        ('convention', 'Convention defined'),
        ('standard', 'Standard referenced'),
        ('guideline', 'Guideline provided'),
    ]
    
    content_lower = content.lower()
    for keyword, description in pattern_keywords:
        if keyword in content_lower:
            learnings["patterns_found"].append(description)
    
    # Extract bullet points as potential best practices
    for line in lines:
        line = line.strip()
        if line.startswith(('- ', '* ', '• ')) and len(line) > 10:
            practice = line.lstrip('-*• ').strip()
            if len(practice) > 15 and len(practice) < 200:
                learnings["best_practices"].append(practice[:100])
                if len(learnings["best_practices"]) >= 10:
                    break
    
    # Extract code blocks
    in_code_block = False
    code_lang = ""
    for line in lines:
        if line.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_lang = line[3:].strip()
                if code_lang:
                    learnings["code_snippets"].append(f"Code example in {code_lang}")
            else:
                in_code_block = False
                code_lang = ""
    
    return learnings


def _analyze_python_file(content: str, learnings: dict) -> dict:
    """Extract patterns from Python code."""
    lines = content.splitlines()
    
    # Pattern detection
    patterns = {
        r'class.*Repository': 'Repository Pattern',
        r'class.*Service': 'Service Layer Pattern',
        r'class.*Factory': 'Factory Pattern',
        r'@dataclass': 'Dataclass usage',
        r'@property': 'Property decorators',
        r'async def': 'Async/Await pattern',
        r'def test_': 'Unit test pattern',
        r'Protocol\)': 'Protocol (interface) pattern',
        r'@abstractmethod': 'Abstract base class',
        r'TypeVar': 'Generic types',
        r'Callable\[': 'Callable types',
        r'contextmanager': 'Context manager pattern',
        r'@staticmethod': 'Static methods',
        r'@classmethod': 'Class methods',
        r'__enter__': 'Context manager implementation',
        r'yield': 'Generator pattern',
    }
    
    for pattern, name in patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            learnings["patterns_found"].append(name)
    
    # Extract class and function names as concepts
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
    
    # Extract docstrings as best practices
    docstring_pattern = r'"""([^"]+)"""'
    docstrings = re.findall(docstring_pattern, content)
    for doc in docstrings[:5]:
        doc = doc.strip().split('\n')[0]  # First line only
        if len(doc) > 20 and len(doc) < 150:
            learnings["best_practices"].append(doc)
    
    # Note decorators and imports
    imports = [line for line in lines if line.startswith(('import ', 'from '))]
    if imports:
        learnings["code_snippets"].append(f"Uses {len(imports)} imports")
    
    decorators = [line.strip() for line in lines if line.strip().startswith('@')]
    if decorators:
        unique_decorators = list(set(d.split('(')[0] for d in decorators))[:5]
        learnings["code_snippets"].append(f"Decorators: {', '.join(unique_decorators)}")
    
    return learnings


def _analyze_javascript_file(content: str, learnings: dict) -> dict:
    """Extract patterns from JavaScript/TypeScript code."""
    lines = content.splitlines()
    
    # Pattern detection
    patterns = {
        r'async\s+function': 'Async functions',
        r'await\s+': 'Await usage',
        r'export\s+default': 'Default exports',
        r'export\s+const': 'Named exports',
        r'interface\s+': 'TypeScript interfaces',
        r'type\s+\w+\s*=': 'Type aliases',
        r'useState': 'React useState hook',
        r'useEffect': 'React useEffect hook',
        r'useCallback': 'React useCallback hook',
        r'useMemo': 'React useMemo hook',
        r'React\.memo': 'React memoization',
        r'class\s+\w+\s+extends': 'Class inheritance',
        r'=>': 'Arrow functions',
        r'Promise': 'Promise usage',
        r'try\s*{': 'Error handling',
    }
    
    for pattern, name in patterns.items():
        if re.search(pattern, content):
            learnings["patterns_found"].append(name)
    
    # Extract exports and components
    for line in lines:
        if 'export' in line:
            match = re.search(r'export\s+(?:default\s+)?(?:function|const|class)\s+(\w+)', line)
            if match:
                learnings["key_concepts"].append(f"Export: {match.group(1)}")
    
    learnings["key_concepts"] = learnings["key_concepts"][:15]
    
    # Extract JSDoc comments
    jsdoc_pattern = r'/\*\*([^*]+)\*/'
    jsdocs = re.findall(jsdoc_pattern, content)
    for doc in jsdocs[:5]:
        doc = doc.strip().split('\n')[0].strip('* ')
        if len(doc) > 20 and len(doc) < 150:
            learnings["best_practices"].append(doc)
    
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
        # Simple YAML key extraction
        for line in content.splitlines():
            if ':' in line and not line.strip().startswith('#'):
                key = line.split(':')[0].strip()
                if key and not key.startswith('-'):
                    learnings["key_concepts"].append(f"Config: {key}")
                    if len(learnings["key_concepts"]) >= 15:
                        break
    
    elif file_ext == '.toml':
        # Simple TOML section extraction
        for line in content.splitlines():
            if line.strip().startswith('['):
                section = line.strip().strip('[]')
                learnings["key_concepts"].append(f"Section: {section}")
    
    # Look for common config patterns
    config_patterns = [
        ('database', 'Database configuration'),
        ('cache', 'Caching configuration'),
        ('logging', 'Logging configuration'),
        ('auth', 'Authentication configuration'),
        ('api', 'API configuration'),
        ('env', 'Environment configuration'),
    ]
    
    content_lower = content.lower()
    for keyword, description in config_patterns:
        if keyword in content_lower:
            learnings["patterns_found"].append(description)
    
    return learnings


def _analyze_generic_file(content: str, learnings: dict) -> dict:
    """Generic file analysis for unknown types."""
    lines = content.splitlines()
    
    # Extract non-empty lines as potential concepts
    for line in lines[:20]:
        line = line.strip()
        if line and len(line) > 10 and len(line) < 100:
            learnings["key_concepts"].append(line[:80])
    
    learnings["key_concepts"] = learnings["key_concepts"][:10]
    
    return learnings


def _record_file_learning(workspace: Path, learnings: dict) -> None:
    """Record file learning to memory system."""
    try:
        from up.memory import MemoryManager
        
        manager = MemoryManager(workspace, use_vectors=False)
        content = f"Learned from file: {learnings['source_file']}. "
        if learnings['patterns_found']:
            content += f"Patterns: {', '.join(learnings['patterns_found'][:3])}"
        manager.record_learning(content)
    except Exception:
        pass


def learn_from_project(workspace: Path, project_path: str) -> dict:
    """Analyze external project for good design patterns.
    
    This is called when `up learn "project/path"` is used.
    """
    external_project = Path(project_path).expanduser().resolve()
    
    if not external_project.exists():
        console.print(f"[red]Error: Path not found: {project_path}[/]")
        return {}
    
    # If it's a file, use file learning
    if external_project.is_file():
        return learn_from_file(workspace, project_path)
    
    console.print(Panel.fit(
        f"[bold blue]Learning System[/] - Learn from Project: {external_project.name}",
        border_style="blue"
    ))
    
    # Analyze the external project
    console.print("\n[bold]Analyzing External Project...[/]")
    external_profile = analyze_project(external_project)
    
    # Analyze current project
    console.print("\n[bold]Analyzing Current Project...[/]")
    current_profile = analyze_project(workspace)
    
    # Compare and find learnable patterns
    learnings = {
        "source_project": external_project.name,
        "source_path": str(external_project),
        "patterns_to_adopt": [],
        "frameworks_to_consider": [],
        "structure_insights": [],
        "file_organization": [],
    }
    
    # Find patterns in external project that current project doesn't have
    current_patterns = set(current_profile.get("patterns_detected", []))
    external_patterns = set(external_profile.get("patterns_detected", []))
    new_patterns = external_patterns - current_patterns
    learnings["patterns_to_adopt"] = list(new_patterns)
    
    # Find frameworks to consider
    current_frameworks = set(current_profile.get("frameworks", []))
    external_frameworks = set(external_profile.get("frameworks", []))
    
    # Only suggest frameworks for same languages
    common_languages = set(current_profile.get("languages", [])) & set(external_profile.get("languages", []))
    if common_languages:
        new_frameworks = external_frameworks - current_frameworks
        learnings["frameworks_to_consider"] = list(new_frameworks)
    
    # Analyze file structure
    structure_insights = _analyze_project_structure(external_project)
    learnings["structure_insights"] = structure_insights
    
    # Display external project profile
    console.print("\n[bold]External Project Profile:[/]")
    display_profile(external_profile)
    
    # Display comparison
    console.print("\n[bold]Comparison with Current Project:[/]")
    
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
    table.add_row(
        "Patterns",
        ", ".join(current_profile.get("patterns_detected", [])) or "None",
        ", ".join(external_profile.get("patterns_detected", [])) or "None"
    )
    
    console.print(table)
    
    # Display learnings
    if learnings["patterns_to_adopt"]:
        console.print("\n[green]✓ Patterns to Consider Adopting:[/]")
        for p in learnings["patterns_to_adopt"]:
            console.print(f"  • {p}")
    
    if learnings["frameworks_to_consider"]:
        console.print("\n[yellow]○ Frameworks to Consider:[/]")
        for f in learnings["frameworks_to_consider"]:
            console.print(f"  • {f}")
    
    if learnings["structure_insights"]:
        console.print("\n[blue]📁 Structure Insights:[/]")
        for s in learnings["structure_insights"]:
            console.print(f"  • {s}")
    
    # Save learnings
    skill_dir = find_skill_dir(workspace, "learning-system")
    skill_dir.mkdir(parents=True, exist_ok=True)
    learnings_dir = skill_dir / "external_learnings"
    learnings_dir.mkdir(exist_ok=True)
    
    safe_name = re.sub(r'[^\w\s-]', '', external_project.name).strip().replace(' ', '_').lower()
    learning_file = learnings_dir / f"{date.today().isoformat()}_{safe_name}.json"
    learning_file.write_text(json.dumps(learnings, indent=2))
    
    # Also create a markdown summary
    summary_file = learnings_dir / f"{date.today().isoformat()}_{safe_name}.md"
    summary_content = f"""# Learnings from: {external_project.name}

**Analyzed**: {date.today().isoformat()}
**Source**: `{external_project}`

## Patterns to Adopt

{chr(10).join(f'- [ ] {p}' for p in learnings['patterns_to_adopt']) or '- None identified'}

## Frameworks to Consider

{chr(10).join(f'- [ ] {f}' for f in learnings['frameworks_to_consider']) or '- None identified'}

## Structure Insights

{chr(10).join(f'- {s}' for s in learnings['structure_insights']) or '- None identified'}

## Action Items

- [ ] Review patterns and decide which to adopt
- [ ] Create implementation plan for chosen patterns
- [ ] Apply learnings to current project
"""
    summary_file.write_text(summary_content)
    
    console.print(f"\n[green]✓[/] Learnings saved to: [cyan]{summary_file}[/]")
    
    # Record to memory
    _record_external_learning(workspace, learnings)
    
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  1. Review [cyan]{summary_file}[/]")
    console.print("  2. Select patterns to implement")
    console.print("  3. Run [cyan]up learn plan[/] to create improvement PRD")
    
    return learnings


def _analyze_project_structure(project_path: Path) -> list:
    """Analyze project directory structure for insights."""
    insights = []
    
    # Check for common good practices
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
    
    return insights[:5]  # Limit to top 5


def _record_learning_to_memory(workspace: Path, profile: dict, improvements: dict) -> None:
    """Record self-improvement learnings to memory system."""
    try:
        from up.memory import MemoryManager
        
        manager = MemoryManager(workspace, use_vectors=False)  # Fast mode
        
        content = f"Self-improvement analysis: Found {len(profile.get('patterns_detected', []))} patterns, "
        content += f"{len(improvements.get('new_patterns', []))} new patterns adopted, "
        content += f"{len(improvements.get('remaining_improvements', []))} areas for improvement"
        
        if improvements.get('new_patterns'):
            content += f". New patterns: {', '.join(improvements['new_patterns'])}"
        
        manager.record_learning(content)
    except Exception:
        pass  # Memory recording is optional


def _record_topic_learning(workspace: Path, learning: dict) -> None:
    """Record topic learning to memory system."""
    try:
        from up.memory import MemoryManager
        
        manager = MemoryManager(workspace, use_vectors=False)
        content = f"Started learning about: {learning['topic']}. "
        content += f"Research areas: {', '.join(learning['learning_areas'][:3])}"
        manager.record_learning(content)
    except Exception:
        pass


def _record_external_learning(workspace: Path, learnings: dict) -> None:
    """Record external project learning to memory system."""
    try:
        from up.memory import MemoryManager
        
        manager = MemoryManager(workspace, use_vectors=False)
        content = f"Learned from external project: {learnings['source_project']}. "
        if learnings['patterns_to_adopt']:
            content += f"Patterns to adopt: {', '.join(learnings['patterns_to_adopt'][:3])}"
        manager.record_learning(content)
    except Exception:
        pass


def check_ai_cli() -> tuple[str, bool]:
    """Check which AI CLI is available.
    
    Returns:
        (cli_name, available) - e.g., ("claude", True) or ("agent", True)
    """
    import shutil
    
    # Check for Claude CLI first
    if shutil.which("claude"):
        return "claude", True
    
    # Check for Cursor Agent CLI
    if shutil.which("agent"):
        return "agent", True
    
    return "", False


def run_ai_analysis(workspace: Path, content_file: Path, source_name: str) -> tuple[str, str]:
    """Run AI CLI (Claude or Cursor Agent) to analyze the file.
    
    Returns:
        (analysis_text, cli_used)
    """
    import subprocess
    
    cli_name, available = check_ai_cli()
    if not available:
        return "Error: No AI CLI found. Install Claude CLI or Cursor Agent.", ""
    
    # Read content and truncate if too large
    content = content_file.read_text()
    max_chars = 15000  # ~4K tokens, safe for most models
    
    if len(content) > max_chars:
        # Take first and last portions
        half = max_chars // 2
        content = content[:half] + "\n\n[... content truncated for analysis ...]\n\n" + content[-half:]
        truncated = True
    else:
        truncated = False
    
    prompt = f"""Analyze this document and extract:

1. **Key Concepts** - Main ideas, frameworks, and mental models (list 5-10)
2. **Patterns** - Design patterns, workflows, and methodologies  
3. **Best Practices** - Actionable guidelines and recommendations
4. **Implementation Ideas** - Specific ways to apply these learnings

Be concise. Format with markdown headers.

{"[Note: Document was truncated due to size]" if truncated else ""}

Document ({source_name}):
{content}
"""
    
    try:
        # Build command based on CLI
        if cli_name == "claude":
            cmd = ["claude", "-p", prompt]
        else:  # agent (Cursor)
            cmd = ["agent", "-p", prompt]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minute timeout
            cwd=workspace
        )
        
        if result.returncode == 0:
            return result.stdout, cli_name
        else:
            return f"Error running {cli_name}: {result.stderr}", cli_name
    except subprocess.TimeoutExpired:
        return f"Error: {cli_name} timed out after 3 minutes. Try with a smaller file or use -d flag.", cli_name
    except Exception as e:
        return f"Error: {e}", cli_name


def learn_from_file_deep(workspace: Path, file_path: str, auto_run: bool = False) -> dict:
    """Prepare file for deep AI analysis in chat.
    
    This saves the full file content and creates an analysis request
    that can be processed by Claude/Cursor in chat.
    
    If auto_run=True and Claude CLI is available, runs the analysis automatically.
    """
    source_file = Path(file_path).expanduser().resolve()
    
    if not source_file.exists():
        console.print(f"[red]Error: File not found: {file_path}[/]")
        return {}
    
    mode = "Auto Analysis" if auto_run else "Deep Analysis"
    console.print(Panel.fit(
        f"[bold blue]Learning System[/] - {mode}: {source_file.name}",
        border_style="blue"
    ))
    
    # Read file content
    try:
        content = source_file.read_text()
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/]")
        return {}
    
    # Create deep learning directory
    skill_dir = find_skill_dir(workspace, "learning-system")
    skill_dir.mkdir(parents=True, exist_ok=True)
    deep_dir = skill_dir / "deep_analysis"
    deep_dir.mkdir(exist_ok=True)
    
    # Save the full content for AI reference
    safe_name = re.sub(r'[^\w\s-]', '', source_file.stem).strip().replace(' ', '_').lower()
    content_file = deep_dir / f"{safe_name}_content.md"
    
    # Create content file with metadata
    content_with_meta = f"""# Source: {source_file.name}

**Original Path**: `{source_file}`
**Analyzed**: {date.today().isoformat()}
**Size**: {len(content)} characters, {len(content.splitlines())} lines

---

{content}
"""
    content_file.write_text(content_with_meta)
    
    # Create analysis request file
    request_file = deep_dir / f"{safe_name}_analysis_request.md"
    request_content = f"""# Deep Analysis Request: {source_file.name}

**Status**: 🔄 Pending AI Analysis
**Created**: {date.today().isoformat()}

## Source File
`{content_file}`

## Analysis Instructions

Please analyze the source file and extract:

1. **Key Concepts** - Main ideas, frameworks, and mental models
2. **Patterns** - Design patterns, workflows, and best practices
3. **Actionable Insights** - What can be applied to this project
4. **Implementation Ideas** - Specific ways to use these learnings

## How to Analyze

In chat, use one of these approaches:

### Option A: Reference the file
```
@{content_file.relative_to(workspace)}
Please do a deep analysis of this document and extract key concepts and patterns.
```

### Option B: Use the learn-deep command
```
/learn-deep {safe_name}
```

## Analysis Output

*AI will fill this section after analysis*

---
"""
    request_file.write_text(request_content)
    
    # Display results
    console.print(f"\n[bold]File:[/] {source_file.name}")
    console.print(f"[bold]Size:[/] {len(content)} characters, {len(content.splitlines())} lines")
    
    console.print(f"\n[green]✓[/] Content saved to: [cyan]{content_file.relative_to(workspace)}[/]")
    
    # Auto-run with AI CLI if requested
    if auto_run:
        cli_name, cli_available = check_ai_cli()
        if not cli_available:
            console.print("\n[red]Error: No AI CLI found.[/]")
            console.print("Install one of:")
            console.print("  • Claude CLI: [cyan]npm install -g @anthropic-ai/claude-code[/]")
            console.print("  • Cursor Agent: (comes with Cursor IDE)")
            console.print("\nOr use [cyan]up learn -d \"file\"[/] for manual analysis.")
            return {}
        
        console.print(f"\n[yellow]Running {cli_name} for analysis...[/]")
        console.print("[dim](This may take 30-60 seconds)[/]")
        
        analysis, cli_used = run_ai_analysis(workspace, content_file, source_file.name)
        
        # Save analysis result
        analysis_file = deep_dir / f"{safe_name}_analysis.md"
        analysis_content = f"""# Analysis: {source_file.name}

**Analyzed**: {date.today().isoformat()}
**Source**: `{source_file}`
**Method**: {cli_used} CLI (automatic)

---

{analysis}

---

## What's Next?

1. **Review the analysis** - Check the key concepts and patterns above
2. **Apply learnings** - Use insights to improve your project
3. **Track progress** - Run `up learn` to see improvements over time
4. **Generate PRD** - Run `up learn plan` to create improvement tasks
"""
        analysis_file.write_text(analysis_content)
        
        console.print(f"\n[green]✓[/] Analysis saved to: [cyan]{analysis_file.relative_to(workspace)}[/]")
        
        # Display the analysis
        console.print("\n" + "─" * 60)
        console.print(f"[bold green]📊 Analysis Result (via {cli_used}):[/]")
        console.print("─" * 60)
        console.print(analysis)
        console.print("─" * 60)
        
        # Show what's next
        console.print("\n[bold]What's Next?[/]")
        console.print(f"  1. Review: [cyan]@{analysis_file.relative_to(workspace)}[/] in chat")
        console.print("  2. Apply: Use insights to improve your project")
        console.print("  3. Track: Run [cyan]up learn[/] to measure improvements")
        console.print("  4. Plan: Run [cyan]up learn plan[/] to create improvement tasks")
        
        # Record to memory
        try:
            from up.memory import MemoryManager
            manager = MemoryManager(workspace, use_vectors=False)
            manager.record_learning(f"Deep analysis completed for: {source_file.name} via {cli_used}")
        except Exception:
            pass
        
        return {
            "source_file": str(source_file),
            "content_file": str(content_file),
            "analysis_file": str(analysis_file),
            "analysis": analysis,
            "cli_used": cli_used,
        }
    
    # Manual mode: show prompt to copy
    console.print(f"[green]✓[/] Request saved to: [cyan]{request_file.relative_to(workspace)}[/]")
    
    relative_content = content_file.relative_to(workspace)
    
    console.print("\n" + "─" * 60)
    console.print("[bold yellow]📋 Copy this to chat for deep AI analysis:[/]")
    console.print("─" * 60)
    
    prompt = f"""@{relative_content}

Please analyze this document deeply and extract:
1. Key concepts and mental models
2. Design patterns and best practices  
3. Actionable insights for this project
4. Specific implementation ideas

Format as a structured summary I can reference later."""
    
    console.print(f"\n[cyan]{prompt}[/]")
    console.print("\n" + "─" * 60)
    
    console.print("\n[dim]Tip: Use [cyan]up learn --run \"file\"[/] to auto-analyze with Claude CLI[/]")
    
    # Record to memory
    try:
        from up.memory import MemoryManager
        manager = MemoryManager(workspace, use_vectors=False)
        manager.record_learning(f"Queued deep analysis for: {source_file.name}")
    except Exception:
        pass
    
    return {
        "source_file": str(source_file),
        "content_file": str(content_file),
        "request_file": str(request_file),
        "prompt": prompt,
    }


@click.group(invoke_without_command=True)
@click.argument("topic_or_path", required=False)
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
@click.option("--deep", "-d", is_flag=True, help="Prepare for deep AI analysis in chat")
@click.option("--run", "-r", is_flag=True, help="Auto-run analysis with Claude/Cursor CLI")
@click.pass_context
def learn_cmd(ctx, topic_or_path: str, workspace: str, deep: bool, run: bool):
    """Learning system - analyze, research, and improve.
    
    \b
    Usage:
      up learn                    Auto-analyze and improve (requires vision map)
      up learn "topic"            Learn about a specific topic/feature
      up learn "file.md"          Quick extraction from file
      up learn -d "file.md"       Prepare for deep AI analysis in chat
      up learn -r "file.md"       Auto-analyze with Claude/Cursor CLI
    
    \b
    Subcommands:
      up learn auto               Analyze project (no vision check)
      up learn analyze            Analyze research files
      up learn plan               Generate improvement PRD
      up learn status             Show learning system status
    
    \b
    Examples:
      up learn                    # Self-improvement analysis
      up learn "caching"          # Learn about caching
      up learn "guide.md"         # Quick extraction
      up learn -d "guide.md"      # Deep AI analysis (copy prompt to chat)
      up learn -r "guide.md"      # Auto-analyze with Claude/Cursor CLI
    """
    # If subcommand invoked, skip main logic
    if ctx.invoked_subcommand is not None:
        return
    
    # Check if topic_or_path is actually a subcommand name
    # This happens because Click processes arguments before subcommands
    subcommands = ["auto", "analyze", "plan", "status"]
    if topic_or_path in subcommands:
        # Invoke the subcommand
        ctx.invoke(ctx.command.commands[topic_or_path])
        return
    
    ws = Path(workspace) if workspace else Path.cwd()
    
    # No argument: self-improvement mode
    if not topic_or_path:
        # Check if vision map is set up
        vision_exists, vision_path = check_vision_map_exists(ws)
        
        if not vision_exists:
            console.print(Panel.fit(
                "[yellow]Vision Map Not Configured[/]",
                border_style="yellow"
            ))
            console.print("\nThe learning system requires a configured vision map to guide improvements.")
            console.print(f"\nPlease configure: [cyan]{vision_path}[/]")
            console.print("\nThe vision map should include:")
            console.print("  • Your product vision statement")
            console.print("  • Problem statement and pain points")
            console.print("  • Success metrics")
            console.print("\n[bold]Alternatives:[/]")
            console.print("  • [cyan]up learn auto[/] - Analyze without vision map")
            console.print("  • [cyan]up learn \"topic\"[/] - Learn about specific topic")
            console.print("  • [cyan]up learn \"path\"[/] - Learn from another project")
            return
        
        # Vision exists, run self-improvement
        learn_self_improvement(ws)
        return
    
    # Has argument: determine if topic or path
    if is_valid_path(topic_or_path):
        # Check if it's a file and deep/run mode is requested
        target_path = Path(topic_or_path).expanduser()
        if target_path.is_file() and (deep or run):
            learn_from_file_deep(ws, topic_or_path, auto_run=run)
        else:
            learn_from_project(ws, topic_or_path)
    else:
        learn_from_topic(ws, topic_or_path)


@learn_cmd.command("auto")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
def learn_auto(workspace: str):
    """Auto-analyze project and identify improvements.
    
    Scans the codebase to detect technologies, patterns, and
    generate research topics for improvement.
    """
    ws = Path(workspace) if workspace else Path.cwd()
    
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Auto Analysis",
        border_style="blue"
    ))
    
    # Run project analyzer
    profile = analyze_project(ws)
    
    if profile is None:
        console.print("[red]Error: Could not analyze project[/]")
        return
    
    # Display results
    display_profile(profile)
    
    # Save profile
    save_path = save_profile(ws, profile)
    console.print(f"\n[green]✓[/] Profile saved to: [cyan]{save_path}[/]")


    
    # Suggest next steps
    console.print("\n[bold]Next Steps:[/]")
    if profile.get("research_topics"):
        console.print("  1. Research topics with: [cyan]up learn research \"topic\"[/]")
    console.print("  2. Generate PRD with: [cyan]up learn plan[/]")
    console.print("  3. Start development with: [cyan]/product-loop[/]")


@learn_cmd.command("analyze")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
def learn_analyze(workspace: str):
    """Analyze all research files and extract patterns."""
    ws = Path(workspace) if workspace else Path.cwd()
    
    research_dir = find_skill_dir(ws, "learning-system") / "research"
    insights_dir = find_skill_dir(ws, "learning-system") / "insights"
    
    if not research_dir.exists():
        console.print("[yellow]No research files found.[/]")
        console.print("Run [cyan]up learn research \"topic\"[/] first.")
        return
    
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Analyze Research",
        border_style="blue"
    ))
    
    # Count research files
    research_files = list(research_dir.glob("*.md"))
    console.print(f"Found [cyan]{len(research_files)}[/] research files")
    
    for f in research_files:
        console.print(f"  • {f.name}")
    
    console.print("\n[bold]Analysis:[/]")
    console.print("  Use Claude/Cursor to analyze research files and update:")
    console.print(f"  • [cyan]{insights_dir}/patterns.md[/]")
    console.print(f"  • [cyan]{insights_dir}/gap-analysis.md[/]")


@learn_cmd.command("plan")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def learn_plan(workspace: str, output: str):
    """Generate improvement plan (PRD) from analysis."""
    ws = Path(workspace) if workspace else Path.cwd()
    
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Generate PRD",
        border_style="blue"
    ))
    
    # Check for gap analysis
    skill_dir = find_skill_dir(ws, "learning-system")
    gap_file = skill_dir / "insights/gap-analysis.md"
    
    if not gap_file.exists():
        console.print("[yellow]No gap analysis found.[/]")
        console.print("Run analysis first to identify gaps.")
        return
    
    # Load profile if exists
    profile_file = skill_dir / "project_profile.json"
    profile = {}
    if profile_file.exists():
        try:
            profile = json.loads(profile_file.read_text())
        except json.JSONDecodeError:
            pass
    
    # Generate PRD template
    output_path = Path(output) if output else skill_dir / "prd.json"
    prd = generate_prd_template(profile)
    
    output_path.write_text(json.dumps(prd, indent=2))
    console.print(f"[green]✓[/] PRD template created: [cyan]{output_path}[/]")
    console.print("\nEdit the PRD to add specific user stories based on gap analysis.")
    console.print("Then run [cyan]/product-loop[/] to start development.")


@learn_cmd.command("status")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
def learn_status(workspace: str):
    """Show learning system status."""
    ws = Path(workspace) if workspace else Path.cwd()
    
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Status",
        border_style="blue"
    ))
    
    skill_dir = find_skill_dir(ws, "learning-system")
    
    if not skill_dir.exists():
        console.print("[yellow]Learning system not initialized.[/]")
        console.print("Run [cyan]up init[/] to set up.")
        return
    
    # Check files
    files = {
        "Project Profile": skill_dir / "project_profile.json",
        "Sources Config": skill_dir / "sources.json",
        "Patterns": skill_dir / "insights/patterns.md",
        "Gap Analysis": skill_dir / "insights/gap-analysis.md",
        "PRD": skill_dir / "prd.json",
    }
    
    table = Table(title="Learning System Files")
    table.add_column("File", style="cyan")
    table.add_column("Status")
    
    for name, path in files.items():
        if path.exists():
            table.add_row(name, "[green]✓ exists[/]")
        else:
            table.add_row(name, "[dim]○ not created[/]")
    
    console.print(table)
    
    # Count research files
    research_dir = skill_dir / "research"
    if research_dir.exists():
        research_count = len(list(research_dir.glob("*.md")))
        console.print(f"\nResearch files: [cyan]{research_count}[/]")


def find_skill_dir(workspace: Path, skill_name: str) -> Path:
    """Find skill directory (Claude or Cursor)."""
    claude_skill = workspace / f".claude/skills/{skill_name}"
    cursor_skill = workspace / f".cursor/skills/{skill_name}"
    
    if claude_skill.exists():
        return claude_skill
    if cursor_skill.exists():
        return cursor_skill
    
    # Default to Claude
    return claude_skill


def analyze_project(workspace: Path) -> dict:
    """Analyze project and return profile."""
    import os
    import re
    
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


def display_profile(profile: dict) -> None:
    """Display profile in rich format."""
    table = Table(title="Project Profile")
    table.add_column("Aspect", style="cyan")
    table.add_column("Detected")
    
    table.add_row("Name", profile.get("name", "Unknown"))
    table.add_row("Languages", ", ".join(profile.get("languages", [])) or "None")
    table.add_row("Frameworks", ", ".join(profile.get("frameworks", [])) or "None")
    table.add_row("Patterns", ", ".join(profile.get("patterns_detected", [])) or "None")
    table.add_row("Improvements", ", ".join(profile.get("improvement_areas", [])) or "None")
    table.add_row("Research Topics", ", ".join(profile.get("research_topics", [])) or "None")
    
    console.print(table)


def save_profile(workspace: Path, profile: dict) -> Path:
    """Save profile to JSON file."""
    skill_dir = find_skill_dir(workspace, "learning-system")
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = skill_dir / "project_profile.json"
    filepath.write_text(json.dumps(profile, indent=2))
    return filepath


def generate_prd_template(profile: dict) -> dict:
    """Generate PRD template from profile."""
    from datetime import date
    
    prd = {
        "project": profile.get("name", "Project") + " Improvements",
        "branchName": "feature/improvements",
        "description": "Improvements identified by learning system",
        "createdAt": date.today().isoformat(),
        "userStories": [],
    }
    
    # Generate user stories from improvement areas
    for i, area in enumerate(profile.get("improvement_areas", []), 1):
        story = {
            "id": f"US-{i:03d}",
            "title": area.replace("-", " ").title(),
            "description": f"Implement {area.replace('-', ' ')}",
            "acceptanceCriteria": [
                "Implementation complete",
                "Tests passing",
                "Documentation updated",
            ],
            "priority": i,
            "effort": "medium",
            "passes": False,
            "notes": "",
        }
        prd["userStories"].append(story)
    
    return prd


if __name__ == "__main__":
    learn_cmd()
