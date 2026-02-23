# Gap Analysis: up-cli v0.5 → v1.0 (Revised)

**Generated**: 2026-02-23
**Revised**: Large-project focus — features stay, interface simplifies
**Based on**: Codebase audit + large-project vibe coding research

---

## Executive Summary

up-cli targets large software projects where vibe coding creates real problems: context loss, architectural debt, security gaps, accountability holes, and multi-agent coordination failures. The v0.5 internals address all 7 of these. The gap is not missing features — it's **too many commands exposing those features**.

**Quality Score: 7/10** — Right features, wrong interface.

---

## Gap 1: Command Surface Complexity (CRITICAL)

28 commands / 80+ options. Not "too many features" — too many *entry points*.

**Revised target**: 14 commands (not 10). Keep memory and agent as groups, but collapse them.

| Group | Current | v1.0 Target |
|-------|---------|-------------|
| memory | 11 subcommands | 3 (search, record, status) |
| agent | 4 subcommands | 2 (spawn, merge — cleanup auto) |
| branch | 4 subcommands | 0 (remove — git handles this) |
| provenance | 4 subcommands | 1 (show — list/stats fold into status) |
| standalone | dashboard, summarize, bisect, history, hooks, sync | 0 (remove or auto) |

## Gap 2: Core Loop Tests (CRITICAL)

`commands/start/` has ZERO tests. This is the product's main value path.

## Gap 3: PRD Schema Contract (HIGH)

No shared schema between learn (writer) and start (reader). Silent breakage.

## Gap 4: Duplicate Parallel Modules (HIGH)

`parallel.py` + `parallel_scheduler.py` overlap. One API needed.

## Gap 5: Fragile JSON Extraction (MEDIUM)

Bracket-depth matching breaks on brackets inside strings.

## Gap 6: Memory UX (MEDIUM)

Memory is the answer to context fragmentation — the #1 large-project problem. But 11 subcommands makes it unusable. Needs 3 commands max.

## Gap 7: Event System Wiring (LOW)

18 event types exist. For large projects, events connecting memory ↔ learn ↔ loop would be valuable. But handlers aren't wired yet. Low priority for v1.0 — wire 3-4 key events, not all 18.
