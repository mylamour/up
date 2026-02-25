---
name: review
description: Run adversarial code review on recent changes
allowed-tools:
  - Bash(git *)
  - Read
---

# /review — Adversarial Code Review

Review the most recent changes with a critical eye.

1. Run `git diff HEAD~1` to get the changes.
2. For each changed file, analyze for:
   - Logic errors or edge cases
   - Security vulnerabilities
   - Performance issues
   - Missing error handling
3. Score each finding 0-100 confidence.
4. Only report findings with confidence >= 80.
5. Present results as a table: File | Line | Severity | Description.
