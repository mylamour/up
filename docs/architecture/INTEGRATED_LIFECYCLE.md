# Integrated Software Lifecycle Architecture

**Created**: 2026-02-03
**Status**: 📋 Draft

---

## Overview

This document describes the integrated, event-driven architecture that connects all up-cli systems for automatic knowledge capture and continuous improvement.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        UP-CLI Integrated Lifecycle                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐           │
│  │   DOCS   │◄───►│  LEARN   │◄───►│   LOOP   │◄───►│  MEMORY  │           │
│  │  System  │     │  System  │     │  System  │     │  System  │           │
│  └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘           │
│       │                │                │                │                  │
│       └────────────────┴────────────────┴────────────────┘                  │
│                                   │                                          │
│                           ┌───────┴───────┐                                  │
│                           │  Event Bridge  │                                  │
│                           └───────┬───────┘                                  │
│                                   │                                          │
│       ┌───────────────────────────┼───────────────────────────┐             │
│       ▼                           ▼                           ▼             │
│  ┌─────────┐               ┌─────────┐               ┌─────────┐           │
│  │   Git   │               │  Files  │               │   AI    │           │
│  │ Watcher │               │ Watcher │               │ Session │           │
│  └─────────┘               └─────────┘               └─────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Event-Driven Architecture

### Core Events

| Event | Source | Triggers |
|-------|--------|----------|
| `git.commit` | Git hook / Watcher | Memory index, Docs update |
| `git.push` | Git hook | Release notes check |
| `file.changed` | File watcher | Memory re-index, Learn trigger |
| `session.start` | AI session | Memory session start |
| `session.end` | AI session / Timeout | Memory save, Handoff update |
| `task.complete` | Product loop | Memory record, Docs update |
| `error.occurred` | Product loop | Memory record, Learn trigger |
| `learning.discovered` | Learn system | Memory record, Docs update |
| `decision.made` | User / AI | Memory record, ADR creation |

### Event Flow

```
User Action / Git Change / File Change
              │
              ▼
        ┌─────────────┐
        │ Event Bridge │
        └──────┬──────┘
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│ Docs  │ │ Learn │ │ Loop  │ │Memory │
│Update │ │Trigger│ │ State │ │Record │
└───────┘ └───────┘ └───────┘ └───────┘
```

---

## System Integration

### 1. Product Loop → Memory Integration

When product loop completes a task:

```python
# In product loop COMMIT phase
def on_task_complete(task, result):
    # 1. Update loop state
    state.complete_task(task.id)
    
    # 2. Record to memory (AUTOMATIC)
    memory.record_task(task.title)
    memory.record_files(result.files_modified)
    
    # 3. If learning discovered
    if result.learnings:
        for learning in result.learnings:
            memory.record_learning(learning)
    
    # 4. Update docs/CONTEXT.md (AUTOMATIC)
    docs.update_context(
        recent_changes=[task.title],
        files_modified=result.files_modified
    )
```

### 2. Product Loop → Memory on Error

When product loop encounters error:

```python
def on_error(error, context):
    # 1. Record error to memory
    memory.record_error(
        error=str(error),
        context=context,
        solution=None  # To be filled when fixed
    )
    
    # 2. Search for similar past errors
    similar = memory.search(str(error), entry_type="error")
    if similar:
        suggest_solution(similar[0].metadata.get("solution"))
    
    # 3. If repeated error, trigger learning
    if count_similar_errors(error) >= 2:
        events.emit("learning.needed", topic=error_type(error))
```

### 3. Git Commit → Automatic Indexing

```python
# Git post-commit hook
def on_git_commit(commit):
    # 1. Index commit to memory
    memory.index_commit(commit)
    
    # 2. Update CONTEXT.md
    docs.add_recent_change(commit.message)
    
    # 3. Check if learning triggers apply
    if commit_touches_patterns(commit):
        events.emit("learning.suggested", 
                    topic=detect_topic(commit))
```

### 4. Session Management → Automatic Handoff

```python
# Session lifecycle
def on_session_end(reason="user"):
    # 1. Generate session summary
    summary = generate_session_summary()
    
    # 2. Save to memory
    memory.end_session(summary)
    
    # 3. Update handoff document (AUTOMATIC)
    docs.update_handoff(
        summary=summary,
        next_steps=suggest_next_steps(),
        files_modified=session.files_modified
    )
    
    # 4. Update CONTEXT.md
    docs.update_context_status()
```

### 5. Learn System → Memory & Docs

```python
def on_learning_complete(research_results):
    # 1. Save patterns to memory
    for pattern in research_results.patterns:
        memory.record_learning(
            f"Pattern: {pattern.name} - {pattern.description}"
        )
    
    # 2. Update insights docs
    docs.update_patterns(research_results.patterns)
    
    # 3. If gaps found, create PRD
    if research_results.gaps:
        prd = generate_prd(research_results.gaps)
        save_prd(prd)
        
        # Notify that tasks are ready
        events.emit("tasks.ready", source="learn")
```

---

## Auto-Update Triggers Matrix

| Trigger | Memory | Docs | Learn | Loop |
|---------|--------|------|-------|------|
| Git commit | ✅ Index | ✅ CONTEXT | - | - |
| File changed | ✅ Re-index | - | ⚡ Maybe | - |
| Task complete | ✅ Record | ✅ CONTEXT | - | ✅ State |
| Task failed | ✅ Error | - | ⚡ If repeated | ✅ Circuit |
| Session start | ✅ Start | - | - | - |
| Session end | ✅ Summary | ✅ Handoff | - | - |
| Error fixed | ✅ Solution | - | ✅ Pattern | - |
| Research done | ✅ Patterns | ✅ Insights | ✅ PRD | - |
| Milestone | ✅ Record | ✅ Changelog | - | ✅ Commit |

Legend: ✅ = Always, ⚡ = Conditional, - = Not applicable

---

## Background Automation Options

### Option 1: Git Hooks (Recommended - No Daemon)

```bash
# .git/hooks/post-commit
#!/bin/bash
up memory sync --commits-only &
up docs update-context &
```

**Pros**: No background process, triggers on actual changes
**Cons**: Only catches git events, not file saves

### Option 2: File Watcher Daemon

```bash
# Start watcher
up watch start

# Watches for:
# - Git commits
# - File changes in src/, docs/
# - Session activity (no input for 30 min = session end)
```

**Pros**: Catches everything, real-time
**Cons**: Background process, resource usage

### Option 3: Hybrid (Recommended)

```bash
# Git hooks for commit events (always)
up init --hooks

# Optional watcher for active development
up watch start
```

---

## Proposed New Commands

| Command | Description |
|---------|-------------|
| `up watch start` | Start background watcher |
| `up watch stop` | Stop background watcher |
| `up watch status` | Show watcher status |

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Complete Data Flow                             │
└─────────────────────────────────────────────────────────────────────────┘

 User Request
      │
      ▼
┌─────────────┐     ┌─────────────┐
│ up learn    │────►│ Research    │
│ auto        │     │ Web/Repos   │
└─────────────┘     └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ patterns.md │──────┐
                    │ gaps.md     │      │
                    └──────┬──────┘      │
                           │             │
                           ▼             │
                    ┌─────────────┐      │
                    │  prd.json   │      │
                    └──────┬──────┘      │
                           │             │
                           ▼             │
┌─────────────┐     ┌─────────────┐      │    ┌─────────────┐
│ up start    │────►│ Product     │      │    │   Memory    │
│             │     │ Loop        │      │    │   System    │
└─────────────┘     └──────┬──────┘      │    └──────▲──────┘
                           │             │           │
              ┌────────────┼────────────┐│           │
              ▼            ▼            ▼│           │
        ┌─────────┐  ┌─────────┐  ┌─────────┐       │
        │ Execute │  │ Verify  │  │ Commit  │       │
        │ Task    │  │ Tests   │  │ Changes │       │
        └────┬────┘  └────┬────┘  └────┬────┘       │
             │            │            │             │
             │            │            ▼             │
             │            │     ┌─────────────┐      │
             │            │     │ Git Commit  │──────┤
             │            │     └──────┬──────┘      │
             │            │            │             │
             ▼            ▼            ▼             │
        ┌─────────────────────────────────────┐     │
        │         Auto-Record to Memory        │─────┘
        │  • Task completed                    │
        │  • Files modified                    │
        │  • Errors encountered                │
        │  • Learnings discovered              │
        └─────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │         Auto-Update Docs            │
        │  • CONTEXT.md                       │
        │  • handoff/LATEST.md               │
        │  • changelog/ (on milestone)        │
        └─────────────────────────────────────┘
```

---

## Implementation Priority

### Phase 1: Core Integration (High Priority)

1. **Product Loop → Memory**: Auto-record tasks, errors, files
2. **Git Hooks**: Auto-index on commit
3. **Session Auto-Save**: Detect session end, save handoff

### Phase 2: Docs Auto-Update (Medium Priority)

4. **CONTEXT.md Auto-Update**: Keep current state fresh
5. **Handoff Auto-Generate**: Create on session end
6. **Changelog Auto-Entry**: On milestone commits

### Phase 3: Advanced Automation (Nice to Have)

7. **File Watcher Daemon**: Real-time monitoring
8. **Learn Auto-Trigger**: When patterns detected
9. **Cross-Session Memory**: Semantic retrieval in new sessions

---

## Configuration

```json
// .up/config.json
{
  "automation": {
    "memory": {
      "auto_index_commits": true,
      "auto_record_tasks": true,
      "auto_record_errors": true,
      "session_timeout_minutes": 30
    },
    "docs": {
      "auto_update_context": true,
      "auto_update_handoff": true,
      "auto_changelog_on_milestone": true
    },
    "learn": {
      "auto_trigger_on_repeated_error": true,
      "auto_trigger_threshold": 2
    },
    "hooks": {
      "post_commit": true,
      "pre_push": false
    }
  }
}
```

---

## Summary

The integrated lifecycle connects all systems through an event-driven architecture:

1. **Memory** captures everything automatically
2. **Docs** stay current without manual updates  
3. **Learn** triggers when patterns suggest improvement
4. **Loop** records progress to memory and docs

No background daemon required for basic functionality - git hooks provide the trigger points. Optional watcher available for real-time monitoring.
