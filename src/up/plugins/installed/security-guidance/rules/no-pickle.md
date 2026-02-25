---
name: no-pickle
event: post_tool_use
pattern: "pickle\\.loads?\\s*\\("
action: warn
confidence: 90
---
pickle deserialization of untrusted data can execute arbitrary code. Use json, msgpack, or other safe serialization formats for untrusted input.
