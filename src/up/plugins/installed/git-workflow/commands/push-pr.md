---
name: push-pr
description: Push branch and create a pull request via gh CLI
allowed-tools:
  - Bash(git *)
  - Bash(gh *)
---

# /push-pr — Push and Create PR

1. Get the current branch name with `git branch --show-current`.
2. Push the branch to origin: `git push -u origin <branch>`.
3. Generate a PR title from recent commit messages.
4. Create a PR with `gh pr create --title "<title>" --body "<body>"`.
5. Show the PR URL.

## Rules
- Only use `git` and `gh` commands
- PR title should be concise (under 70 chars)
- PR body should summarize all commits on the branch
