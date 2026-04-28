"""
CLI module for nanocode.

Provides the interactive REPL interface, terminal I/O handling,
and command processing.
"""

from nanocode.cli.main import Repl, main as cli_main
from nanocode.cli.io import Terminal, Colors
from nanocode.cli.commands import register_command, get_commands, is_command, execute_command

__all__ = [
    "Repl",
    "cli_main",
    "Terminal",
    "Colors",
    "register_command",
    "get_commands",
    "is_command",
    "execute_command",
]
