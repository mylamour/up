"""Main CLI entry point for up."""

import click
from rich.console import Console

from up.commands.init import init_cmd
from up.commands.new import new_cmd
from up.commands.status import status_cmd
from up.learn import learn_cmd
from up.commands.summarize import summarize_cmd
from up.commands.dashboard import dashboard_cmd
from up.commands.start import start_cmd
from up.commands.memory import memory_cmd
from up.commands.sync import sync_cmd, hooks_cmd
from up.commands.vibe import save_cmd, reset_cmd, diff_cmd
from up.commands.agent import agent as agent_group
from up.commands.bisect import bisect_cmd, history_cmd
from up.commands.provenance import provenance as provenance_group
from up.commands.review import review_cmd
from up.commands.branch import branch as branch_group

console = Console()


@click.group()
@click.version_option(version="0.4.0", prog_name="up")
def main():
    """up - Verifiable, observable AI-assisted development.

    Build tools using vibe coding with safety rails, resulting in
    stable, high-performance, and modern software engineering.
    
    \b
    Quick Start:
      up new my-project       Create new project
      up init                 Initialize in existing project
      up start                Start the product loop
      up status               Show system health
    
    \b
    Vibe Coding Safety Rails:
      up save                 Checkpoint before AI work
      up reset                Restore to checkpoint
      up diff                 Review AI changes
      up start --parallel     Run multiple tasks in parallel
    
    \b
    Project Templates:
      up new api --template fastapi      FastAPI backend
      up new app --template nextjs       Next.js frontend
      up new lib --template python-lib   Python library
    
    \b
    Memory & Learning:
      up memory search <q>    Semantic search
      up memory record        Record learnings/decisions
      up learn                Auto-improve with AI
    
    \b
    System:
      up hooks                Install git hooks for auto-sync
      up sync                 Manual sync all systems
      up dashboard            Live monitoring
    """
    pass


# Project commands
main.add_command(init_cmd, name="init")
main.add_command(new_cmd, name="new")
main.add_command(status_cmd, name="status")

# Vibe coding commands
main.add_command(start_cmd, name="start")
main.add_command(save_cmd, name="save")
main.add_command(reset_cmd, name="reset")
main.add_command(diff_cmd, name="diff")
main.add_command(agent_group, name="agent")

# Debugging commands
main.add_command(bisect_cmd, name="bisect")
main.add_command(history_cmd, name="history")
main.add_command(provenance_group, name="provenance")
main.add_command(review_cmd, name="review")
main.add_command(branch_group, name="branch")

# System commands
main.add_command(sync_cmd, name="sync")
main.add_command(hooks_cmd, name="hooks")
main.add_command(dashboard_cmd, name="dashboard")

# Learning & memory
main.add_command(learn_cmd, name="learn")
main.add_command(memory_cmd, name="memory")
main.add_command(summarize_cmd, name="summarize")


if __name__ == "__main__":
    main()
