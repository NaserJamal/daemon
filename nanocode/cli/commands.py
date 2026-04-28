"""
CLI command registry for nanocode.

Provides a registry for slash commands like /q, /c, etc.
Easy to extend with new commands.

Example:
    >>> from nanocode.cli.commands import register_command
    >>> @register_command("/help", "Show help message")
    ... def show_help(args, repl):
    ...     print("Available commands...")
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from nanocode.cli.io import Colors, Terminal


class CommandHandler(Protocol):
    """
    Protocol for command handler functions.

    Handlers receive the command arguments and the REPL instance.
    """

    def __call__(
        self,
        args: list[str],
        repl: Any,  # Repl type defined in main.py to avoid circular import
    ) -> bool | None:
        """
        Handle a command.

        Args:
            args: Command arguments (first element is the command name).
            repl: The REPL instance.

        Returns:
            True to continue running, False to exit, None for default.
        """
        ...


# Command registry: name -> (description, help_text, handler)
_commands: dict[str, tuple[str, str, Callable[[list[str], Any], bool | None]]] = {}


def register_command(
    name: str,
    description: str,
    help_text: str = "",
) -> Callable[[CommandHandler], CommandHandler]:
    """
    Decorator to register a CLI command.

    Args:
        name: The command name (e.g., "/q").
        description: Short description for help.
        help_text: Detailed help text.

    Returns:
        Decorator function.

    Example:
        >>> @register_command("/mycmd", "Does something", "Usage: /mycmd arg")
        ... def my_handler(args, repl):
        ...     print("Command executed!")
        ...     return True
    """
    def decorator(handler: CommandHandler) -> CommandHandler:
        _commands[name] = (description, help_text, handler)
        return handler
    return decorator


def get_commands() -> dict[str, tuple[str, str]]:
    """
    Get all registered commands.

    Returns:
        Dictionary mapping command names to (description, help_text) tuples.
    """
    return {name: (desc, help_) for name, (desc, help_, _) in _commands.items()}


def execute_command(
    name: str,
    args: list[str],
    repl: Any,
) -> bool | None:
    """
    Execute a registered command.

    Args:
        name: The command name.
        args: Command arguments.
        repl: The REPL instance.

    Returns:
        True to continue, False to exit, None if command not found.
    """
    if name not in _commands:
        return None

    _, _, handler = _commands[name]
    return handler(args, repl)


def is_command(text: str) -> bool:
    """
    Check if text starts with a registered command.

    Args:
        text: Input text to check.

    Returns:
        True if text starts with a known command.
    """
    return any(text.startswith(cmd) for cmd in _commands)


# Built-in commands

@register_command(
    "/q",
    "Exit the REPL",
    "Usage: /q or /quit\nExits nanocode and ends the session.",
)
def cmd_quit(args: list[str], repl: Any) -> bool:
    """Handle the /q (quit) command."""
    return False


@register_command(
    "/quit",
    "Exit the REPL",
    "Usage: /q or /quit\nExits nanocode and ends the session.",
)
def cmd_quit_alias(args: list[str], repl: Any) -> bool:
    """Handle the /quit command (alias for /q)."""
    return False


@register_command(
    "/exit",
    "Exit the REPL",
    "Usage: /exit\nExits nanocode and ends the session.",
)
def cmd_exit(args: list[str], repl: Any) -> bool:
    """Handle the /exit command."""
    return False


@register_command(
    "/c",
    "Clear conversation",
    "Usage: /c\nClears all messages except the system prompt, starting fresh.",
)
def cmd_clear(args: list[str], repl: Any) -> bool | None:
    """Handle the /c (clear) command."""
    if hasattr(repl, "session"):
        repl.session.clear()
    if hasattr(repl, "terminal"):
        repl.terminal.print_success("⏺ Cleared conversation")
    return None  # Continue running


@register_command(
    "/clear",
    "Clear conversation",
    "Usage: /clear\nClears all messages except the system prompt.",
)
def cmd_clear_alias(args: list[str], repl: Any) -> bool:
    """Handle the /clear command (alias for /c)."""
    return cmd_clear(args, repl)


@register_command(
    "/help",
    "Show help",
    "Usage: /help [command]\nShows help for all commands or a specific command.",
)
def cmd_help(args: list[str], repl: Any) -> bool | None:
    """Handle the /help command."""
    term = getattr(repl, "terminal", Terminal())
    commands = get_commands()

    if len(args) > 1:
        # Show specific command help
        cmd_name = args[1]
        if cmd_name in commands:
            desc, help_text = commands[cmd_name]
            term.print(f"{Colors.BOLD}{cmd_name}{Colors.RESET}: {desc}")
            if help_text:
                term.print(f"\n{help_text}")
        else:
            term.print_error(f"Unknown command: {cmd_name}")
    else:
        # Show all commands
        term.print(f"{Colors.BOLD}Available commands:{Colors.RESET}")
        for name, (desc, _) in sorted(commands.items()):
            term.print(f"  {name}: {desc}")

    return None


@register_command(
    "/tools",
    "List available tools",
    "Usage: /tools\nLists all available tools and their descriptions.",
)
def cmd_tools(args: list[str], repl: Any) -> bool | None:
    """Handle the /tools command."""
    term = getattr(repl, "terminal", Terminal())

    try:
        from nanocode.tools import list_tools

        tools = list_tools()
        term.print(f"{Colors.BOLD}Available tools:{Colors.RESET}")
        for name, info in sorted(tools.items()):
            term.print(f"  {Colors.BOLD}{name}{Colors.RESET}: {info['description']}")
    except Exception as e:
        term.print_error(f"Error loading tools: {e}")

    return None


@register_command(
    "/env",
    "Show environment",
    "Usage: /env\nShows current configuration and environment variables.",
)
def cmd_env(args: list[str], repl: Any) -> bool | None:
    """Handle the /env command."""
    term = getattr(repl, "terminal", Terminal())

    try:
        from nanocode.core.config import get_settings

        settings = get_settings()
        term.print(f"{Colors.BOLD}Current configuration:{Colors.RESET}")
        term.print(f"  BASE_URL: {settings.base_url}")
        term.print(f"  MODEL_NAME: {settings.model_name}")
        term.print(f"  YOLO: {settings.yolo}")
        term.print(f"  BASH_TIMEOUT: {settings.bash_timeout}")
    except Exception as e:
        term.print_error(f"Error loading settings: {e}")

    return None
