# Learnings from: Git for AI Vibe Coding.txt

**Analyzed**: 2026-02-04
**Source**: `/Users/mour/AI/up-cli/Git for AI Vibe Coding.txt`
**Type**: .txt
**Method**: AI-powered

## AI Analysis

I'll analyze this document on Git strategies for AI-driven "vibe coding" development.

## Key Concepts

1. **Vibe Coding Paradigm** - Development where intent orchestration replaces manual coding; developer acts as architect directing AI builders

2. **Pure vs Responsible Vibe Coding** - Pure is exploratory/rapid prototyping; Responsible maintains code ownership with rigorous review

3. **The "70% Problem"** - AI gets you 70% there instantly, but final 30% of integration/debugging takes exponentially longer

4. **"Paint Sprayer" Effect** - AI generates code as "black boxes" vs the "white box" understanding of manual coding

5. **Version Loop Tightening** - Traditional "Code → Test → Commit" becomes "Prompt → Generate → Visual Diff → Reset/Commit"

6. **Git as "Ripcord"** - Commit before every significant prompt; `git reset --hard` immediately on flawed generation

7. **Provenance Obscurity** - `git blame` shows who prompted, but the reasoning/prompt context is lost

8. **Contextual Overwrite Risk** - AI may delete critical edge-case handling outside its context window

## Patterns

| Pattern | Description |
|---------|-------------|
| **Commit-Before-Prompt** | Always commit clean state before AI generation |
| **Hard Reset Recovery** | Reset immediately on bad generation vs "prompting out" |
| **Git Worktrees** | Parallel development with multiple AI agents |
| **Specification-Driven** | Tools like Copilot Workspace use specs before code |
| **Composer Model** | IDE-native AI editing multiple files simultaneously |

## Best Practices

1. **Never "prompt your way out"** of bad generation - reset and refine the prompt instead
2. **Use `.cursorrules`** (or equivalent) as a gatekeeper for AI behavior
3. **Review every diff** in responsible mode - treat AI as pair programmer, not autonomous agent
4. **Commit atomically** - small, logical commits for easier bisect debugging
5. **Preserve prompt context** - document the "why" alongside commits for future debugging
6. **Avoid "Apply All" blindly** - scrutinize multi-file changes before accepting
7. **Use worktrees for parallel agents** - prevents agents from overwriting each other

## Implementation Ideas

### For up-cli

1. **Add pre-prompt checkpoint command** - Auto-commit or stash before AI operations
2. **Prompt logging** - Store prompts alongside commits for provenance
3. **Worktree orchestration** - Manage parallel agent branches with automatic merge conflict detection
4. **"Doom loop" detection** - Warn when multiple failed prompts suggest need for reset
5. **Diff review workflow** - Integrate visual diff step before accepting AI changes
6. **Context budget awareness** - Track AI context window usage to prevent contextual overwrite

### Workflow Integration

```
# Proposed vibe coding safety loop
1. git commit -m "checkpoint: before AI prompt"
2. Run AI generation
3. Review diff (mandatory)
4. Accept → commit with prompt context
   OR Reject → git reset --hard HEAD
```

---

## Key Concepts (Basic Extraction)

- !/bin/bash
- Save as test_regression.sh and make executable (chmod +x)
- 1. Build the project. If the build fails, we can't test.
- We return 125 to tell git bisect to 'skip' this commit.
- 2. Run the specific test case that reproduces the bug.
- Do NOT run the full suite; it's too slow. Focus on the regression.
- 3. Return exit code to git bisect
- 0 = Good (Bug not present)
- 1 = Bad (Bug present)
- .cursorrules
- Add to.zshrc or.bashrc

## Patterns Found

- [ ] Design pattern mentioned
- [ ] Best practice documented
- [ ] Architecture concept
- [ ] Workflow described
- [ ] Convention defined
- [ ] Standard referenced

## Best Practices

- [ ] Constraint Example: "Before applying changes to more than 3 files, propose a plan."
- [ ] Constraint Example: "Never delete comments marked // CRITICAL."
- [ ] The Cost: This can lead to "commit explosion." A feature that takes a human 3 commits might take Aid
- [ ] Create branch feat/login-page from main.
- [ ] Run git worktree add.worktrees/login-page feat/login-page.
- [ ] Copy necessary .env files or context configs to the new directory.
- [ ] Open a new terminal tab/pane in that directory.
- [ ] git bisect start
- [ ] git bisect bad (Current broken state)
- [ ] git bisect good <commit-hash-from-yesterday>

## Action Items

- [ ] Review insights and apply to project
- [ ] Run `up learn analyze` to process all learnings
- [ ] Run `up learn plan` to generate improvement PRD
