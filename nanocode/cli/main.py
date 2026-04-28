"""
Main REPL loop for nanocode.

Orchestrates the interactive conversation loop, handling user input,
API calls, tool execution, and result display.

Example:
    >>> from nanocode.cli.main import main
    >>> main()  # Starts interactive REPL
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from nanocode.cli.io import Colors, Terminal
from nanocode.cli.commands import execute_command, is_command
from nanocode.core.api import call_api
from nanocode.core.config import get_settings
from nanocode.core.prompt import get_default_system_prompt
from nanocode.core.session import Session
from nanocode.tools import get_schema, run_tool


class Repl:
    """
    Interactive REPL for nanocode.

    Manages the conversation loop, handling user input, API calls,
    tool execution, and display of results. Supports slash commands
    for special operations.

    Attributes:
        terminal: Terminal I/O handler.
        session: Message session manager.
        running: Whether the REPL is actively running.

    Example:
        >>> repl = Repl()
        >>> repl.run()
    """

    def __init__(self, terminal: Terminal | None = None) -> None:
        """
        Initialize the REPL.

        Args:
            terminal: Optional Terminal instance for I/O.
        """
        self.terminal = terminal or Terminal()
        self.session = Session()
        self.settings = get_settings()
        self.schema = get_schema()
        self.running = False

    def print_banner(self) -> None:
        """Print the startup banner."""
        yolo_tag = (
            f" | {Colors.RED}YOLO{Colors.RESET}"
            if self.settings.yolo
            else ""
        )
        self.terminal.print(
            f"{Colors.BOLD}nanocode{Colors.RESET} | "
            f"{Colors.DIM}{self.settings.model_name} | "
            f"{self.settings.base_url} | "
            f"{os.getcwd()}{Colors.RESET}{yolo_tag}\n"
        )

    def process_input(self, user_input: str) -> bool:
        """
        Process user input.

        Args:
            user_input: The user's input string.

        Returns:
            True to continue the loop, False to exit.
        """
        if not user_input:
            return True

        # Check for slash commands
        if is_command(user_input):
            args = user_input.split()
            result = execute_command(args[0], args, self)
            if result is not None:
                return result
            return True

        # Regular message to API
        self.session.add_user(user_input)
        return self._process_api_response()

    def _process_api_response(self) -> bool:
        """
        Call the API and process the response.

        Returns:
            True to continue, False to exit.
        """
        try:
            response = call_api(
                self.session.get_messages(),
                settings=self.settings,
                tools=self.schema,
            )
        except Exception as err:
            self.terminal.print_error(f"Error: {err}")
            return True

        message = response["choices"][0]["message"]
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []

        # Handle content
        if content:
            self.terminal.print(f"\n{Colors.CYAN}⏺{Colors.RESET} ")
            self.terminal.print_markdown(content)

        # Build assistant message
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}

        # Pass through reasoning fields (provider-dependent naming)
        for key in ("reasoning_content", "reasoning", "reasoning_details"):
            if message.get(key) is not None:
                assistant_msg[key] = message[key]

        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls

        self.session.messages.append(assistant_msg)

        # If no tool calls, we're done
        if not tool_calls:
            return True

        # Execute tool calls
        for call in tool_calls:
            tool_name = call["function"]["name"]
            try:
                tool_args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                tool_args = {}

            # Print tool execution
            arg_preview = str(next(iter(tool_args.values()), ""))[:50]
            self.terminal.print(
                f"\n{Colors.GREEN}⏺ {tool_name.capitalize()}"
                f"{Colors.RESET}({Colors.DIM}{arg_preview}{Colors.RESET})"
            )

            # Execute tool
            result = run_tool(tool_name, tool_args)

            # Print result preview
            self.terminal.print_result_preview(result)

            # Add to session
            self.session.add_tool(
                content=result,
                tool_call_id=call.get("id", ""),
            )

        return True

    def run(self) -> None:
        """
        Run the interactive REPL loop.
        """
        self.running = True
        self.print_banner()

        while self.running:
            try:
                # Print separator
                self.terminal.print(self.terminal.separator())
                user_input = self.terminal.input(f"{Colors.PROMPT}❯{Colors.RESET} ")
                self.terminal.print(self.terminal.separator())

                if not self.process_input(user_input):
                    break

                self.terminal.print()  # Blank line

            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as err:
                self.terminal.print_error(f"⏺ Error: {err}")

        self.running = False

    def stop(self) -> None:
        """Stop the REPL loop."""
        self.running = False


def main() -> None:
    """
    Main entry point for the CLI.

    Loads configuration and starts the interactive REPL.
    """
    # Ensure .env is loaded
    from nanocode.core.config import load_dotenv
    load_dotenv()

    try:
        repl = Repl()
        repl.run()
    except Exception as e:
        print(f"{Colors.RED}Fatal error: {e}{Colors.RESET}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
