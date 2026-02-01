# Learning System for Ralph Hybrid

> Automated research, analysis, and improvement planning for the AI Code Auditor

## Overview

The Learning System enables continuous improvement by:
1. Researching top open source security tools and blogs
2. Extracting design patterns and best practices
3. Comparing with current implementation
4. Generating improvement plans (PRD)
5. Handing off to Ralph Hybrid for implementation

## Quick Start

```bash
# Run the learning skill
claude -p "/learn"

# Or run specific phases
claude -p "/learn research taint-analysis"
claude -p "/learn analyze"
claude -p "/learn compare"
claude -p "/learn plan"
claude -p "/learn full"
```

## Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  RESEARCH   │───▶│   ANALYZE   │───▶│   COMPARE   │
│             │    │             │    │             │
│ WebSearch   │    │ Extract     │    │ Gap         │
│ WebFetch    │    │ Patterns    │    │ Analysis    │
└─────────────┘    └─────────────┘    └─────────────┘
                                             │
                                             ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  IMPLEMENT  │◀───│    PLAN     │◀───│             │
│             │    │             │    │             │
│ Ralph       │    │ Generate    │    │             │
│ Hybrid      │    │ PRD         │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Directory Structure

```
.claude/skills/learning-system/
├── SKILL.md              # Skill definition
├── README.md             # This file
├── sources.json          # Research sources config
├── learn.sh              # CLI orchestrator
├── research_agent.py     # Research utilities
├── analysis_engine.py    # Pattern extraction
├── planning_engine.py    # PRD generation
├── research/             # Research findings
│   └── YYYY-MM-DD-*.md   # Topic research files
└── insights/             # Extracted insights
    ├── patterns.md       # Design patterns
    └── gap-analysis.md   # Gap analysis
```

## Research Sources

Configured in `sources.json`:

### Open Source Projects
| Project | Category | Topics |
|---------|----------|--------|
| semgrep | Static Analysis | Pattern matching, multi-language |
| codeql | Query Analysis | Dataflow, taint tracking |
| joern | CPG Analysis | Code property graphs |
| angr | Symbolic Execution | Binary analysis |
| nuclei | Vulnerability Scanner | Templates, YAML DSL |
| bandit | Python Security | AST analysis, plugins |

### Security Blogs
- Project Zero (Google) - Vulnerability research
- Trail of Bits - Program analysis, fuzzing
- PortSwigger Research - Web security

## Output Files

| File | Description |
|------|-------------|
| `research/*.md` | Raw research notes per topic |
| `insights/patterns.md` | Extracted design patterns |
| `insights/gap-analysis.md` | Gaps vs best practices |
| `prd.json` | Generated improvement plan |

## Integration with Ralph Hybrid

After generating a PRD, start Ralph Hybrid:

```bash
# Start autonomous implementation
./.claude/skills/product-loop/ralph_hybrid.sh start

# Monitor progress
./.claude/skills/product-loop/ralph_hybrid.sh status
```

## Python API

```python
from research_agent import ResearchAgent, ResearchFinding
from analysis_engine import AnalysisEngine, Pattern, GapAnalysis
from planning_engine import PlanningEngine, UserStory

# Research
agent = ResearchAgent()
finding = ResearchFinding(
    source="semgrep",
    title="Pattern Matching Architecture",
    summary="...",
    patterns=["visitor pattern", "rule engine"],
    insights=["multi-language support via tree-sitter"]
)
agent.save_finding(finding, "pattern-matching")

# Analysis
engine = AnalysisEngine()
patterns = [Pattern(name="...", source="...", ...)]
engine.save_patterns(patterns)

# Planning
planner = PlanningEngine()
stories = [planner.create_story("US-001", "...", "...", [...], 1)]
planner.generate_prd("Improvements", stories)
```

## Adding New Sources

Edit `sources.json`:

```json
{
  "projects": [
    {
      "name": "new-tool",
      "repo": "org/repo",
      "category": "category",
      "topics": ["topic1", "topic2"],
      "docs_url": "https://..."
    }
  ],
  "blogs": [
    {
      "name": "New Blog",
      "url": "https://...",
      "topics": ["topic1"]
    }
  ]
}
```
