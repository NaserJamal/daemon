"""
Terminal I/O utilities for nanocode.

Provides color constants, terminal size detection, and formatted
output utilities including markdown rendering.

Example:
    >>> from nanocode.cli.io import Terminal, Colors
    >>> term = Terminal()
    >>> term.print_info("Hello, world!")
    >>> term.print_error("Something went wrong")
"""

from __future__ import annotations

import os
import re
from typing import TextIO


# ANSI escape codes for terminal colors and styles
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

# Foreground colors
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Bright foreground colors
BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"


class Colors:
    """
    Color and style constants for terminal output.

    Use these constants to build colored output strings by
    concatenating with RESET at the end.

    Example:
        >>> print(f"{Colors.RED}Error!{Colors.RESET}")
    """

    RESET = RESET
    BOLD = BOLD
    DIM = DIM
    ITALIC = ITALIC
    UNDERLINE = UNDERLINE

    BLACK = BLACK
    RED = RED
    GREEN = GREEN
    YELLOW = YELLOW
    BLUE = BLUE
    MAGENTA = MAGENTA
    CYAN = CYAN
    WHITE = WHITE

    BRIGHT_BLACK = BRIGHT_BLACK
    BRIGHT_RED = BRIGHT_RED
    BRIGHT_GREEN = BRIGHT_GREEN
    BRIGHT_YELLOW = BRIGHT_YELLOW
    BRIGHT_BLUE = BRIGHT_BLUE
    BRIGHT_MAGENTA = BRIGHT_MAGENTA
    BRIGHT_CYAN = BRIGHT_CYAN
    BRIGHT_WHITE = BRIGHT_WHITE

    # Common combinations
    PROMPT = BLUE + BOLD
    SUCCESS = GREEN
    ERROR = RED
    WARNING = YELLOW
    INFO = CYAN
    DEBUG = DIM
    RESULT = DIM


class Terminal:
    """
    Terminal I/O handler with formatting utilities.

    Provides convenient methods for colored output, input handling,
    and formatted display of results. Handles terminal detection
    and width calculation.

    Attributes:
        output: File-like object for output (default: sys.stdout).
        input_stream: File-like object for input (default: sys.stdin).
        use_colors: Whether to use ANSI color codes.

    Example:
        >>> term = Terminal()
        >>> term.print("Hello, world!", style=Colors.GREEN)
        >>> user_input = term.input("Enter your name: ")
    """

    def __init__(
        self,
        output: TextIO | None = None,
        input_stream: TextIO | None = None,
        use_colors: bool = True,
    ) -> None:
        """
        Initialize the terminal handler.

        Args:
            output: Output stream (default: sys.stdout).
            input_stream: Input stream (default: sys.stdin).
            use_colors: Whether to use color codes (auto-detect if None).
        """
        import sys

        self._output = output or sys.stdout
        self._input_stream = input_stream or sys.stdin
        self._use_colors = use_colors

    @property
    def output(self) -> TextIO:
        """Get the output stream."""
        return self._output

    @property
    def input_stream(self) -> TextIO:
        """Get the input stream."""
        return self._input_stream

    @property
    def use_colors(self) -> bool:
        """Check if colors are enabled."""
        return self._use_colors

    def print(
        self,
        *args: object,
        sep: str = " ",
        end: str = "\n",
        style: str = "",
        file: TextIO | None = None,
    ) -> None:
        """
        Print to the terminal with optional styling.

        Args:
            *args: Objects to print.
            sep: Separator between arguments.
            end: String appended after the last value.
            style: ANSI style code to apply.
            file: Output stream (uses default if None).
        """
        output_file = file or self._output
        if style and self._use_colors:
            output_file.write(style)
        print(*args, sep=sep, end=end, file=output_file)
        if style and self._use_colors:
            output_file.write(RESET)

    def input(self, prompt: str = "", style: str = "") -> str:
        """
        Get input from the user.

        Args:
            prompt: Prompt to display.
            style: ANSI style code for the prompt.

        Returns:
            The user's input, stripped of whitespace.

        Raises:
            KeyboardInterrupt: If user presses Ctrl+C.
            EOFError: If input stream ends.
        """
        if style and self._use_colors:
            self._output.write(style)
            self._output.write(prompt)
            self._output.write(RESET)
        else:
            self._output.write(prompt)
        self._output.flush()
        return self._input_stream.readline().strip()

    def print_error(self, *args: object, sep: str = " ") -> None:
        """
        Print an error message.

        Args:
            *args: Arguments to print.
            sep: Separator between arguments.
        """
        self.print(*args, sep=sep, style=Colors.ERROR)

    def print_success(self, *args: object, sep: str = " ") -> None:
        """
        Print a success message.

        Args:
            *args: Arguments to print.
            sep: Separator between arguments.
        """
        self.print(*args, sep=sep, style=Colors.SUCCESS)

    def print_info(self, *args: object, sep: str = " ") -> None:
        """
        Print an info message.

        Args:
            *args: Arguments to print.
            sep: Separator between arguments.
        """
        self.print(*args, sep=sep, style=Colors.INFO)

    def print_warning(self, *args: object, sep: str = " ") -> None:
        """
        Print a warning message.

        Args:
            *args: Arguments to print.
            sep: Separator between arguments.
        """
        self.print(*args, sep=sep, style=Colors.WARNING)

    def print_debug(self, *args: object, sep: str = " ") -> None:
        """
        Print a debug message.

        Args:
            *args: Arguments to print.
            sep: Separator between arguments.
        """
        self.print(*args, sep=sep, style=Colors.DEBUG)

    def separator(self, character: str = "─", width: int | None = None) -> str:
        """
        Generate a visual separator line.

        Args:
            character: Character to repeat.
            width: Width of the line (auto-detect if None).

        Returns:
            The separator string.
        """
        if width is None:
            try:
                width = min(os.get_terminal_size().columns, 80)
            except OSError:
                width = 80

        return Colors.DIM + character * width + Colors.RESET

    def render_markdown(self, text: str) -> str:
        """
        Render basic markdown formatting.

        Currently supports: **bold**, *italic*, `code`

        Args:
            text: Text with markdown formatting.

        Returns:
            Text with ANSI codes applied.
        """
        result = text

        # Bold: **text**
        result = re.sub(
            r"\*\*(.+?)\*\*",
            BOLD + r"\1" + RESET,
            result,
        )

        # Italic: *text*
        result = re.sub(
            r"\*(.+?)\*",
            ITALIC + r"\1" + RESET,
            result,
        )

        # Inline code: `code`
        result = re.sub(
            r"`(.+?)`",
            Colors.CYAN + r"\1" + RESET,
            result,
        )

        return result

    def print_markdown(self, text: str) -> None:
        """
        Print text with markdown rendering.

        Args:
            text: Text with markdown formatting.
        """
        self.print(self.render_markdown(text))

    def print_result_preview(
        self,
        result: str,
        max_lines: int = 10,
        max_line_len: int = 60,
    ) -> None:
        """
        Print a preview of a command result.

        Args:
            result: The result string.
            max_lines: Maximum lines to show.
            max_line_len: Maximum characters per line.
        """
        lines = result.split("\n")
        preview_lines = lines[:max_lines]

        for i, line in enumerate(preview_lines):
            if len(line) > max_line_len:
                preview_lines[i] = line[:max_line_len] + "..."

        if len(lines) > max_lines:
            preview_lines.append(
                f"... +{len(lines) - max_lines} more lines"
            )

        for line in preview_lines:
            self.print(f"  {Colors.DIM}⎿ {line}{Colors.RESET}")

    def clear_line(self) -> None:
        """Clear the current terminal line."""
        self.print("\033[2K\r", end="")

    def clear_screen(self) -> None:
        """Clear the entire terminal screen."""
        self.print("\033[2J\033[H", end="", file=self._output)
