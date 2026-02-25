---
name: no-hardcoded-secrets
event: post_tool_use
pattern: "(?:api_key|secret_key|password|token)\\s*=\\s*['\"][^'\"]{8,}['\"]"
action: warn
confidence: 80
---
Possible hardcoded secret detected. Store secrets in environment variables or a secrets manager, never in source code.
