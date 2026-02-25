---
name: bisect
description: Walk UP checkpoints to find which change broke tests
allowed-tools:
  - Bash(git *)
  - Bash(python3 -m pytest *)
---

# /bisect — Find Breaking Change

Walk through UP checkpoints to find which change introduced a regression.

1. List available checkpoints with `git tag -l "up-checkpoint/*"`.
2. Run the test command at each checkpoint using binary search.
3. Report which checkpoint introduced the failure.
4. Show the commit diff that caused the regression.

## Default test command
Use `python3 -m pytest --tb=short -q` unless configured otherwise in .up/config.json.
