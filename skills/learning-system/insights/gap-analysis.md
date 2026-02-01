# Gap Analysis

> Generated: 2026-01-28
> Updated: 2026-01-28
> Compared: Current implementation vs Industry Best Practices (CodeQL, Semgrep, Joern)
> Status: 5 Resolved, 3 Remaining

## Gap: Hardcoded Taint Configuration

| Aspect | Details |
|--------|---------|
| **Current State** | ✅ RESOLVED - `TaintConfig` Protocol and `YamlTaintConfig` implemented |
| **Best Practice** | CodeQL/Semgrep use configurable interfaces (DataFlow::ConfigSig, YAML rules) |
| **Impact** | High - Users can now customize for their frameworks via YAML |
| **Status** | ✅ Implemented in `taint_config.py` |

### Resolution
- `TaintConfig` Protocol with `is_source`, `is_sink`, `is_sanitizer` methods
- `YamlTaintConfig` class loads from YAML files
- Framework auto-detection in `taint_tracer.py`
- Default config with common patterns for Flask, Django, Express, FastAPI

---

## Gap: No Two-Phase Analysis

| Aspect | Details |
|--------|---------|
| **Current State** | ⏳ PARTIAL - `taint_cache.py` provides caching, but no persistent offline phase |
| **Best Practice** | Joern uses offline preprocessing + online query execution |
| **Impact** | Medium - Repeated analyses still rebuild call graphs |
| **Effort** | High |

### Progress
- `taint_cache.py` caches analysis results during session
- `call_graph.py` builds graphs but not persisted

### Remaining Work
- Add persistent storage for preprocessed call graphs
- Implement offline phase that runs once per codebase version

---

## Gap: Limited Language Support for Call Graph

| Aspect | Details |
|--------|---------|
| **Current State** | ✅ RESOLVED - `call_graph.py` now supports Python and JavaScript |
| **Best Practice** | Joern/CodeQL support multiple languages via language-agnostic CPG |
| **Impact** | High - Inter-procedural analysis now works for Python/JS |
| **Status** | ✅ Implemented in `call_graph.py` |

### Resolution
- `PythonCallGraphExtractor` class using tree-sitter-python
- `JavaScriptCallGraphExtractor` class using tree-sitter-javascript
- `build_call_graph()` function walks repo and extracts from both languages
- `CallGraph` dataclass with `find_path()` for BFS path finding
- Fallback regex extraction when tree-sitter unavailable

---

## Gap: No Configurable Propagation Rules

| Aspect | Details |
|--------|---------|
| **Current State** | ✅ RESOLVED - `PropagationRule` dataclass implemented |
| **Best Practice** | Semgrep allows custom `pattern-propagators` for framework-specific flows |
| **Impact** | Medium - Now supports custom propagation rules |
| **Status** | ✅ Implemented in `taint_config.py` |

### Resolution
- `PropagationRule` dataclass with `from_pattern`, `to_pattern`, `propagates_taint`
- Default rules for list.append, dict assignment, string format/concat, JSON ops
- `YamlTaintConfig.get_propagation_rules()` method

---

## Gap: No Layered Analysis Modes

| Aspect | Details |
|--------|---------|
| **Current State** | ✅ RESOLVED - `taint_mode` parameter supports local/global |
| **Best Practice** | CodeQL offers local (fast) vs global (thorough) modes |
| **Impact** | Low - Users can now trade speed for precision |
| **Status** | ✅ Implemented in `taint_tracer.py:98` |

### Resolution
```python
taint_mode = state.get("taint_mode", "local")
```

---

## Gap: Regex-Based Sanitizer Detection

| Aspect | Details |
|--------|---------|
| **Current State** | Sanitizers detected via regex + LLM semantic verification |
| **Best Practice** | Semantic analysis of sanitizer effectiveness |
| **Impact** | Medium - Combined approach reduces false positives |
| **Status** | ⏳ Partial - `semantic_sanitizer_check.py` exists |

### Progress
- Regex-based detection in `taint_config.py`
- LLM-based semantic verification in `semantic_sanitizer_check.py`

### Remaining Work
- Improve semantic analysis to verify sanitizer effectiveness
- Add context-aware sanitizer matching (e.g., HTML escape for XSS only)

---

## Summary

| Gap | Status | Priority |
|-----|--------|----------|
| Hardcoded Taint Configuration | ✅ Resolved | High |
| No Two-Phase Analysis | ⏳ Partial | High |
| Limited Language Support | ✅ Resolved | High |
| No Configurable Propagation | ✅ Resolved | Medium |
| No Layered Analysis Modes | ✅ Resolved | Low |
| Regex-Based Sanitizer Detection | ⏳ Partial | Medium |
| No Code Property Graph (CPG) | ❌ Open | High |
| No Query DSL | ❌ Open | Medium |

---

## New Gap: No Code Property Graph (CPG)

| Aspect | Details |
|--------|---------|
| **Current State** | Separate AST (tree-sitter) and call graph structures |
| **Best Practice** | Joern unifies AST + CFG + PDG into single queryable CPG |
| **Impact** | High - Complex queries require multiple data structures |
| **Effort** | High |

### Analysis
Current implementation has:
- AST parsing via tree-sitter in `parsers/`
- Call graph in `call_graph.py`
- No Control Flow Graph (CFG)
- No Program Dependence Graph (PDG)

### Recommendation
1. **Short-term**: Consider Joern integration for CPG queries
2. **Long-term**: Build lightweight CPG for Python/JS with CFG edges

---

## New Gap: No Query DSL for Vulnerability Patterns

| Aspect | Details |
|--------|---------|
| **Current State** | Hardcoded pattern matching in hunter nodes |
| **Best Practice** | CodeQL provides declarative QL for custom vulnerability queries |
| **Impact** | Medium - Users cannot define custom vulnerability patterns |
| **Effort** | High |

### Analysis
Current approach:
- Patterns defined in `hunter/patterns/*.py` as Python code
- `taint_config.py` uses regex patterns in YAML
- No declarative query language

### Recommendation
Consider implementing a lightweight query interface:
```yaml
# Example: Custom SQL injection query
query:
  from: source(type="user_input")
  to: sink(type="sql")
  where: not sanitized_by("parameterized_query")
```

---

### Remaining High-Priority Items

1. **Persistent Offline Preprocessing** - Cache call graphs between runs
2. **Code Property Graph** - Unified AST + CFG + PDG representation
3. **Context-Aware Sanitizer Verification** - Semantic analysis of sanitizer effectiveness