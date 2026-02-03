---
name: docs
description: Documentation system with standards and templates
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Documentation Skill

Create and maintain standardized documentation.

## Commands

- `/docs init` - Initialize docs structure
- `/docs new [type]` - Create new document
- `/docs status` - Show docs status
- `/docs validate` - Validate headers

## Document Types

| Type | Folder | Purpose |
|------|--------|---------|
| feature | features/ | Feature specs |
| arch | architecture/ | Architecture docs |
| changelog | changelog/ | Progress tracking |
| roadmap | roadmap/ | Planning |
| guide | guides/ | How-to guides |
| todo | todo/ | Task tracking |
