---
name: commit
description: Stage changes and generate an AI-powered commit message
allowed-tools:
  - Bash(git *)
  - Bash(ruff *)
---

# /commit — AI-Powered Commit

1. Run `git diff --stat` to see what changed.
2. Run `git add -A` to stage all changes.
3. Analyze the staged diff and generate a concise, conventional commit message.
4. Run `git commit -m "<message>"` with the generated message.
5. Show the commit hash and summary.

## Rules
- Use conventional commits format: `type(scope): description`
- Keep the first line under 72 characters
- Only use `git` commands — no other tools
