"""up start - Product loop command package.

Split from the original 1125-line start.py into:
- command.py: CLI entry point and routing
- loop.py: AI and manual product loop execution
- helpers.py: State, task, checkpoint, and PRD utilities
- verification.py: Test/lint runners and git helpers
"""

from up.commands.start.command import start_cmd

__all__ = ["start_cmd"]
