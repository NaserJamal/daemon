# Contributing to daemon

Thank you for your interest in contributing to daemon! This guide will help you get started with developing, testing, and extending the project.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/naserjamal/daemon.git
   cd daemon
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Verify the installation:
   ```bash
   python -m daemon --help
   ```

## Project Structure

```
daemon/
├── core/           # Core functionality
│   ├── config.py   # Configuration (Pydantic Settings)
│   ├── api.py      # API client (call_api)
│   ├── session.py  # Message session management
│   └── prompt.py   # System prompt handling
├── tools/          # Tool implementations
│   ├── __init__.py # Tool registry and @register_tool decorator
│   ├── base.py     # BaseTool abstract class
│   └── *.py        # Individual tool implementations
├── cli/            # CLI interface
│   ├── main.py     # REPL loop
│   ├── io.py       # Terminal I/O utilities
│   └── commands.py # Slash commands
└── safety/         # Safety features
    ├── danger.py   # Danger pattern detection
    └── confirm.py  # User confirmation prompts
```

## Adding a New Tool

Tools extend the AI's capabilities. Here's how to add a new tool:

### 1. Create the Tool File

Create a new file in `daemon/tools/` (e.g., `mytool.py`):

```python
"""My custom tool for daemon."""

from __future__ import annotations

from typing import Any, ClassVar

from daemon.tools.base import BaseTool
from daemon.tools import register_tool


@register_tool
class MyTool(BaseTool):
    """
    Tool for doing something useful.

    Provide a clear description of what this tool does.
    The AI uses this description to decide when to call the tool.

    Attributes:
        name: The tool's identifier.
        description: What the AI sees.
        parameters: Parameter schema.
    """

    name = "my_tool"
    description = "Does something useful with the given input."
    parameters = {
        "input": "string",           # Required string parameter
        "count": "integer?",        # Optional integer parameter
        "verbose": "boolean?",      # Optional boolean parameter
    }

    def execute(self, args: dict[str, Any]) -> str:
        """
        Execute the tool.

        Args:
            args: Dictionary of arguments from the AI.

        Returns:
            A string result to send back to the AI.
        """
        input_value = args["input"]
        count = args.get("count", 1)
        verbose = args.get("verbose", False)

        # Your tool logic here
        result = f"Processed {input_value} {count} times"

        if verbose:
            result = f"[DEBUG] {result}"

        return result
```

### 2. Register the Tool

The `@register_tool` decorator automatically registers the tool with the global registry. Just importing the module is enough:

```python
# In daemon/tools/__init__.py
from daemon.tools import mytool  # noqa: F401
```

### 3. Parameter Types

Supported parameter types:

| Type | Required | Description |
|------|----------|-------------|
| `string` | Yes | Text string |
| `integer` | Yes | Whole number |
| `boolean` | Yes | True/false |
| `string?` | No | Optional string |
| `integer?` | No | Optional integer |
| `boolean?` | No | Optional boolean |

### 4. Error Handling

Always return error strings, never raise exceptions:

```python
def execute(self, args: dict[str, Any]) -> str:
    try:
        # Your code
        return success_result
    except FileNotFoundError as e:
        return f"error: file not found - {e}"
    except PermissionError as e:
        return f"error: permission denied - {e}"
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"
```

## Adding Slash Commands

Slash commands provide REPL utilities like `/help` and `/clear`.

### 1. Register a Command

```python
# In daemon/cli/commands.py
from daemon.cli.commands import register_command

@register_command(
    "/mycmd",
    "Does something useful",
    "Usage: /mycmd [args]\nDetailed help text here.",
)
def my_command_handler(args: list[str], repl) -> bool | None:
    """Handle the /mycmd command."""
    repl.terminal.print_info("Command executed!")

    # Return values:
    # - None: Continue running (default)
    # - True: Continue running
    # - False: Exit the REPL
    return None
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=daemon --cov-report=html

# Run specific test file
pytest tests/test_tools.py

# Run specific test
pytest tests/test_tools.py::test_read_tool
```

## Code Style

- Use type hints everywhere
- Add docstrings for all public functions and classes
- Follow PEP 8 guidelines
- Use descriptive variable names
- Keep functions focused and small

### Type Hints

```python
# Good
def read_file(path: str, offset: int = 1) -> str:
    ...

# Bad
def read_file(path, offset=1):
    ...
```

### Docstrings

```python
def my_function(param: str) -> str:
    """
    Brief description of what this function does.

    Longer explanation if needed. Can span multiple lines
    and include examples.

    Args:
        param: Description of the parameter.

    Returns:
        Description of the return value.

    Raises:
        ValueError: When this happens.
        TypeError: When that happens.

    Example:
        >>> my_function("test")
        'result'
    """
```

## Adding Danger Patterns

To add new danger patterns for bash safety:

```python
# In daemon/safety/danger.py
DANGER_PATTERNS = [
    ...
    (r"\bnew_pattern\b", "description"),
]
```

Or dynamically:

```python
from daemon.safety.danger import get_detector

detector = get_detector()
detector.add_pattern(r"\bmy_command\b", "my_command")
```

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/my-feature`)
3. **Add** your changes with tests
4. **Ensure** all tests pass (`pytest`)
5. **Update** documentation if needed
6. **Commit** with clear messages
7. **Push** to your fork
8. **Open** a Pull Request

## Reporting Issues

When reporting issues, please include:

- Python version
- daemon version
- Steps to reproduce
- Expected vs actual behavior
- Error messages or logs

## Questions?

Feel free to open an issue for questions or discussions.
