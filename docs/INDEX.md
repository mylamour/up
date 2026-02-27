# Documentation Index

**Updated**: 2026-02-26

> AI: Use this index to quickly find relevant documentation.

---

## Quick Reference

| Topic | File | Description |
|-------|------|-------------|
| Project State | CONTEXT.md | Current status, architecture, key files |
| Recent Work | handoff/LATEST.md | Last session summary |
| Vision | roadmap/vision/PRODUCT_VISION.md | Product goals and target users |
| Improvement Plan | roadmap/IMPROVEMENT_PLAN.md | Development roadmap |

## By Category

### Architecture
| Topic | File |
|-------|------|
| SESRC Design | architecture/SESRC_DESIGN.md |
| Integrated Lifecycle | architecture/INTEGRATED_LIFECYCLE.md |
| Multi-Worktree Execution | architecture/MULTI_WORKTREE_EXECUTION.md |

### Plugin System
| Topic | Location |
|-------|----------|
| Builtin: memory | src/up/plugins/builtin/memory/plugin.json |
| Builtin: safety | src/up/plugins/builtin/safety/plugin.json |
| Builtin: verify | src/up/plugins/builtin/verify/plugin.json |
| Builtin: provenance | src/up/plugins/builtin/provenance/plugin.json |
| Installed: code-review | src/up/plugins/installed/code-review/plugin.json |
| Installed: security-guidance | src/up/plugins/installed/security-guidance/plugin.json |
| Plugin template | src/up/templates/projects/plugin/ |

### Memory System
| Topic | Location |
|-------|----------|
| Data models | src/up/memory/entry.py |
| Storage backends | src/up/memory/stores.py |
| Manager API | src/up/memory/_manager.py |
| Error patterns | src/up/memory/patterns.py |

### Config Sync
| Topic | Location |
|-------|----------|
| Renderer base | src/up/sync/renderer.py |
| CLAUDE.md generator | src/up/sync/claude_md.py |
| .cursorrules generator | src/up/sync/cursorrules.py |
| .claude/settings.json | src/up/sync/claude_settings.py |

### Guides
| Topic | File |
|-------|------|
| Cursor + Claude Integration | guides/CURSOR_CLAUDE_INTEGRATION.md |
| Concurrency & Thread Safety | guides/CONCURRENCY_AND_THREAD_SAFETY.md |

### Research & Analysis
| Topic | File |
|-------|------|
| AI Vibing Coding Approach | AI_VIBING_CODING_APPROACH.md |
| AI Programming Behavioral Analysis | AI_PROGRAMMING_BEHAVIORAL_ANALYSIS.md |
| Multi-Agent Skills Design | MULTI_AGENT_SKILLS_DESIGN.md |

---

## How to Update

When adding new docs, update this index:
1. Add entry to relevant category table
2. Keep descriptions brief (5-10 words)
3. Use relative paths
