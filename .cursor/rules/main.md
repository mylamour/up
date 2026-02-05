---
description: Main project rules for AI assistance
globs: ["**/*"]
---

# Project Rules

## Skills Available

- `/docs` - Documentation management
- `/learn` - Research and PRD generation
- `/product-loop` - SESRC development workflow

## Workflow

1. **Research**: `/learn auto` - Analyze project and generate insights
2. **Build**: `/product-loop` - Development with circuit breaker
3. **Document**: `/docs new` - Create documentation

## Code Quality

- Always run tests after changes
- Use type hints (Python) or TypeScript strict mode
- Keep functions under 50 lines
- Document public APIs

## Context Management

- Read `docs/CONTEXT.md` for current state
- Update `docs/handoff/LATEST.md` at session end
- Reference specific files with @file syntax

## Error Handling

If something fails twice:
1. Add more context
2. Break into smaller steps
3. Consider a different approach
