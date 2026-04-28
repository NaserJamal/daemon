"""Slash commands: registry, built-ins, and dispatch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from daemon.cli.configure import run_configure
from daemon.cli.io import BOLD, CYAN, DIM, GREEN, RED, RESET
from daemon.core import sessions, usage
from daemon.core.prompt import get_default_system_prompt
from daemon.core.sessions import Session

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
_SESSION: Session | None = None


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


def set_session(session: Session | None) -> None:
    """Tell the command module which session is active. Called from the REPL."""
    global _SESSION
    _SESSION = session


def get_session() -> Session | None:
    """Return the currently active session, if any."""
    return _SESSION


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


@register_command("/clear", "Start a new conversation", aliases=("/c",))
def _cmd_clear(_args: list[str], messages: list[dict[str, Any]]) -> bool | None:
    messages[:] = [{"role": "system", "content": get_default_system_prompt()}]
    usage.reset()
    set_session(Session.new())
    print(f"{GREEN}⏺ Started a new conversation{RESET}")
    return True


@register_command(
    "/usage",
    "Show token usage; pass on/off to toggle per-turn display",
    aliases=("/u",),
)
def _cmd_usage(args: list[str], _messages: list[dict[str, Any]]) -> bool | None:
    if args:
        choice = args[0].lower()
        if choice in ("on", "off"):
            usage.set_show_per_turn(choice == "on")
            state = "on" if choice == "on" else "off"
            print(f"{GREEN}⏺ Per-turn usage display: {state}{RESET}")
            return True
        print(f"{RED}Usage: /usage [on|off]{RESET}")
        return True
    state = "on" if usage.show_per_turn() else "off"
    print(f"{GREEN}⏺ {usage.format_summary()}{RESET} {DIM}(per-turn: {state}){RESET}")
    return True


@register_command(
    "/rewind",
    "Roll back to a previous user message",
    aliases=("/r",),
)
def _cmd_rewind(args: list[str], messages: list[dict[str, Any]]) -> bool | None:
    user_indices = [i for i, m in enumerate(messages) if m.get("role") == "user"]
    if not user_indices:
        print(f"{DIM}Nothing to rewind to.{RESET}")
        return True

    if args:
        choice = _parse_rewind_choice(args[0], len(user_indices))
        if choice is None:
            print(f"{RED}Invalid selection.{RESET}")
            return True
    else:
        _print_rewind_menu(messages, user_indices)
        try:
            raw = input(f"{BOLD}Rewind to [1-{len(user_indices)}]:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return True
        if not raw:
            return True
        choice = _parse_rewind_choice(raw, len(user_indices))
        if choice is None:
            print(f"{RED}Invalid selection.{RESET}")
            return True

    target = user_indices[choice - 1]
    # Drop the chosen user message and everything after it so the user can
    # re-prompt from that point. The session file is rewritten to match.
    messages[:] = messages[:target]
    session = get_session()
    if session is not None:
        session.rewrite(messages)
    print(f"{GREEN}⏺ Rewound to before user message #{choice}{RESET}")
    return True


def _parse_rewind_choice(raw: str, maximum: int) -> int | None:
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if 1 <= n <= maximum else None


def _print_rewind_menu(messages: list[dict[str, Any]], user_indices: list[int]) -> None:
    print(f"{BOLD}User messages in this conversation:{RESET}\n")
    width = len(str(len(user_indices)))
    for n, idx in enumerate(user_indices, start=1):
        content = messages[idx].get("content")
        text = (content or "").strip().splitlines()[0] if isinstance(content, str) else ""
        if len(text) > 70:
            text = text[:69] + "…"
        print(f"  {DIM}{n:>{width}}.{RESET} {text}")
    print()


@register_command("/sessions", "List recent sessions for this directory")
def _cmd_sessions(_args: list[str], _messages: list[dict[str, Any]]) -> bool | None:
    metas = sessions.list_sessions()
    if not metas:
        print(f"{DIM}No previous sessions for this directory.{RESET}")
        return True
    active = get_session()
    width = len(str(len(metas)))
    for i, meta in enumerate(metas, start=1):
        age = sessions.format_age(meta.updated_at)
        marker = f"{GREEN}*{RESET}" if active and meta.session_id == active.session_id else " "
        print(
            f"  {marker} {DIM}{i:>{width}}.{RESET} "
            f"{CYAN}{age:>4}{RESET} ago  "
            f"{DIM}{meta.message_count:>3} msgs{RESET}  "
            f"{meta.summary}"
        )
    return True


@register_command("/config", "Run the interactive configuration flow", aliases=("/configure",))
def _cmd_config(_args: list[str], _messages: list[dict[str, Any]]) -> bool | None:
    run_configure()
    return True


@register_command("/quit", "Exit daemon", aliases=("/q", "/exit", "exit"))
def _cmd_quit(_args: list[str], _messages: list[dict[str, Any]]) -> bool | None:
    return False
