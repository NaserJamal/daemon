"""Interactive REPL: read user input, drive the model, dispatch tool calls."""

from __future__ import annotations

import json
import os
from typing import Any

from daemon.cli import commands
from daemon.cli.io import BOLD, CYAN, DIM, GREEN, RED, RESET, render_markdown, separator
from daemon.cli.prompt import read_input
from daemon.core.api import call_api
from daemon.core.config import get_settings
from daemon.core.prompt import get_default_system_prompt
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
        message = call_api(messages, tools=schema)["choices"][0]["message"]
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []

        if content:
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

            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": result,
            })


def main() -> None:
    """Run the REPL. Returns when the user quits or the input stream closes."""
    _print_banner()
    schema = get_schema()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": get_default_system_prompt()}
    ]

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
                continue

            messages.append({"role": "user", "content": user_input})
            _run_turn(messages, schema)
            print()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}⏺ Error: {err}{RESET}")


if __name__ == "__main__":
    main()
