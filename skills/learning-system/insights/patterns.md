# Extracted Design Patterns

> Generated: 2026-01-28
> Updated: 2026-01-28
> Source: Taint Analysis Research + Function Design Patterns
> Patterns: 8
> Implementation Status: 4 Implemented, 4 Pending

## Pattern: Configuration-Based Taint Definition

- **Source**: CodeQL, Semgrep
- **Priority**: high
- **Status**: ✅ IMPLEMENTED

### Description
Define taint sources, sinks, and sanitizers through a configuration interface rather than hardcoding. This allows users to customize analysis for their specific frameworks.

### Implementation
```python
class TaintConfig(Protocol):
    def is_source(self, function: str, file_path: str, context: dict) -> bool: ...
    def is_sink(self, function: str, file_path: str, context: dict) -> bool: ...
    def is_sanitizer(self, function: str, file_path: str, context: dict) -> bool: ...
```

### Current Implementation
Located in `src/code_auditor/hunter/taint_config.py`:
- `TaintConfig` Protocol with `is_source`, `is_sink`, `is_sanitizer` methods
- `YamlTaintConfig` class for YAML-based configuration
- `SourcePattern`, `SinkPattern`, `SanitizerPattern` dataclasses
- Framework-specific configs in `hunter/configs/` directory
- Auto-detection via `detect_framework()` in `taint_tracer.py`

---

## Pattern: Two-Phase Analysis (Offline/Online)

- **Source**: Joern
- **Priority**: high
- **Status**: ⏳ PARTIAL (caching implemented, full offline phase pending)

### Description
Separate analysis into offline preprocessing (build graphs, compute def-use chains) and online query execution (user-specific source/sink queries).

### Implementation
1. **Offline**: Parse code → Build CPG → Compute reachability
2. **Online**: Load precomputed data → Apply user query → Return results

### Current Implementation
- `taint_cache.py` provides caching for taint analysis results
- `call_graph.py` builds call graphs but not cached between runs
- **Gap**: No persistent offline preprocessing phase

---

## Pattern: Layered Analysis Modes

- **Source**: CodeQL
- **Priority**: medium
- **Status**: ✅ IMPLEMENTED

### Description
Provide local (intra-procedural) and global (inter-procedural) analysis modes. Local is fast but less precise; global is thorough but slower.

### Current Implementation
Located in `taint_tracer.py:98`:
```python
taint_mode = state.get("taint_mode", "local")
```
- Supports `local` and `global` modes via state configuration
- Default is `local` for backward compatibility

---

## Pattern: Graph Reachability for Taint Checking

- **Source**: All tools (CodeQL, Semgrep, Joern)
- **Priority**: high
- **Status**: ✅ IMPLEMENTED

### Description
Reduce taint analysis to graph reachability problem. Build a data flow graph, then check if paths exist from sources to sinks.

### Current Implementation
Located in `call_graph.py`:
- `build_call_graph()` constructs call graph from source files
- Path finding from entry points to sinks in `taint_tracer.py`
- `TaintPath` dataclass tracks source → sink flows

---

## Pattern: Configurable Propagation Rules

- **Source**: Semgrep
- **Priority**: medium
- **Status**: ✅ IMPLEMENTED

### Description
Allow custom propagation rules for framework-specific data flows (e.g., taint spreading through collections, ORM models).

### Current Implementation
Located in `taint_config.py:142-176`:
- `PropagationRule` dataclass with `from_pattern`, `to_pattern`, `propagates_taint`
- Default rules for: list.append, dict assignment, string format/concat, JSON ops
- `YamlTaintConfig.get_propagation_rules()` and `propagates_taint()` methods

---

## Pattern: Code Property Graph (CPG)

- **Source**: Joern
- **Priority**: high
- **Status**: ❌ NOT IMPLEMENTED

### Description
Combine AST, CFG, and PDG into unified queryable graph structure. Enables complex queries across multiple code dimensions.

### Implementation
```
CPG = AST ∪ CFG ∪ PDG
- AST: Syntax structure
- CFG: Control flow edges
- PDG: Data + control dependencies
```

### Gap Analysis
- Current: Separate AST parsing (tree-sitter) and call graph
- Missing: Unified CPG representation
- Missing: Control flow graph construction
- Missing: Program dependence graph

### Recommendation
Consider integrating with Joern or building lightweight CPG for Python/JS.

---

## Pattern: Query-Based Detection (DSL)

- **Source**: CodeQL
- **Priority**: medium
- **Status**: ❌ NOT IMPLEMENTED

### Description
Declarative query language for expressing vulnerability patterns. Queries interrogate code database to find complex relationships.

### Implementation
```ql
// Example: Find SQL injection
from DataFlow::PathNode source, DataFlow::PathNode sink
where SqlInjectionConfig.hasFlowPath(source, sink)
select sink, source, "SQL injection from $@", source, "user input"
```

### Gap Analysis
- Current: Hardcoded pattern matching in nodes
- Missing: Query DSL for custom vulnerability patterns
- Missing: Reusable query library

### Recommendation
Consider implementing a lightweight query interface for custom patterns.

---

## Pattern: Modular Pipeline Architecture

- **Source**: All tools (CodeQL, Semgrep, Joern)
- **Priority**: high
- **Status**: ✅ IMPLEMENTED

### Description
Stage-isolated analysis pipeline with well-defined interfaces. Each stage has single responsibility, failures don't crash the pipeline.

### Current Implementation
- LangGraph-based workflow in `hunter/coordinator.py`
- Modular nodes in `hunter/nodes/` directory
- Error accumulation pattern (errors collected, not thrown)
- `HunterState` TypedDict for inter-node communication

---

## Summary

| Pattern | Priority | Status | Location |
|---------|----------|--------|----------|
| Configuration-Based Taint | High | ✅ Implemented | `taint_config.py` |
| Two-Phase Analysis | High | ⏳ Partial | `taint_cache.py` |
| Layered Analysis Modes | Medium | ✅ Implemented | `taint_tracer.py` |
| Graph Reachability | High | ✅ Implemented | `call_graph.py` |
| Configurable Propagation | Medium | ✅ Implemented | `taint_config.py` |
| Code Property Graph | High | ❌ Not Implemented | - |
| Query-Based Detection | Medium | ❌ Not Implemented | - |
| Modular Pipeline | High | ✅ Implemented | `hunter/coordinator.py` |

### Next Steps

1. **Complete Two-Phase Analysis**: Add persistent offline preprocessing
2. **Implement CPG**: Consider Joern integration or lightweight CPG
3. **Add Query DSL**: Enable custom vulnerability pattern queries
4. **Extend Language Support**: Add Python/JS call graph support