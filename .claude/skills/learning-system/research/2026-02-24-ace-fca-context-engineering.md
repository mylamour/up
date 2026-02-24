# Research: Advanced Context Engineering for Coding Agents (ACE-FCA)

**Created**: 2026-02-24
**Status**: 📋 Reference
**Source**: HumanLayer (Dex Horthy) - humanlayer.dev

---

## Key Findings

1. **Context window is the only lever** - LLMs are pure functions; output quality depends entirely on input quality
2. **Frequent Intentional Compaction (FIC)** - Deliberately structure how context is fed throughout development, keeping utilization at 40-60%
3. **Hierarchy of Effort** - Bad research → thousands of bad code lines; bad plan → hundreds of bad lines; bad code → fixable
4. **Human review at highest leverage** - Review research and plans, not code diffs
5. **Mental alignment > raw productivity** - Code review is about team understanding, not catching bugs

## Core Workflow: Research → Plan → Implement

### Research Phase
- Understand system architecture and information flow
- Identify relevant files and dependencies
- Use sub-agents for codebase exploration (reduces parent context burden)
- Output: research document with findings

### Plan Phase
- Detail every change: files affected, code snippets, verification steps
- Human review checkpoint here (highest leverage)
- Output: step-by-step implementation plan

### Implementation Phase
- Execute plan phase-by-phase
- Continuously update progress file
- Keep context under 40% utilization
- If implementation fails, revisit the plan (not the code)

## Compaction Techniques

### Intentional Compaction
- When approaching context limits, write a specific progress file
- This file onboards the next agent with only relevant information
- Never use generic compaction - always craft deliberately

### Sub-Agent Pattern
- Delegate specific tasks (file search, tracing, analysis) to sub-agents
- Parent receives concise results without full search context
- Reduces context burden significantly

### Backpressure Pattern
- Swallow all test/build/lint output on success (replace with ✓)
- Only expose full output on failure
- Use `failFast` flags (`pytest -x`, `jest --bail`)
- Deterministic truncation beats model-driven decisions
- Anti-pattern: piping to `/dev/null` or `head -n 50`

## Context Window Optimization Rules

| Dimension | Description |
|-----------|-------------|
| **Correctness** | Information must be accurate |
| **Completeness** | Include all necessary details |
| **Size** | Minimize noise and irrelevant data |
| **Trajectory** | Context should guide toward the goal |

## Results & Metrics

- 35k LOC of working Rust code shipped in 7 hours (2 people)
- Successfully worked in 300k LOC Rust codebase
- Features estimated at 3-5 days each completed same day
- Context utilization target: under 40%

## Critical Insight

> "You have to engage with your task when you're doing this or it WILL NOT WORK."

This is engineering craft, not magic prompts. Human expertise remains essential for complex problems.
