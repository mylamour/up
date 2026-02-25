---
name: no-todo-comments
event: post_tool_use
pattern: "TODO|FIXME|HACK|XXX"
action: warn
confidence: 60
---
TODO/FIXME comment detected. Consider resolving these before committing.
