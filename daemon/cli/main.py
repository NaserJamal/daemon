"""Interactive REPL: read user input, drive the model, dispatch tool calls."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from daemon.cli import commands
from daemon.cli.configure import handle_subcommand, run_configure
from daemon.cli.io import BOLD, CYAN, DIM, GREEN, RED, RESET, render_markdown, separator
from daemon.cli.prompt import read_input
from daemon.core import sessions, usage
from daemon.core.api import call_api
from daemon.core.config import get_settings
from daemon.core.prompt import get_default_system_prompt
from daemon.core.sessions import Session, SessionMeta
from daemon.tools import get_schema, run_tool

PREVIEW_LEN = 60
ARG_PREVIEW_LEN = 50


def _print_banner() -> None:
    settings = get_settings()
    yolo_tag = f" | {RED}YOLO{RESET}" if settings.yolo else ""
    print(
        f"{BOLD}daemon{RESET} | "
        f"{DIM}{settings.model_name} | {settings.base_url} | {os.getcwd()}{RESET}"
        f"{yolo_tag}\n"
    )


def _assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    """Build the assistant message to append, echoing any reasoning fields verbatim."""
    out: dict[str, Any] = {"role": "assistant", "content": message.get("content") or ""}
    # Providers disagree on the field name for interleaved reasoning; pass
    # through whichever the server returned so the next turn keeps it.
    for key in ("reasoning_content", "reasoning", "reasoning_details"):
        if message.get(key) is not None:
            out[key] = message[key]
    if message.get("tool_calls"):
        out["tool_calls"] = message["tool_calls"]
    return out


def _result_preview(result: str) -> str:
    lines = result.split("\n")
    head = lines[0][:PREVIEW_LEN]
    if len(lines) > 1:
        return f"{head} ... +{len(lines) - 1} lines"
    if len(lines[0]) > PREVIEW_LEN:
        return f"{head}..."
    return head


def _run_turn(messages: list[dict[str, Any]], schema: list[dict[str, Any]]) -> None:
    """Drive the model until it produces a turn with no tool calls."""
    while True:
        streamed = False

        def on_delta(text: str) -> None:
            nonlocal streamed
            if not streamed:
                print(f"\n{CYAN}⏺{RESET} ", end="", flush=True)
                streamed = True
            print(text, end="", flush=True)

        response = call_api(messages, tools=schema, stream=True, on_content_delta=on_delta)
        usage.add_response(response)
        message = response["choices"][0]["message"]
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []

        if streamed:
            print()
        elif content:
            # Server returned content but never streamed a delta (e.g. an
            # adapter that buffers). Render once after the fact.
            print(f"\n{CYAN}⏺{RESET} {render_markdown(content)}")

        messages.append(_assistant_message(message))

        if not tool_calls:
            return

        for call in tool_calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}

            arg_preview = str(next(iter(args.values()), ""))[:ARG_PREVIEW_LEN]
            print(f"\n{GREEN}⏺ {name.capitalize()}{RESET}({DIM}{arg_preview}{RESET})")

            result = run_tool(name, args)
            print(f"  {DIM}⎿  {_result_preview(result)}{RESET}")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": result,
                }
            )


def _pick_session() -> SessionMeta | None:
    """Show the resume picker for the current cwd. Returns the chosen session or None."""
    metas = sessions.list_sessions()
    if not metas:
        print(f"{DIM}No previous sessions found for {os.getcwd()}.{RESET}")
        return None
    print(f"{BOLD}Resume a previous session:{RESET}\n")
    width = len(str(len(metas)))
    for i, meta in enumerate(metas, start=1):
        age = sessions.format_age(meta.updated_at)
        print(
            f"  {DIM}{i:>{width}}.{RESET} "
            f"{CYAN}{age:>4}{RESET} ago  "
            f"{DIM}{meta.message_count:>3} msgs{RESET}  "
            f"{meta.summary}"
        )
    print()
    try:
        raw = input(f"{BOLD}Choose [1-{len(metas)}, Enter to start fresh]:{RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        print(f"{RED}Not a number.{RESET}")
        return None
    if not 1 <= idx <= len(metas):
        print(f"{RED}Out of range.{RESET}")
        return None
    return metas[idx - 1]


def _start_session(argv: list[str]) -> tuple[Session, list[dict[str, Any]]]:
    """Decide whether to resume or start a new session and return (session, messages)."""
    if "--resume" in argv or "-r" in argv:
        chosen = _pick_session()
        if chosen is not None:
            session, messages = Session.open(chosen.path)
            print(f"{GREEN}⏺ Resumed {chosen.session_id} ({len(messages)} messages){RESET}\n")
            return session, messages
    if "--continue" in argv or "-c" in argv:
        latest = sessions.latest_session()
        if latest is not None:
            session, messages = Session.open(latest.path)
            print(f"{GREEN}⏺ Continuing {session.session_id} ({len(messages)} messages){RESET}\n")
            return session, messages
        print(f"{DIM}No previous session to continue; starting fresh.{RESET}\n")
    session = Session.new()
    messages = [{"role": "system", "content": get_default_system_prompt()}]
    session.sync(messages)
    return session, messages


def main() -> None:
    """Run the REPL or dispatch a subcommand."""
    argv = sys.argv[1:]
    # The session flags are REPL-level, not subcommands; strip them before
    # `handle_subcommand` so they don't trigger an "unknown subcommand" error.
    repl_argv = [a for a in argv if a not in ("--resume", "-r", "--continue", "-c")]
    exit_code = handle_subcommand(repl_argv)
    if exit_code is not None:
        raise SystemExit(exit_code)

    if not get_settings().api_key:
        print(f"{DIM}No API key found. Let's set one up.{RESET}\n")
        if run_configure() != 0:
            raise SystemExit(1)
        print()

    _print_banner()
    schema = get_schema()
    session, messages = _start_session(argv)
    commands.set_session(session)

    while True:
        try:
            print(separator())
            user_input = read_input().strip()
            print(separator())
            if not user_input:
                continue

            handled = commands.handle(user_input, messages)
            if handled is False:
                break
            if handled is True:
                # Slash commands may have swapped the active session (e.g.
                # /clear creates a new one). Re-fetch and persist.
                active = commands.get_session()
                if active is not None:
                    session = active
                    session.sync(messages)
                continue

            messages.append({"role": "user", "content": user_input})
            _run_turn(messages, schema)
            session.sync(messages)
            if usage.show_per_turn():
                print(f"\n{DIM}⏺ usage: {usage.format_summary()}{RESET}")
            print()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}⏺ Error: {err}{RESET}")


if __name__ == "__main__":
    main()
