# Function Design Patterns in Security Analysis Tools

> Research findings on function analysis patterns from leading security tools
> Date: 2026-01-28

## Table of Contents

1. [Overview](#overview)
2. [CodeQL Patterns](#codeql-patterns)
3. [Semgrep Patterns](#semgrep-patterns)
4. [Joern Code Property Graph](#joern-code-property-graph)
5. [Taint Analysis Patterns](#taint-analysis-patterns)
6. [Pipeline Architecture Patterns](#pipeline-architecture-patterns)
7. [Key Takeaways](#key-takeaways)

---

## Overview

This research examines function design patterns used by leading security analysis tools to detect vulnerabilities. The focus is on architectural approaches that can be applied to improve the AI Code Auditor.

### Tools Researched

| Tool | Approach | Key Strength |
|------|----------|--------------|
| CodeQL | Query-based semantic analysis | Data flow tracking |
| Semgrep | Pattern matching with AST | Fast, customizable rules |
| Joern | Code Property Graphs | Unified code representation |

---

## CodeQL Patterns

### Architecture: Code as Data

CodeQL converts source code into a **relational database** containing facts about program elements:
- Classes, functions, variables
- Control structures and flow
- Type information

### Key Design Patterns

**1. Source-Sink-Sanitizer Model**
```
Source (untrusted input) → Propagation → Sink (sensitive operation)
                              ↓
                         Sanitizer (neutralizes taint)
```

**2. Interprocedural Data Flow**
- Tracks data movement across function boundaries
- Identifies if untrusted data reaches dangerous functions
- Recognizes proper sanitization in the flow path

**3. Query-Based Detection**
- Declarative QL queries interrogate the code database
- Queries express complex relationships and predicates
- Example: "Find all functions where user input reaches SQL execution without sanitization"

### Benefits
- Semantic understanding reduces false positives
- Can recognize conditional guards and sanitization
- Supports custom query development

---

## Semgrep Patterns

### Architecture: Semantic Grep

Semgrep combines text searching with code structure understanding through AST analysis.

### Key Design Patterns

**1. AST-Based Pattern Matching**
```
Source Code → Parser → AST
Rule (Query) → Parser → Query AST
Query AST matches against Source AST → Findings
```

**2. Rule-Based System**
- YAML-based rule definitions
- Pattern syntax resembles actual code
- Supports boolean composition of patterns

**3. Taint Mode for Data Flow**
- Tracks data from sources to sinks
- Configurable propagators and sanitizers
- Cross-function analysis in enterprise version

### Design Principles
- Lightweight and fast execution
- No compilation required
- Language-agnostic pattern syntax where possible

---

## Joern Code Property Graph

### Architecture: Unified Graph Representation

Joern creates a **Code Property Graph (CPG)** that unifies:
- Abstract Syntax Trees (AST)
- Control Flow Graphs (CFG)
- Program Dependence Graphs (PDG)

### Key Design Patterns

**1. Graph-Based Querying**
```scala
// Find all call sites to vulnerable function
cpg.call.name("strcpy").l

// Track data flow from source to sink
cpg.method("getUserInput").reachableBy(cpg.call.name("system"))
```

**2. Call Site Analysis**
- Identifies all call sites with incoming/outgoing edges
- Detects method invocation frequency
- Finds recursive calls and invocation conditions

**3. Backward Reachability**
- Traces data flow backwards from sinks
- Identifies all possible sources for a given sink
- Useful for understanding attack surface

### Benefits
- Single queryable structure for multiple analyses
- Supports complex pattern discovery
- Extensible query language (Scala-based)

---

## Taint Analysis Patterns

### Core Concepts

| Concept | Definition | Example |
|---------|------------|---------|
| **Source** | Origin of untrusted data | User input, network requests, file reads |
| **Sink** | Sensitive operation | SQL queries, command execution, file writes |
| **Sanitizer** | Neutralizes tainted data | Input validation, encoding, escaping |
| **Propagator** | Transfers taint through operations | String concatenation, array access |

### Design Pattern: Explicit Configuration

```python
# Pattern: Define sources, sinks, sanitizers explicitly
taint_config = {
    "sources": [
        {"function": "request.get", "returns": True},
        {"function": "input", "returns": True},
    ],
    "sinks": [
        {"function": "execute_sql", "args": [0]},
        {"function": "os.system", "args": [0]},
    ],
    "sanitizers": [
        {"function": "escape_sql", "args": [0], "returns": True},
        {"function": "shlex.quote", "args": [0], "returns": True},
    ]
}
```

### Best Practices

1. **Context-Specific Sanitizers**: HTML encoding prevents XSS but not SQL injection
2. **Field Sensitivity**: Track taint for different object fields separately
3. **Interprocedural Tracking**: Follow data across function boundaries
4. **Defense in Depth**: Combine taint analysis with other techniques

---

## Pipeline Architecture Patterns

### Pattern: Modular Analysis Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Parser    │ →  │  Analyzer   │ →  │  Reporter   │
│  (AST Gen)  │    │  (Rules)    │    │  (Output)   │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Design Principles

**1. Stage Isolation**
- Each stage has single responsibility
- Stages communicate through well-defined interfaces
- Failures in one stage don't crash the pipeline

**2. Composability**
- Stages can be reordered or replaced
- New stages can be added without disruption
- Supports parallel execution where possible

**3. Error Accumulation**
- Don't fail fast on analysis errors
- Collect all findings and errors
- Report comprehensive results

---

## Key Takeaways

### Patterns to Adopt

1. **Source-Sink-Sanitizer Model**: Explicit configuration of taint tracking
2. **Graph-Based Representation**: Unified structure for multiple analyses
3. **Query-Based Detection**: Declarative rules for vulnerability patterns
4. **Pipeline Architecture**: Modular, composable analysis stages
5. **Error Accumulation**: Graceful degradation on failures

### Implementation Recommendations

| Pattern | Current State | Recommendation |
|---------|---------------|----------------|
| Taint Config | Hardcoded | Move to configurable YAML |
| Node Architecture | LangGraph nodes | Add explicit interfaces |
| Query System | Ad-hoc patterns | Implement query DSL |
| Error Handling | Mixed | Standardize accumulation |

---

## Sources

- [GitHub CodeQL](https://github.com/github/codeql)
- [Semgrep Documentation](https://semgrep.dev/docs/writing-rules/overview)
- [Joern.io](https://joern.io)
- [Snyk Static Analysis](https://snyk.io)
- [SonarSource](https://sonarsource.com)
- [JetBrains Security](https://jetbrains.com)
