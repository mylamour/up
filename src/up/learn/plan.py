"""PRD generation for the learning system."""

import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tqdm import tqdm

from up.ai_cli import check_ai_cli, run_ai_prompt
from up.learn.utils import find_skill_dir, load_profile

console = Console()


def analyze_research_file(file_path: Path, workspace: Path) -> dict:
    """Analyze a single research file using AI CLI."""
    content = file_path.read_text()
    
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
    
    try:
        if cli_name == "claude":
            cmd = ["claude", "-p", prompt]
        else:
            cmd = ["agent", "-p", prompt]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
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


def learn_analyze(workspace: Path) -> None:
    """Analyze all research files and extract patterns with AI."""
    skill_dir = find_skill_dir(workspace, "learning-system")
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
    
    console.print(f"Found [cyan]{len(files_to_analyze)}[/] files to analyze")
    
    cli_name, cli_available = check_ai_cli()
    if not cli_available:
        console.print("\n[yellow]No AI CLI available.[/]")
        console.print("Install Claude CLI or Cursor Agent for automatic analysis.")
        return
    
    console.print(f"\n[yellow]Analyzing with {cli_name}...[/]")
    
    all_patterns = []
    insights_dir.mkdir(parents=True, exist_ok=True)
    
    with tqdm(files_to_analyze, desc="Analyzing", unit="file") as pbar:
        for file_path in pbar:
            pbar.set_postfix_str(file_path.name[:30])
            
            result = analyze_research_file(file_path, workspace)
            
            if "error" in result:
                console.print(f"\n[red]Error analyzing {file_path.name}: {result['error']}[/]")
                continue
            
            # Save individual analysis
            analysis_file = insights_dir / f"{file_path.stem}_insights.md"
            analysis_file.write_text(f"""# Insights: {file_path.name}

**Analyzed**: {date.today().isoformat()}
**Source**: `{file_path}`

---

{result['analysis']}
""")
            
            all_patterns.append(f"### From {file_path.name}\n{result['analysis']}")
    
    # Generate combined insights
    patterns_file = insights_dir / "patterns.md"
    patterns_content = f"""# Patterns Extracted

**Generated**: {date.today().isoformat()}
**Files Analyzed**: {len(files_to_analyze)}

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

## Files Analyzed

{chr(10).join(f'- {f.name}' for f in files_to_analyze)}

## Next Steps

1. Review patterns in `patterns.md`
2. Run `up learn plan` to generate improvement PRD
"""
    gap_file.write_text(gap_content)
    
    console.print(f"\n[green]✓[/] Analysis complete!")
    console.print(f"\n[bold]Generated:[/]")
    console.print(f"  • [cyan]{patterns_file.relative_to(workspace)}[/]")
    console.print(f"  • [cyan]{gap_file.relative_to(workspace)}[/]")


def learn_plan(workspace: Path, output: Optional[str] = None) -> None:
    """Generate improvement plan (PRD) from analysis."""
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Generate PRD",
        border_style="blue"
    ))
    
    skill_dir = find_skill_dir(workspace, "learning-system")
    insights_dir = skill_dir / "insights"
    
    # Collect all insights
    insights_content = []
    
    patterns_file = insights_dir / "patterns.md"
    if patterns_file.exists():
        content = patterns_file.read_text()
        if len(content) > 100:
            insights_content.append(f"## Patterns\n{content}")
    
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
            if "AI Research" in content:
                insights_content.append(f"## Research: {f.stem}\n{content[:2000]}")
    
    if not insights_content:
        console.print("[yellow]No insights found to generate PRD.[/]")
        console.print("Run [cyan]up learn analyze[/] first.")
        return
    
    console.print(f"Found [cyan]{len(insights_content)}[/] insight sources")
    
    profile = load_profile(workspace)
    
    # Try AI to generate user stories
    cli_name, cli_available = check_ai_cli()
    user_stories = []
    
    if cli_available:
        console.print(f"\n[yellow]Generating tasks with {cli_name}...[/]")
        
        all_insights = "\n\n".join(insights_content)
        if len(all_insights) > 10000:
            all_insights = all_insights[:10000] + "\n\n[... truncated ...]"
        
        prompt = f"""Based on these insights, generate 5-10 actionable improvement tasks.

Project context:
- Languages: {', '.join(profile.get('languages', ['unknown']))}
- Frameworks: {', '.join(profile.get('frameworks', ['unknown']))}

Insights:
{all_insights}

Return ONLY a JSON array of user stories:
[
  {{"id": "US-001", "title": "Short title", "description": "What to implement", "priority": "high|medium|low", "effort": "small|medium|large"}},
  ...
]

Focus on practical improvements. No explanation, just the JSON array."""

        result = run_ai_prompt(workspace, prompt, cli_name, timeout=120)
        
        if result:
            try:
                json_match = re.search(r'\[[\s\S]*\]', result)
                if json_match:
                    user_stories = json.loads(json_match.group())
                    console.print(f"[green]✓[/] Generated {len(user_stories)} user stories")
            except json.JSONDecodeError:
                console.print("[yellow]Could not parse AI response[/]")
    
    if not user_stories:
        # Fallback: extract action items from insights
        console.print("[yellow]Using basic task generation...[/]")
        
        all_insights = "\n".join(insights_content)
        action_items = []
        
        for line in all_insights.splitlines():
            line = line.strip()
            if line.startswith("- [ ]"):
                item = line[5:].strip()
                if item and len(item) > 5:
                    action_items.append(item)
        
        if not action_items:
            action_items = profile.get("improvement_areas", [])
        
        for i, item in enumerate(action_items[:10], 1):
            priority = "medium"
            if any(w in item.lower() for w in ["immediate", "critical", "urgent"]):
                priority = "high"
            elif any(w in item.lower() for w in ["optional", "later", "future"]):
                priority = "low"
            
            user_stories.append({
                "id": f"US-{i:03d}",
                "title": item[:60] + ("..." if len(item) > 60 else ""),
                "description": item,
                "priority": priority,
                "effort": "medium"
            })
        
        if user_stories:
            console.print(f"[green]✓[/] Extracted {len(user_stories)} tasks")
    
    # Generate PRD
    prd = {
        "name": profile.get("name", workspace.name),
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
    
    if user_stories:
        console.print("\n[bold]Generated User Stories:[/]")
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Priority")
        
        for story in user_stories[:10]:
            table.add_row(
                story.get("id", "?"),
                story.get("title", "")[:50],
                story.get("priority", "medium")
            )
        console.print(table)
    
    console.print("\n[bold]Next Steps:[/]")
    console.print(f"  1. Review: [cyan]{output_path}[/]")
    console.print("  2. Start development: [cyan]up start[/]")


def learn_status(workspace: Path) -> None:
    """Show learning system status."""
    console.print(Panel.fit(
        "[bold blue]Learning System[/] - Status",
        border_style="blue"
    ))
    
    skill_dir = find_skill_dir(workspace, "learning-system")
    
    if not skill_dir.exists():
        console.print("[yellow]Learning system not initialized.[/]")
        console.print("Run [cyan]up init[/] to set up.")
        return
    
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
    
    research_dir = skill_dir / "research"
    if research_dir.exists():
        research_count = len(list(research_dir.glob("*.md")))
        console.print(f"\nResearch files: [cyan]{research_count}[/]")
