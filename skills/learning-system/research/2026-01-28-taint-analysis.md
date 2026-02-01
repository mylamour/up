# Research: Taint Analysis Implementations

> Source: Multiple (CodeQL, Semgrep, Joern, Industry Research)
> Date: 2026-01-28
> Relevance: high

## Summary

Taint analysis is a fundamental technique in static code analysis for identifying security vulnerabilities by tracking "tainted" data flow from sources to sinks. This research covers implementations in top security tools and emerging trends.

## Core Concepts

### The Taint Analysis Triad

| Component | Description | Example |
|-----------|-------------|---------|
| **Sources** | Origins of untrusted data | User input, HTTP params, file reads |
| **Sinks** | Dangerous operations | SQL queries, command execution, HTML output |
| **Sanitizers** | Data validation/transformation | Input escaping, type casting, validation |

### Data Flow vs Taint Tracking

- **Data Flow**: Tracks exact values through program
- **Taint Tracking**: Propagates "taint" through derived values (e.g., `y = x + 1` - if `x` is tainted, `y` is also tainted)

---

## Tool Implementations

### 1. CodeQL (GitHub)

**Architecture**: Query-based analysis using QL language

**Key Features**:
- Local vs Global data flow analysis
- Declarative query language
- Semantic code representation (not just AST)

**Implementation Pattern**:
```
DataFlow::ConfigSig interface
├── isSource(node) - Define taint sources
├── isSink(node) - Define dangerous sinks
└── isBarrier(node) - Define sanitizers
```

**Strengths**:
- Precise interprocedural analysis
- Strong type system in queries
- Extensive standard library models

**Limitations**:
- Computationally intensive for large codebases
- Requires compilation/build for some languages

---

### 2. Semgrep (Returntocorp)

**Architecture**: Pattern-based with taint mode extension

**YAML Rule Structure**:
```yaml
mode: taint
pattern-sources:
  - pattern: get_user_input(...)
pattern-sanitizers:
  - pattern: sanitize_input(...)
pattern-sinks:
  - pattern: html_output(...)
```

**Key Components**:
- `pattern-sources`: Entry points (supports `exact` option)
- `pattern-sinks`: Vulnerable functions (default `exact: true`)
- `pattern-sanitizers`: Cleaning functions
- `pattern-propagators`: Custom taint flow rules (Pro)

**Propagation Behaviors**:
- String concatenation propagates taint
- Function return values inherit taint from inputs
- Opaque functions assumed to propagate (Pro)

**Strengths**:
- Fast, lightweight analysis
- Easy rule authoring (YAML)
- Good for CI/CD integration

**Limitations**:
- OSS version limited interprocedural analysis
- Pro required for cross-file analysis

---

### 3. Joern (joernio)

**Architecture**: Code Property Graph (CPG) based analysis

**CPG Components**:
- Abstract Syntax Tree (AST)
- Control Flow Graph (CFG)
- Program Dependence Graph (PDG)

**Two-Phase Analysis**:
1. **Offline**: Static def-use chain analysis (over-tainting)
2. **Online**: Query-specific refinement with sources/sinks

**Key API**:
```scala
// Find taint flows from source to sink
sink.reachableByFlows(source)
```

**Terminology**:
- DIP (Data Initialization Point) = Source
- DEP (Data Egress Point) = Sink

**Strengths**:
- Language-agnostic intermediate representation
- Fuzzy parsing (works on incomplete code)
- Powerful Scala-based query language
- Inter-procedural analysis built-in

**Limitations**:
- External methods assumed to propagate all taint
- Higher false positive rate for soundness

---

## Emerging Trends (2025-2026)

### 1. AI-Powered Analysis
- Intent-aware AI to understand developer context
- Moving beyond rigid rule-based detection
- AI-suggested one-click fixes

### 2. Multi-Type Taint Sources
- Record multiple plausible source types upfront
- Resolve actual type based on usage context
- Reduces false positives in cryptography analysis

### 3. Contextual Analysis
- Track conditions under which data flows occur
- Distinguish malicious from benign paths
- Better handling of conditional sanitization

---

## Key Patterns

- **Graph Reachability**: All tools reduce taint checking to graph reachability
- **Layered Analysis**: Local (fast) → Global (thorough) analysis modes
- **Configurable Propagation**: Custom rules for framework-specific flows
- **Over-tainting for Soundness**: Better false positives than missed vulns

---

## Insights

- CodeQL's declarative approach enables precise, reusable vulnerability patterns
- Semgrep's YAML rules lower barrier to entry for security teams
- Joern's CPG provides most flexible foundation for custom analysis
- Two-phase (offline/online) analysis balances performance and precision
- AI integration is the next frontier for reducing false positives

---

## Code Examples

### Semgrep Taint Rule
```yaml
rules:
  - id: sql-injection
    mode: taint
    pattern-sources:
      - pattern: request.args.get(...)
    pattern-sanitizers:
      - pattern: escape_sql(...)
    pattern-sinks:
      - pattern: cursor.execute($QUERY, ...)
    message: "Potential SQL injection"
    severity: ERROR
```

### CodeQL Taint Query (Python)
```ql
import python
import semmle.python.dataflow.new.TaintTracking

class SqlInjectionConfig extends TaintTracking::Configuration {
  SqlInjectionConfig() { this = "SqlInjectionConfig" }

  override predicate isSource(DataFlow::Node source) {
    source instanceof RemoteFlowSource
  }

  override predicate isSink(DataFlow::Node sink) {
    exists(Call c | c.getFunc().(Attribute).getName() = "execute" |
      sink.asExpr() = c.getArg(0)
    )
  }
}
```

### Joern CPG Query (Scala)
```scala
// Find flows from HTTP input to SQL execution
val sources = cpg.call.name("request.*").argument
val sinks = cpg.call.name("execute").argument(0)
sinks.reachableByFlows(sources).p
```

---

## Sources

- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Semgrep Taint Mode](https://semgrep.dev/docs/writing-rules/data-flow/taint-mode)
- [Joern Documentation](https://joern.io/)
- [GitHub Blog](https://github.blog/)
- [Trail of Bits Blog](https://blog.trailofbits.com/)
