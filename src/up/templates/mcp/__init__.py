"""MCP (Model Context Protocol) server templates."""

from pathlib import Path
from datetime import date


def create_mcp_config(target_dir: Path, ai_target: str, force: bool = False) -> None:
    """Create MCP server configuration files.
    
    Creates:
    - .mcp/config.json - MCP server configuration
    - .mcp/tools/ - Custom tool definitions
    """
    mcp_dir = target_dir / ".mcp"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    
    _create_mcp_config_json(mcp_dir, force)
    _create_mcp_tools_dir(mcp_dir, force)
    _create_mcp_readme(mcp_dir, force)


def _write_file(path: Path, content: str, force: bool) -> None:
    """Write file if it doesn't exist or force is True."""
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _create_mcp_config_json(mcp_dir: Path, force: bool) -> None:
    """Create MCP configuration file."""
    content = """{
  "$schema": "https://modelcontextprotocol.io/schema/config.json",
  "version": "1.0.0",
  "servers": {
    "project-tools": {
      "description": "Project-specific tools for AI assistants",
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {},
      "tools": [
        "project_status",
        "run_tests",
        "lint_code",
        "search_code"
      ]
    }
  },
  "resources": {
    "docs": {
      "uri": "file://./docs/",
      "description": "Project documentation"
    },
    "context": {
      "uri": "file://./docs/CONTEXT.md",
      "description": "Current project context"
    }
  },
  "prompts": {
    "project-overview": {
      "description": "Get a quick project overview",
      "template": "Read docs/CONTEXT.md and provide a summary of the current project state."
    }
  }
}
"""
    _write_file(mcp_dir / "config.json", content, force)


def _create_mcp_tools_dir(mcp_dir: Path, force: bool) -> None:
    """Create MCP tools directory with sample tools."""
    tools_dir = mcp_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    
    # Project status tool
    status_tool = """{
  "name": "project_status",
  "description": "Get current project status including loop state and circuit breakers",
  "inputSchema": {
    "type": "object",
    "properties": {
      "verbose": {
        "type": "boolean",
        "description": "Include detailed information",
        "default": false
      }
    }
  }
}
"""
    _write_file(tools_dir / "project_status.json", status_tool, force)
    
    # Run tests tool
    tests_tool = """{
  "name": "run_tests",
  "description": "Run project tests with optional filtering",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Test file or directory path"
      },
      "pattern": {
        "type": "string",
        "description": "Test name pattern to match"
      },
      "verbose": {
        "type": "boolean",
        "default": false
      }
    }
  }
}
"""
    _write_file(tools_dir / "run_tests.json", tests_tool, force)
    
    # Lint code tool
    lint_tool = """{
  "name": "lint_code",
  "description": "Run linter on specified files or directories",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "File or directory to lint"
      },
      "fix": {
        "type": "boolean",
        "description": "Automatically fix issues",
        "default": false
      }
    }
  }
}
"""
    _write_file(tools_dir / "lint_code.json", lint_tool, force)
    
    # Search code tool
    search_tool = """{
  "name": "search_code",
  "description": "Search for patterns in the codebase",
  "inputSchema": {
    "type": "object",
    "properties": {
      "pattern": {
        "type": "string",
        "description": "Search pattern (regex supported)"
      },
      "file_pattern": {
        "type": "string",
        "description": "File glob pattern to search",
        "default": "**/*"
      },
      "context_lines": {
        "type": "integer",
        "description": "Number of context lines",
        "default": 2
      }
    },
    "required": ["pattern"]
  }
}
"""
    _write_file(tools_dir / "search_code.json", search_tool, force)


def _create_mcp_readme(mcp_dir: Path, force: bool) -> None:
    """Create MCP README with usage instructions."""
    content = """# MCP (Model Context Protocol) Configuration

This directory contains MCP server configuration for enhanced AI assistant integration.

## Overview

MCP provides a standardized way to expose tools, resources, and prompts to AI assistants
like Claude and Cursor.

## Structure

```
.mcp/
├── config.json      # Main MCP configuration
├── tools/           # Tool definitions
│   ├── project_status.json
│   ├── run_tests.json
│   ├── lint_code.json
│   └── search_code.json
└── README.md        # This file
```

## Configuration

### config.json

The main configuration file defines:

- **servers**: MCP server definitions
- **resources**: Read-only data sources
- **prompts**: Pre-defined prompt templates

### Tools

Each tool in `tools/` is a JSON file with:

- `name`: Tool identifier
- `description`: What the tool does
- `inputSchema`: JSON Schema for parameters

## Usage with Claude Code

Claude Code automatically detects MCP configuration.
Tools become available as `/tool_name` commands.

## Usage with Cursor

Add to your Cursor settings:

```json
{
  "mcp.servers": {
    "project": {
      "configPath": ".mcp/config.json"
    }
  }
}
```

## Implementing Tool Handlers

Create a Python MCP server:

```python
from mcp import Server, Tool

server = Server("project-tools")

@server.tool("project_status")
async def project_status(verbose: bool = False):
    # Implementation
    return {"status": "healthy"}

if __name__ == "__main__":
    server.run()
```

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/docs)
- [MCP Python SDK](https://github.com/anthropics/mcp-python-sdk)
"""
    _write_file(mcp_dir / "README.md", content, force)


def create_mcp_server_stub(target_dir: Path, force: bool = False) -> None:
    """Create a stub MCP server implementation."""
    content = '''#!/usr/bin/env python3
"""
MCP Server for Project Tools

A Model Context Protocol server that provides project-specific tools
to AI assistants.

Usage:
    python -m mcp_server

Or install as a package and run:
    up-mcp-server
"""

import json
import subprocess
from pathlib import Path
from typing import Any


class MCPServer:
    """Simple MCP server implementation."""
    
    def __init__(self, workspace: Path = None):
        self.workspace = workspace or Path.cwd()
        self.tools = {
            "project_status": self.project_status,
            "run_tests": self.run_tests,
            "lint_code": self.lint_code,
            "search_code": self.search_code,
        }
    
    async def project_status(self, verbose: bool = False) -> dict:
        """Get project status."""
        status = {"healthy": True, "systems": {}}
        
        # Check loop state
        loop_file = self.workspace / ".loop_state.json"
        if loop_file.exists():
            try:
                data = json.loads(loop_file.read_text())
                status["systems"]["loop"] = {
                    "iteration": data.get("iteration", 0),
                    "phase": data.get("phase", "UNKNOWN"),
                }
            except json.JSONDecodeError:
                status["systems"]["loop"] = {"error": "Invalid state"}
        
        # Check context budget
        context_file = self.workspace / ".claude/context_budget.json"
        if context_file.exists():
            try:
                data = json.loads(context_file.read_text())
                status["systems"]["context"] = {
                    "usage_percent": data.get("usage_percent", 0),
                    "status": data.get("status", "OK"),
                }
            except json.JSONDecodeError:
                status["systems"]["context"] = {"error": "Invalid state"}
        
        if verbose:
            status["workspace"] = str(self.workspace)
            status["initialized"] = (self.workspace / ".claude").exists()
        
        return status
    
    async def run_tests(
        self,
        path: str = None,
        pattern: str = None,
        verbose: bool = False
    ) -> dict:
        """Run tests."""
        cmd = ["pytest"]
        
        if path:
            cmd.append(path)
        
        if pattern:
            cmd.extend(["-k", pattern])
        
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test timeout"}
        except FileNotFoundError:
            return {"success": False, "error": "pytest not found"}
    
    async def lint_code(self, path: str = None, fix: bool = False) -> dict:
        """Run linter."""
        cmd = ["ruff", "check"]
        
        if path:
            cmd.append(path)
        else:
            cmd.append(".")
        
        if fix:
            cmd.append("--fix")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
            }
        except FileNotFoundError:
            return {"success": False, "error": "ruff not found"}
    
    async def search_code(
        self,
        pattern: str,
        file_pattern: str = "**/*",
        context_lines: int = 2
    ) -> dict:
        """Search code for pattern."""
        cmd = [
            "rg",  # ripgrep
            "-n",  # line numbers
            f"-C{context_lines}",  # context
            "-g", file_pattern,
            pattern,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            matches = []
            if result.stdout:
                for line in result.stdout.strip().split("\\n"):
                    matches.append(line)
            
            return {
                "success": True,
                "match_count": len([m for m in matches if ":" in m]),
                "matches": matches[:100],  # Limit results
            }
        except FileNotFoundError:
            return {"success": False, "error": "ripgrep not found"}
    
    async def handle_request(self, request: dict) -> dict:
        """Handle incoming MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "tools/list":
            return {
                "tools": [
                    {"name": name, "description": func.__doc__}
                    for name, func in self.tools.items()
                ]
            }
        
        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            if tool_name in self.tools:
                result = await self.tools[tool_name](**tool_args)
                return {"result": result}
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        
        return {"error": f"Unknown method: {method}"}


async def main():
    """Run MCP server."""
    import sys
    
    server = MCPServer()
    
    # Simple stdin/stdout protocol for demonstration
    # In production, use the official MCP SDK
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = await server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON"}), flush=True)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''
    _write_file(target_dir / "mcp_server.py", content, force)
