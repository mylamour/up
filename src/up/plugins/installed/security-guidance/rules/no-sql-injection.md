---
name: no-sql-injection
event: post_tool_use
pattern: "f['\"]\\s*(?:SELECT|INSERT|UPDATE|DELETE|DROP)\\b"
action: warn
confidence: 85
---
Possible SQL injection via f-string or string formatting in a SQL query. Use parameterized queries (placeholders) instead of string interpolation to prevent SQL injection attacks.
