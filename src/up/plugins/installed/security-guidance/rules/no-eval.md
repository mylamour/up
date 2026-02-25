---
name: no-eval
event: post_tool_use
pattern: "eval\\s*\\("
action: warn
confidence: 95
---
Dangerous use of eval() detected. eval() can execute arbitrary code and is a common injection vector. Use ast.literal_eval() for safe parsing or find an alternative approach.
