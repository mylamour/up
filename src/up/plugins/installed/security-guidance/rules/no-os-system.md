---
name: no-os-system
event: post_tool_use
pattern: "os\\.system\\s*\\("
action: warn
confidence: 90
---
os.system() is vulnerable to command injection. Use subprocess.run() with a list of arguments instead, which avoids shell interpretation.
