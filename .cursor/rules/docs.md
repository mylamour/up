---
description: Documentation standards
globs: ["docs/**/*.md", "*.md"]
---

# Documentation Rules

## Structure

All docs should have:
1. Title (H1)
2. Metadata (Updated date, Status)
3. Horizontal rule separator
4. Content sections

## Header Template

```markdown
# Document Title

**Updated**: YYYY-MM-DD
**Status**: 🔄 Active | ✅ Completed | 📋 Draft

---
```

## Status Icons

| Icon | Meaning |
|------|---------|
| 📋 | Draft/Planned |
| 🔄 | Active/In Progress |
| ✅ | Completed |
| ⏸️ | Paused |
| ❌ | Cancelled |

## Tables

Use tables for structured information:

```markdown
| Column 1 | Column 2 |
|----------|----------|
| Value 1 | Value 2 |
```

## Code Blocks

Always specify language:

```python
def example():
    pass
```

## Links

- Use relative paths for internal docs
- Use descriptive link text
- Example: [Architecture Overview](./architecture/README.md)

## Key Files

| File | Purpose |
|------|---------|
| docs/CONTEXT.md | AI reads first |
| docs/INDEX.md | Quick reference |
| docs/handoff/LATEST.md | Session continuity |
