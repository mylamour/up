# Insights: 2026-02-04_git_for_ai_vibe_coding.md

**Analyzed**: 2026-02-04
**Source**: `/Users/mour/AI/up-cli/.claude/skills/learning-system/file_learnings/2026-02-04_git_for_ai_vibe_coding.md`
**Method**: claude CLI

---

I'll analyze this research document and extract the key information.

## Analysis: Git for AI Vibe Coding

### 1. Key Patterns

| Pattern | Description |
|---------|-------------|
| **Commit-Before-Prompt** | Always commit clean state before AI generation |
| **Hard Reset Recovery** | Reset immediately on bad generation vs "prompting out" |
| **Git Worktrees** | Parallel development with multiple AI agents in separate directories |
| **Specification-Driven** | Use specs/rules files before code generation |
| **Composer Model** | IDE-native AI editing multiple files simultaneously |
| **Version Loop Tightening** | "Prompt → Generate → Visual Diff → Reset/Commit" replaces traditional cycle |

### 2. Best Practices

1. **Never "prompt your way out"** - Reset and refine prompt instead of iterating on bad code
2. **Use `.cursorrules`/`CLAUDE.md`** - Gatekeeper files for AI behavior constraints
3. **Review every diff** - Treat AI as pair programmer, not autonomous agent
4. **Commit atomically** - Small, logical commits for easier `git bisect` debugging
5. **Preserve prompt context** - Document the "why" alongside commits
6. **Avoid "Apply All" blindly** - Scrutinize multi-file changes
7. **Use worktrees for parallel agents** - Prevents agents from overwriting each other

### 3. Gaps Identified

| Gap | Impact |
|-----|--------|
| **Provenance Obscurity** | `git blame` shows who prompted, but reasoning/prompt context is lost |
| **Contextual Overwrite Risk** | AI may delete critical edge-case handling outside its context window |
| **The "70% Problem"** | Final 30% of integration/debugging takes exponentially longer |
| **"Paint Sprayer" Effect** | AI generates "black boxes" vs "white box" understanding |
| **Commit Explosion** | Features that take humans 3 commits may take 30+ with AI |

### 4. Action Items

**Immediate (for up-cli)**:
- [ ] Add pre-prompt checkpoint command (auto-commit/stash before AI ops)
- [ ] Implement "doom loop" detection (warn after multiple failed prompts)
- [ ] Add context budget tracking to prevent contextual overwrite

**Short-term**:
- [ ] Prompt logging - store prompts alongside commits for provenance
- [ ] Diff review workflow - integrate mandatory visual diff step
- [ ] Worktree orchestration - manage parallel agent branches

**Workflow to Implement**:
```bash
# Vibe coding safety loop
1. git commit -m "checkpoint: before AI prompt"
2. Run AI generation
3. Review diff (mandatory)
4. Accept → commit with prompt context
   OR Reject → git reset --hard HEAD
```

**Constraint Examples for CLAUDE.md**:
- "Before applying changes to more than 3 files, propose a plan"
- "Never delete comments marked `// CRITICAL`"

