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

from up.ai_cli import check_ai_cli, run_ai_prompt as _run_ai_prompt

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


def learn_self_improvement(workspace: Path, use_ai: bool = True) -> dict:
    """Analyze current project for self-improvement opportunities.
    
    This is called when `up learn` is used without arguments.
    Uses AI by default for deeper insights, with basic analysis as fallback.
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


def learn_from_topic(workspace: Path, topic: str, use_ai: bool = True) -> dict:
    """Learn in a specific direction provided by the user.
    
    This is called when `up learn "topic"` is used.
    Uses AI by default for research generation, with basic analysis as fallback.
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
        "ai_research": None,
    }
    
    # Try AI-powered research first
    if use_ai:
        cli_name, cli_available = check_ai_cli()
        if cli_available:
            console.print(f"\n[yellow]Researching with {cli_name}...[/]")
            ai_result = _ai_research_topic(workspace, topic, profile, cli_name)
            if ai_result:
                learning["ai_research"] = ai_result
    
    # Map topic to relevant areas (fallback or supplement)
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
    
    # Display AI research if available
    if learning.get("ai_research"):
        console.print("\n[green]✓ AI Research Complete[/]")
        console.print(Panel(learning["ai_research"], title=f"Research: {topic}", border_style="green"))
    else:
        # Show basic analysis
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
    
    # Include AI research in the file
    ai_section = ""
    if learning.get("ai_research"):
        ai_section = f"""## AI Research

{learning["ai_research"]}

---

"""
    
    research_content = f"""# Learning: {topic}

**Created**: {date.today().isoformat()}
**Status**: {"✅ Researched" if learning.get("ai_research") else "📋 In Progress"}
**Method**: {"AI-powered" if learning.get("ai_research") else "Basic analysis"}

## Context

Project languages: {', '.join(profile.get('languages', ['N/A']))}
Project frameworks: {', '.join(profile.get('frameworks', ['N/A']))}

{ai_section}## Learning Areas

{chr(10).join(f'- [ ] {area}' for area in learning['learning_areas'])}

## Action Items

{chr(10).join(f'- [ ] {item}' for item in learning['action_items'])}

## Applied Changes

*Track changes made based on learnings*
"""
    
    research_file.write_text(research_content)
    console.print(f"\n[green]✓[/] Research file created: [cyan]{research_file}[/]")
    
    # Record to memory
    _record_topic_learning(workspace, learning)
    
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  1. Review [cyan]{research_file}[/]")
    console.print("  2. Run [cyan]up learn analyze[/] to process all research")
    console.print("  3. Run [cyan]up learn plan[/] to generate improvement PRD")
    
    return learning


def learn_from_file(workspace: Path, file_path: str, use_ai: bool = True) -> dict:
    """Learn from a single file (markdown, code, config, etc.).
    
    Uses AI by default for deep analysis, with basic extraction as fallback.
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
        "ai_analysis": None,
    }
    
    # Try AI analysis first
    ai_success = False
    if use_ai:
        cli_name, cli_available = check_ai_cli()
        if cli_available:
            console.print(f"\n[yellow]Analyzing with {cli_name}...[/]")
            ai_result = _ai_analyze_file(workspace, content, source_file.name, cli_name)
            if ai_result:
                learnings["ai_analysis"] = ai_result
                ai_success = True
    
    # Always do basic extraction (supplements AI or provides fallback)
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
    
    # Show AI analysis if available
    if learnings.get("ai_analysis"):
        console.print("\n[green]✓ AI Analysis Complete[/]")
        console.print(Panel(learnings["ai_analysis"], title="AI Insights", border_style="green"))
    else:
        # Show basic extraction results
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
    
    # Include AI analysis if available
    ai_section = ""
    if learnings.get("ai_analysis"):
        ai_section = f"""## AI Analysis

{learnings["ai_analysis"]}

---

"""
    
    summary_content = f"""# Learnings from: {source_file.name}

**Analyzed**: {date.today().isoformat()}
**Source**: `{source_file}`
**Type**: {file_ext or 'unknown'}
**Method**: {"AI-powered" if learnings.get("ai_analysis") else "Basic extraction"}

{ai_section}## Key Concepts (Basic Extraction)

{chr(10).join(f'- {c}' for c in learnings['key_concepts']) or '- None extracted'}

## Patterns Found

{chr(10).join(f'- [ ] {p}' for p in learnings['patterns_found']) or '- None identified'}

## Best Practices

{chr(10).join(f'- [ ] {b}' for b in learnings['best_practices']) or '- None identified'}

## Action Items

- [ ] Review insights and apply to project
- [ ] Run `up learn analyze` to process all learnings
- [ ] Run `up learn plan` to generate improvement PRD
"""
    summary_file.write_text(summary_content)
    
    console.print(f"\n[green]✓[/] Learnings saved to: [cyan]{summary_file}[/]")
    
    # Record to memory
    _record_file_learning(workspace, learnings)
    
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  1. Review [cyan]{summary_file}[/]")
    console.print("  2. Run [cyan]up learn analyze[/] to process all research")
    console.print("  3. Run [cyan]up learn plan[/] to generate improvement PRD")
    
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


def learn_from_project(workspace: Path, project_path: str, use_ai: bool = True) -> dict:
    """Analyze external project for good design patterns.
    
    This is called when `up learn "project/path"` is used.
    Uses AI by default for deeper comparison insights.
    """
    external_project = Path(project_path).expanduser().resolve()
    
    if not external_project.exists():
        console.print(f"[red]Error: Path not found: {project_path}[/]")
        return {}
    
    # If it's a file, use file learning
    if external_project.is_file():
        return learn_from_file(workspace, project_path, use_ai=use_ai)
    
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


def _ai_research_topic(workspace: Path, topic: str, profile: dict, cli_name: str) -> str | None:
    """Use AI to research a topic in context of the project."""
    languages = ", ".join(profile.get("languages", [])) or "unknown"
    frameworks = ", ".join(profile.get("frameworks", [])) or "none"
    
    prompt = f"""Research the topic "{topic}" for a software project with:
- Languages: {languages}
- Frameworks: {frameworks}

Provide:
1. **Key Concepts** - Main ideas to understand (3-5 items)
2. **Best Practices** - Actionable recommendations (3-5 items)  
3. **Implementation Steps** - How to implement in this stack (3-5 steps)
4. **Common Pitfalls** - What to avoid (2-3 items)

Be concise and practical. Format with markdown."""

    return _run_ai_prompt(workspace, prompt, cli_name, timeout=120)


def _ai_analyze_file(workspace: Path, content: str, filename: str, cli_name: str) -> str | None:
    """Use AI to analyze a file and extract insights."""
    # Truncate if too large
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
3. **Best Practices** - Actionable recommendations to apply
4. **Implementation Ideas** - How to use these learnings

{"[Note: File was truncated due to size]" if truncated else ""}

File ({filename}):
{content}

Be concise. Format with markdown headers."""

    return _run_ai_prompt(workspace, prompt, cli_name, timeout=180)


@click.group(invoke_without_command=True)
@click.argument("topic_or_path", required=False)
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
@click.option("--no-ai", is_flag=True, help="Disable AI analysis (use basic extraction only)")
@click.pass_context
def learn_cmd(ctx, topic_or_path: str, workspace: str, no_ai: bool):
    """Learning system - analyze, research, and improve.
    
    All commands use Claude/Cursor AI by default with automatic fallback.
    
    \b
    Usage:
      up learn                    Auto-analyze and improve (requires vision map)
      up learn "topic"            Learn about a specific topic/feature
      up learn "file.md"          Analyze file with AI (fallback: basic extraction)
      up learn "project/path"     Compare and learn from another project
    
    \b
    Subcommands:
      up learn auto               Analyze project (no vision check)
      up learn analyze            Analyze all research files with AI
      up learn plan               Generate improvement PRD
      up learn status             Show learning system status
    
    \b
    Options:
      --no-ai                     Disable AI analysis (faster, basic extraction)
    
    \b
    Examples:
      up learn                    # Self-improvement with AI
      up learn "caching"          # Learn about caching with AI research
      up learn "guide.md"         # AI-powered file analysis
      up learn "../other-project" # Compare projects with AI insights
    """
    # If subcommand invoked, skip main logic
    if ctx.invoked_subcommand is not None:
        return
    
    # Store options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['workspace'] = workspace
    ctx.obj['no_ai'] = no_ai
    
    # Check if topic_or_path is actually a subcommand name
    # This happens because Click processes arguments before subcommands
    subcommands = ["auto", "analyze", "plan", "status"]
    if topic_or_path in subcommands:
        # Invoke the subcommand with stored options
        subcmd = ctx.command.commands[topic_or_path]
        ctx.invoke(subcmd, workspace=workspace)
        return
    
    ws = Path(workspace) if workspace else Path.cwd()
    use_ai = not no_ai
    
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
        learn_self_improvement(ws, use_ai=use_ai)
        return
    
    # Has argument: determine if topic or path
    if is_valid_path(topic_or_path):
        learn_from_project(ws, topic_or_path, use_ai=use_ai)
    else:
        learn_from_topic(ws, topic_or_path, use_ai=use_ai)


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


def analyze_research_file(file_path: Path, workspace: Path) -> dict:
    """Analyze a single research file using AI CLI."""
    content = file_path.read_text()
    
    # Truncate if too large
    max_chars = 10000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[... truncated ...]"
    
    prompt = f"""Analyze this research document and extract:

1. **Key Patterns** - Design patterns, methodologies, workflows mentioned
2. **Best Practices** - Actionable guidelines and recommendations
3. **Gaps** - What's missing or could be improved in a typical project
4. **Action Items** - Specific things to implement

Be concise. Return as structured markdown.

Research file ({file_path.name}):
{content}
"""
    
    cli_name, available = check_ai_cli()
    if not available:
        return {"error": "No AI CLI available", "file": file_path.name}
    
    import subprocess
    try:
        if cli_name == "claude":
            cmd = ["claude", "-p", prompt]
        else:
            cmd = ["agent", "-p", prompt]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for longer files
            cwd=workspace
        )
        
        if result.returncode == 0:
            return {
                "file": file_path.name,
                "analysis": result.stdout,
                "cli": cli_name
            }
        else:
            return {"error": result.stderr, "file": file_path.name}
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "file": file_path.name}
    except Exception as e:
        return {"error": str(e), "file": file_path.name}


@learn_cmd.command("analyze")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
def learn_analyze(workspace: str):
    """Analyze all research files and extract patterns with AI.
    
    Uses Claude/Cursor AI by default with automatic progress bar.
    Falls back to showing files if AI is unavailable.
    """
    from tqdm import tqdm
    
    ws = Path(workspace) if workspace else Path.cwd()
    
    skill_dir = find_skill_dir(ws, "learning-system")
    research_dir = skill_dir / "research"
    deep_dir = skill_dir / "deep_analysis"
    file_learnings_dir = skill_dir / "file_learnings"
    insights_dir = skill_dir / "insights"
    
    # Collect all analyzable files
    files_to_analyze = []
    
    if research_dir.exists():
        files_to_analyze.extend(list(research_dir.glob("*.md")))
    
    if deep_dir.exists():
        files_to_analyze.extend(list(deep_dir.glob("*_content.md")))
    
    if file_learnings_dir.exists():
        files_to_analyze.extend(list(file_learnings_dir.glob("*.md")))
    
    if not files_to_analyze:
        console.print("[yellow]No research or learning files found.[/]")
        console.print("Run [cyan]up learn \"topic\"[/] or [cyan]up learn \"file.md\"[/] first.")
        return
    
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Analyze Research",
        border_style="blue"
    ))
    
    console.print(f"Found [cyan]{len(files_to_analyze)}[/] files to analyze:")
    for f in files_to_analyze:
        console.print(f"  • {f.name}")
    
    # Check AI availability
    cli_name, cli_available = check_ai_cli()
    if not cli_available:
        # Fallback mode - just show files
        console.print("\n[yellow]No AI CLI available. Showing files for manual review.[/]")
        console.print("\n[bold]Install Claude CLI or Cursor Agent for automatic analysis.[/]")
        console.print("\n[bold]Manual analysis:[/]")
        console.print(f"  Update [cyan]{insights_dir}/patterns.md[/]")
        console.print(f"  Update [cyan]{insights_dir}/gap-analysis.md[/]")
        return
    
    console.print(f"\n[yellow]Analyzing with {cli_name}...[/]")
    
    # Analyze each file with progress bar
    all_patterns = []
    all_practices = []
    all_gaps = []
    all_actions = []
    
    insights_dir.mkdir(parents=True, exist_ok=True)
    
    with tqdm(files_to_analyze, desc="Analyzing", unit="file") as pbar:
        for file_path in pbar:
            pbar.set_postfix_str(file_path.name[:30])
            
            result = analyze_research_file(file_path, ws)
            
            if "error" in result:
                console.print(f"\n[red]Error analyzing {file_path.name}: {result['error']}[/]")
                continue
            
            # Save individual analysis
            analysis_file = insights_dir / f"{file_path.stem}_insights.md"
            analysis_file.write_text(f"""# Insights: {file_path.name}

**Analyzed**: {date.today().isoformat()}
**Source**: `{file_path}`
**Method**: {result.get('cli', 'unknown')} CLI

---

{result['analysis']}
""")
            
            # Collect for combined report
            all_patterns.append(f"### From {file_path.name}\n{result['analysis']}")
    
    # Generate combined insights files
    patterns_file = insights_dir / "patterns.md"
    patterns_content = f"""# Patterns Extracted

**Generated**: {date.today().isoformat()}
**Files Analyzed**: {len(files_to_analyze)}
**Method**: {cli_name} CLI (automatic)

---

{chr(10).join(all_patterns)}
"""
    patterns_file.write_text(patterns_content)
    
    # Generate gap analysis
    gap_file = insights_dir / "gap-analysis.md"
    gap_content = f"""# Gap Analysis

**Generated**: {date.today().isoformat()}
**Based on**: {len(files_to_analyze)} research files

---

## Summary

Review the individual insight files in this directory for detailed analysis.

## Files Analyzed

{chr(10).join(f'- {f.name}' for f in files_to_analyze)}

## Next Steps

1. Review patterns in `patterns.md`
2. Identify gaps relevant to your project
3. Run `up learn plan` to generate improvement PRD
"""
    gap_file.write_text(gap_content)
    
    console.print(f"\n[green]✓[/] Analysis complete!")
    console.print(f"\n[bold]Generated:[/]")
    console.print(f"  • [cyan]{patterns_file.relative_to(ws)}[/]")
    console.print(f"  • [cyan]{gap_file.relative_to(ws)}[/]")
    console.print(f"  • {len(files_to_analyze)} individual insight files")
    
    console.print("\n[bold]Next Steps:[/]")
    console.print("  1. Review: [cyan]@" + str(patterns_file.relative_to(ws)) + "[/]")
    console.print("  2. Generate PRD: [cyan]up learn plan[/]")
    console.print("  3. Start development: [cyan]up start[/]")


@learn_cmd.command("plan")
@click.option("--workspace", "-w", type=click.Path(exists=True), help="Workspace path")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def learn_plan(workspace: str, output: str):
    """Generate improvement plan (PRD) from analysis.
    
    Uses AI to convert insights and patterns into actionable user stories.
    """
    ws = Path(workspace) if workspace else Path.cwd()
    
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Generate PRD",
        border_style="blue"
    ))
    
    skill_dir = find_skill_dir(ws, "learning-system")
    insights_dir = skill_dir / "insights"
    
    # Collect all insights
    insights_content = []
    
    # Read patterns
    patterns_file = insights_dir / "patterns.md"
    if patterns_file.exists():
        content = patterns_file.read_text()
        if len(content) > 100:  # Not just template
            insights_content.append(f"## Patterns\n{content}")
    
    # Read gap analysis
    gap_file = insights_dir / "gap-analysis.md"
    if gap_file.exists():
        content = gap_file.read_text()
        if len(content) > 100:
            insights_content.append(f"## Gap Analysis\n{content}")
    
    # Read individual insight files
    for f in insights_dir.glob("*_insights.md"):
        content = f.read_text()
        insights_content.append(f"## {f.stem}\n{content[:2000]}")
    
    # Read research files
    research_dir = skill_dir / "research"
    if research_dir.exists():
        for f in research_dir.glob("*.md"):
            content = f.read_text()
            if "AI Research" in content:  # Has AI-generated content
                insights_content.append(f"## Research: {f.stem}\n{content[:2000]}")
    
    # Read file learnings
    learnings_dir = skill_dir / "file_learnings"
    if learnings_dir.exists():
        for f in learnings_dir.glob("*.md"):
            content = f.read_text()
            if "AI Analysis" in content:
                insights_content.append(f"## Learning: {f.stem}\n{content[:2000]}")
    
    if not insights_content:
        console.print("[yellow]No insights found to generate PRD.[/]")
        console.print("Run [cyan]up learn analyze[/] first to process research files.")
        return
    
    console.print(f"Found [cyan]{len(insights_content)}[/] insight sources")
    
    # Load profile if exists
    profile_file = skill_dir / "project_profile.json"
    profile = {}
    if profile_file.exists():
        try:
            profile = json.loads(profile_file.read_text())
        except json.JSONDecodeError:
            pass
    
    # Try AI to generate user stories
    cli_name, cli_available = check_ai_cli()
    user_stories = []
    
    if cli_available:
        console.print(f"\n[yellow]Generating tasks with {cli_name}...[/]")
        
        # Truncate insights if too long
        all_insights = "\n\n".join(insights_content)
        if len(all_insights) > 10000:
            all_insights = all_insights[:10000] + "\n\n[... truncated ...]"
        
        prompt = f"""Based on these insights and learnings, generate 5-10 actionable improvement tasks.

Project context:
- Languages: {', '.join(profile.get('languages', ['unknown']))}
- Frameworks: {', '.join(profile.get('frameworks', ['unknown']))}

Insights:
{all_insights}

Return ONLY a JSON array of user stories in this exact format:
[
  {{"id": "US-001", "title": "Short title", "description": "What to implement", "priority": "high|medium|low", "effort": "small|medium|large"}},
  ...
]

Focus on practical, implementable improvements. No explanation, just the JSON array."""

        result = _run_ai_prompt(ws, prompt, cli_name, timeout=120)
        
        if result:
            # Try to parse JSON from response
            try:
                # Find JSON array in response
                import re
                json_match = re.search(r'\[[\s\S]*\]', result)
                if json_match:
                    user_stories = json.loads(json_match.group())
                    console.print(f"[green]✓[/] Generated {len(user_stories)} user stories")
            except json.JSONDecodeError:
                console.print("[yellow]Could not parse AI response, using template[/]")
    
    if not user_stories:
        # Fallback: extract action items from insights
        console.print("[yellow]Using basic task generation...[/]")
        
        # Parse insights for action items (- [ ] checkbox items)
        all_insights = "\n".join(insights_content)
        action_items = []
        
        # Find checkbox items: - [ ] task description
        for line in all_insights.splitlines():
            line = line.strip()
            if line.startswith("- [ ]"):
                item = line[5:].strip()
                if item and len(item) > 5:
                    action_items.append(item)
        
        # Also find numbered items after "Action Items" header
        in_action_section = False
        for line in all_insights.splitlines():
            if "action item" in line.lower() or "immediate" in line.lower():
                in_action_section = True
                continue
            if in_action_section:
                if line.startswith("#") or line.startswith("**") and not "- [" in line:
                    in_action_section = False
                elif line.strip().startswith("-") and len(line.strip()) > 3:
                    item = line.strip().lstrip("-[ ]").strip()
                    if item and item not in action_items:
                        action_items.append(item)
        
        # Fallback to improvement areas if no action items found
        if not action_items:
            action_items = profile.get("improvement_areas", [])
        
        # Generate user stories from action items
        for i, item in enumerate(action_items[:10], 1):
            # Determine priority based on keywords
            priority = "medium"
            if any(w in item.lower() for w in ["immediate", "critical", "urgent", "must"]):
                priority = "high"
            elif any(w in item.lower() for w in ["optional", "nice", "later", "future"]):
                priority = "low"
            
            user_stories.append({
                "id": f"US-{i:03d}",
                "title": item[:60] + ("..." if len(item) > 60 else ""),
                "description": item,
                "priority": priority,
                "effort": "medium"
            })
        
        if user_stories:
            console.print(f"[green]✓[/] Extracted {len(user_stories)} tasks from insights")
    
    # Generate PRD
    prd = {
        "name": profile.get("name", ws.name),
        "version": "1.0.0",
        "generated": date.today().isoformat(),
        "source": "up learn plan",
        "userStories": user_stories,
        "metadata": {
            "insights_count": len(insights_content),
            "ai_generated": cli_available and len(user_stories) > 0,
        }
    }
    
    output_path = Path(output) if output else skill_dir / "prd.json"
    output_path.write_text(json.dumps(prd, indent=2))
    
    console.print(f"\n[green]✓[/] PRD generated: [cyan]{output_path}[/]")
    
    # Display user stories
    if user_stories:
        console.print("\n[bold]Generated User Stories:[/]")
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Priority")
        table.add_column("Effort")
        
        for story in user_stories[:10]:
            table.add_row(
                story.get("id", "?"),
                story.get("title", "")[:50],
                story.get("priority", "medium"),
                story.get("effort", "medium")
            )
        console.print(table)
    
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  1. Review: [cyan]{output_path}[/]")
    console.print("  2. Edit priorities/details as needed")
    console.print("  3. Start development: [cyan]up start[/]")


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
