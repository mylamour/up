"""up learn - Learning system CLI commands."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def learn_cmd():
    """Learning system commands.
    
    Research best practices, analyze code, and generate improvement plans.
    """
    pass


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
