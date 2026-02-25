"""Main CLI entry point for up."""

import click
from rich.console import Console

from up import __version__
from up.commands.init import init_cmd
from up.commands.new import new_cmd
from up.commands.status import status_cmd
from up.learn import learn_cmd
from up.commands.start import start_cmd
from up.commands.memory import memory_cmd
from up.commands.vibe import save_cmd, reset_cmd, diff_cmd
from up.commands.done import done_cmd
from up.commands.agent import agent as agent_group
from up.commands.provenance import provenance as provenance_group
from up.commands.review import review_cmd
from up.commands.plugin import plugin_group
from up.commands.sync_config import sync_config_cmd

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="up")
def main():
    """up - Verifiable, observable AI-assisted development.

    Build tools using vibe coding with safety rails, resulting in
    stable, high-performance, and modern software engineering.
    
    \b
    Setup:
      up init                 Initialize in existing project
      up new <name>           Create new project
    
    \b
    Safety:
      up save                 Checkpoint before AI work
      up diff                 Review AI changes
      up reset                Restore to checkpoint
    
    \b
    Workflow:
      up start                Start the product loop
      up done                 Mark task as completed
    
    \b
    Quality:
      up review               AI adversarial code review
      up status               Show system health
    
    \b
    Context:
      up memory search <q>    Search across sessions
      up memory record        Record learnings/decisions
      up memory status        Memory statistics
    
    \b
    Agents:
      up agent spawn <name>   Create parallel agent
      up agent merge <name>   Merge agent work
    
    \b
    Learning:
      up learn                Analyze and generate PRD
    
    \b
    Tracing:
      up provenance show      View AI operation history
    """
    pass


# Project commands
main.add_command(init_cmd, name="init")
main.add_command(new_cmd, name="new")
main.add_command(status_cmd, name="status")

# Safety rails
main.add_command(start_cmd, name="start")
main.add_command(save_cmd, name="save")
main.add_command(reset_cmd, name="reset")
main.add_command(diff_cmd, name="diff")
main.add_command(done_cmd, name="done")

# Quality
main.add_command(review_cmd, name="review")
main.add_command(provenance_group, name="provenance")

# Context & agents
main.add_command(memory_cmd, name="memory")
main.add_command(agent_group, name="agent")
main.add_command(learn_cmd, name="learn")

# Plugins
main.add_command(plugin_group, name="plugin")

# Config sync
main.add_command(sync_config_cmd, name="sync")


if __name__ == "__main__":
    main()
