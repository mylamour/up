"""Main CLI entry point for up."""

import click
from rich.console import Console

from up.commands.init import init_cmd
from up.commands.new import new_cmd
from up.commands.status import status_cmd
from up.commands.learn import learn_cmd
from up.commands.summarize import summarize_cmd
from up.commands.dashboard import dashboard_cmd
from up.commands.start import start_cmd

console = Console()


@click.group()
@click.version_option(version="0.2.0", prog_name="up")
def main():
    """up - AI-powered project scaffolding.

    Create projects with built-in docs, learn, and product-loop systems
    for Claude Code and Cursor AI.
    
    \b
    Quick Start:
      up new my-project       Create new project
      up init                 Initialize in existing project
      up start                Start the product loop
      up status               Show system health
      up dashboard            Live health dashboard
      up learn auto           Analyze project for improvements
      up summarize            Summarize AI conversations
    
    \b
    Project Templates:
      up new api --template fastapi      FastAPI backend
      up new app --template nextjs       Next.js frontend
      up new lib --template python-lib   Python library
    """
    pass


main.add_command(init_cmd, name="init")
main.add_command(new_cmd, name="new")
main.add_command(start_cmd, name="start")
main.add_command(status_cmd, name="status")
main.add_command(dashboard_cmd, name="dashboard")
main.add_command(learn_cmd, name="learn")
main.add_command(summarize_cmd, name="summarize")


if __name__ == "__main__":
    main()
