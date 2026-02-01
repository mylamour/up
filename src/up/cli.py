"""Main CLI entry point for up."""

import click
from rich.console import Console

from up.commands.init import init_cmd
from up.commands.new import new_cmd

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="up")
def main():
    """up - AI-powered project scaffolding.

    Create projects with built-in docs, learn, and product-loop systems
    for Claude Code and Cursor AI.
    """
    pass


main.add_command(init_cmd, name="init")
main.add_command(new_cmd, name="new")


if __name__ == "__main__":
    main()
