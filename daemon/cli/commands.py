"""Slash commands: registry, built-ins, and dispatch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from daemon.cli.configure import run_configure
from daemon.cli.io import DIM, GREEN, RED, RESET
from daemon.core.prompt import get_default_system_prompt

Handler = Callable[[list[str], list[dict[str, Any]]], "bool | None"]


@dataclass(frozen=True)
class Command:
    """A registered slash command."""

    name: str
    description: str
    handler: Handler
    aliases: tuple[str, ...] = ()


_COMMANDS: dict[str, Command] = {}
_DISPATCH: dict[str, Command] = {}


def register_command(
    name: str,
    description: str,
    *,
    aliases: tuple[str, ...] = (),
) -> Callable[[Handler], Handler]:
    """Register a slash-command handler. The decorated function is returned unchanged."""

    def decorator(handler: Handler) -> Handler:
        cmd = Command(name=name, description=description, handler=handler, aliases=aliases)
        _COMMANDS[name] = cmd
        _DISPATCH[name] = cmd
        for alias in aliases:
            _DISPATCH[alias] = cmd
        return handler

    return decorator


def commands() -> list[Command]:
    """Return all registered commands, sorted by name."""
    return sorted(_COMMANDS.values(), key=lambda c: c.name)


def handle(user_input: str, messages: list[dict[str, Any]]) -> bool | None:
    """Dispatch a slash command.

    Returns False to quit, True if handled, or None if the input is not a
    command and should be sent to the model.
    """
    parts = user_input.split()
    if not parts:
        return None
    head = parts[0]
    cmd = _DISPATCH.get(head)
    if cmd is not None:
        return cmd.handler(parts[1:], messages)
    if head.startswith("/"):
        print(f"{RED}Unknown command: {head}{RESET} {DIM}(try /help){RESET}")
        return True
    return None


@register_command("/help", "Show this list of commands", aliases=("/h", "/?"))
def _cmd_help(_args: list[str], _messages: list[dict[str, Any]]) -> bool | None:
    cmds = commands()
    width = max(len(c.name) for c in cmds)
    for cmd in cmds:
        line = f"  {cmd.name:<{width}}  {cmd.description}"
        if cmd.aliases:
            line += f" {DIM}({', '.join(cmd.aliases)}){RESET}"
        print(line)
    return True


@register_command("/clear", "Reset the conversation history", aliases=("/c",))
def _cmd_clear(_args: list[str], messages: list[dict[str, Any]]) -> bool | None:
    messages[:] = [{"role": "system", "content": get_default_system_prompt()}]
    print(f"{GREEN}⏺ Cleared conversation{RESET}")
    return True


@register_command("/config", "Run the interactive configuration flow", aliases=("/configure",))
def _cmd_config(_args: list[str], _messages: list[dict[str, Any]]) -> bool | None:
    run_configure()
    return True


@register_command("/quit", "Exit daemon", aliases=("/q", "/exit", "exit"))
def _cmd_quit(_args: list[str], _messages: list[dict[str, Any]]) -> bool | None:
    return False
