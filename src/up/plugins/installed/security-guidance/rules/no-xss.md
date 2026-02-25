---
name: no-xss
event: post_tool_use
pattern: "dangerouslySetInnerHTML|innerHTML\\s*="
action: warn
confidence: 90
---
Potential XSS vulnerability. dangerouslySetInnerHTML and innerHTML bypass React/DOM sanitization. Sanitize user input before rendering or use safe alternatives.
