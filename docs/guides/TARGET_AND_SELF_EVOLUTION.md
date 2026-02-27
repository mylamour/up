# Target & Self-Evolution

**Updated**: 2026-02-27

This guide describes how the project stays aimed at a **final target** and **evolves itself** over time using a single north star, event-driven updates, and feedback loops.

---

## Final Target: One North Star

The project’s direction is defined in one place so every session and every agent can align to it:

| Artifact | Role |
|----------|------|
| **[docs/TARGET.md](../TARGET.md)** | North star: vision, success metrics, current focus |
| [Product Vision](../roadmap/vision/PRODUCT_VISION.md) | Full vision and problem statement |
| [Improvement Plan](../roadmap/IMPROVEMENT_PLAN.md) | Roadmap and sprint tasks |

**Use TARGET.md to:**

- Start a session: read it to know where the project is heading.
- Plan work: choose tasks that move the metrics (e.g. “iterations per feature”, “test coverage”).
- End a session: update CONTEXT or handoff so the next session knows progress toward the target.

Keep **Current Focus** in TARGET.md in sync with CONTEXT and the roadmap so the “next priority” is always clear.

---

## How the Project Self-Evolves

The system improves over time through several feedback loops.

### 1. Target → Context → Next session

- **CONTEXT.md** summarizes current state and points to [TARGET.md](../TARGET.md).
- **handoff/LATEST.md** is updated on task complete and session end with:
  - What was done and what changed.
  - **Suggested next steps (toward target)** from the PRD (pending tasks) plus “Review changes”, “Run tests”, and a link to TARGET.
- The next session (human or AI) reads handoff + TARGET and continues work aligned to the same goal.

### 2. Loop → Memory → Better next runs

- **Task complete / failure** events update state and (via EventBridge) can update docs and memory.
- **Memory** records errors and learnings; **auto_recall** and **memory hints** feed past solutions back into the loop.
- **Provenance** tracks what was tried and what passed, so the system can avoid repeating failed approaches.

So: each run leaves a trace; the next run uses that trace to get closer to the target (fewer iterations, fewer errors, better context).

### 3. Learning system → Analysis → PRD / improvement plan

- **Continuous learning** (e.g. every N task completions) can trigger `learn_self_improvement` and then `up sync` to refresh AI instructions.
- **`up learn`** (analyze, research, plan) produces or updates a PRD and improvement ideas.
- The **PRD** drives the product loop; pending tasks from the PRD are shown in handoff as “Suggested next steps (toward target)”.

So: analysis and learning feed into the same target (PRD + TARGET) and into the same handoff, keeping the project moving toward the final goal.

### 4. Metrics vs target

- **Success metrics** in TARGET.md (e.g. “iterations per feature 1–2”, “test coverage > 50%”) define what “done” looks like.
- **State** (e.g. in `.up/state.json`) holds completed/failed counts, rollbacks, and other run data.
- You can periodically compare state and logs to the metrics in TARGET and adjust **Current Focus** or the PRD so the next work closes the gap.

This is the “aim at the final target” loop: define target → run loop → measure → adjust focus and tasks → repeat.

---

## Putting It Together

```
TARGET.md (vision, metrics, focus)
       │
       ▼
CONTEXT.md ◄── updated on task complete
       │
       ▼
Product loop (PRD tasks, memory, provenance)
       │
       ├── task complete ──► handoff updated (next steps from PRD + TARGET link)
       ├── session end   ──► handoff updated
       ├── failures     ──► memory + circuit breaker
       └── every N tasks ──► continuous learning → sync
       │
       ▼
handoff/LATEST.md (suggested next steps toward target)
       │
       ▼
Next session: read TARGET + CONTEXT + handoff → continue toward target
```

---

## What You Can Do

1. **Keep TARGET up to date**  
   When the roadmap or priority changes, update **Current Focus** (and if needed, success metrics) in [TARGET.md](../TARGET.md).

2. **Use handoff every session**  
   Rely on handoff’s “Next steps (toward target)” so the next session doesn’t start from zero and stays aligned to the PRD and TARGET.

3. **Run the loop with a PRD**  
   Use a PRD (e.g. `prd.json`) so pending tasks are derived from the plan; they will automatically feed into handoff as suggested next steps.

4. **Use learn and sync**  
   Use `up learn` and continuous learning so analysis and improvements feed back into the same target and docs.

5. **Compare metrics to TARGET**  
   Periodically check state and outcomes against the success metrics in TARGET and adjust focus or tasks to close the gap.

---

## See Also

- [TARGET.md](../TARGET.md) — North star
- [CONTEXT.md](../CONTEXT.md) — Current state
- [Integrated Lifecycle](../architecture/INTEGRATED_LIFECYCLE.md) — Event-driven architecture
- [Product Vision](../roadmap/vision/PRODUCT_VISION.md) — Full vision
