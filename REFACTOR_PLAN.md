# Nanocode Refactoring Plan

## Overview

Transform `nanocode.py` (479 lines, single file) into a scalable, modular open-source CLI coding harness. Target: easy for humans and AI to understand, extend, and contribute to.

---

## Current State Analysis

| Aspect | Current | Target |
|--------|---------|--------|
| Structure | Single file | Modular package |
| Type Safety | None | Full type hints |
| Testing | None | Comprehensive test suite |
| Extensibility | Hardcoded tools | Plugin architecture |
| Documentation | Sparse | Full docs (README, CONTRIBUTING) |
| Config | Environment vars only | Pydantic + env vars |

---

## Target Directory Structure

```
nanocode/
├── __init__.py              # Package entry, version, exports
├── __main__.py              # CLI entry point (python -m nanocode)
├── pyproject.toml           # Project metadata, dependencies, build config
├── README.md                # User-facing documentation
├── CONTRIBUTING.md          # Contributor guide
├── LICENSE                  # MIT License
│
├── core/
│   ├── __init__.py
│   ├── config.py            # Configuration management (Pydantic)
│   ├── api.py               # API client (call_api, retries, errors)
│   ├── session.py           # Message session management
│   └── prompt.py            # System prompt handling
│
├── tools/
│   ├── __init__.py          # Tool registry and base class
│   ├── base.py              # BaseTool abstract class
│   ├── read.py              # File reading tool
│   ├── write.py             # File writing tool
│   ├── edit.py              # Smart edit tool
│   ├── glob.py              # Glob pattern matching
│   ├── grep.py              # Regex search tool
│   ├── bash.py              # Shell execution with safety
│   └── explore.py           # Sub-agent spawning
│
├── cli/
│   ├── __init__.py
│   ├── main.py              # REPL loop and user interaction
│   ├── io.py                # Terminal I/O (colors, formatting)
│   └── commands.py          # CLI commands (/q, /c, etc.)
│
└── safety/
    ├── __init__.py
    ├── danger.py            # Pattern detection for dangerous commands
    └── confirm.py           # User confirmation prompts
```

---

## Implementation Phases

### Phase 1: Project Foundation
1. Create `pyproject.toml` with dependencies
   - `pydantic` for config validation
   - `pytest` for testing
   - Standard library only for runtime
   
2. Create `nanocode/__init__.py` with version and exports

3. Create `nanocode/__main__.py` for CLI entry point

### Phase 2: Core Module
1. **`core/config.py`**
   - Pydantic `Settings` class
   - Load from .env automatically
   - Validate BASE_URL, API_KEY, MODEL_NAME
   - YOLO mode configuration
   
2. **`core/api.py`**
   - `call_api(messages, tools)` function
   - HTTPError handling with proper messages
   - Retry logic (optional)
   - Streaming support (future)
   
3. **`core/session.py`**
   - `Session` class managing message history
   - `add_user()`, `add_assistant()`, `add_tool()` methods
   - `clear()` for conversation reset
   - Serialize/deserialize for debugging
   
4. **`core/prompt.py`**
   - System prompt templates
   - Tool descriptions from registry
   - Dynamic prompt injection

### Phase 3: Tool Framework
1. **`tools/base.py`**
   - `BaseTool` abstract class
   - `name`, `description`, `parameters` properties
   - Abstract `execute(args)` method
   - JSON schema generation
   
2. **`tools/__init__.py`**
   - `ToolRegistry` class (singleton)
   - `@register_tool` decorator
   - `get_tool()`, `list_tools()`, `get_schema()`
   - Auto-discovery via entry points (future)

3. **Individual tool implementations**
   - Each tool in its own file
   - Inherit from `BaseTool`
   - Full type hints
   - Docstrings for AI consumption

### Phase 4: Safety Module
1. **`safety/danger.py`**
   - `DangerDetector` class
   - Patterns loaded from config/yaml
   - Easy to extend/add patterns
   - Clear categorization
   
2. **`safety/confirm.py`**
   - `ConfirmPrompt` class
   - Clear warning display
   - Timeout handling
   - YOLO bypass

### Phase 5: CLI Module
1. **`cli/io.py`**
   - `Terminal` class for all I/O
   - Color constants
   - `print()`, `input()`, `separator()`
   - Markdown rendering
   
2. **`cli/commands.py`**
   - `CommandRegistry` for `/q`, `/c`, etc.
   - Easy to add new commands
   
3. **`cli/main.py`**
   - `Repl` class orchestrating everything
   - Clear event loop
   - Proper error handling
   - Signal handling (Ctrl+C)

### Phase 6: Documentation
1. **`README.md`**
   - Quick start guide
   - Configuration options
   - Available tools
   - Examples
   
2. **`CONTRIBUTING.md`**
   - How to add a new tool
   - Code style guide
   - Testing requirements
   - Pull request process

### Phase 7: Testing
1. **Unit tests for each tool**
   - Test file operations (temp files)
   - Test edge cases
   - Test error handling
   
2. **Integration tests**
   - API mocking
   - Full session flow
   
3. **Safety tests**
   - Danger pattern detection
   - Confirmation flow

---

## Design Principles

### For AI Consumption
- Every class, method, function has a docstring
- Type hints on ALL parameters and return values
- Tool descriptions are detailed and explicit
- Clear error messages that guide correction

### For Human Contributors
- One concept per file
- Clear file naming matching content
- README and CONTRIBUTING guides
- Example implementations
- Code style enforced (ruff/black)

### For Extensibility
- `@register_tool` decorator for adding tools
- Config file for danger patterns
- Tool schema auto-generated from class
- Clear base class interface

---

## Migration Path

1. Create new directory structure
2. Implement modules in order (foundation → core → tools → cli)
3. Create `nanocode.py` as wrapper maintaining backward compatibility
4. Add deprecation warnings to old interface
5. Full migration after testing

---

## Key Type Definitions

```python
# tools/base.py
from abc import ABC, abstractmethod
from typing import Any, ClassVar

class BaseTool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[dict[str, str]]  # name -> type
    
    @abstractmethod
    def execute(self, args: dict[str, Any]) -> str:
        """Execute the tool with given arguments."""
        ...

# core/config.py
from pydantic import BaseModel

class Settings(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model_name: str = "gpt-4o-mini"
    max_lines: int = 2000
    max_line_len: int = 2000
    bash_timeout: int = 120
    grep_cap: int = 50
    yolo: bool = False
```

---

## Backward Compatibility

The refactor must maintain these exact behaviors:
- Same CLI interface (`python nanocode.py`)
- Same environment variable configuration
- Same tool names, descriptions, parameters
- Same output formats
- Same safety behavior (danger patterns, confirmations)

---

## Success Criteria

1. All existing tools work identically
2. Type check passes (mypy --strict)
3. Test coverage for all tools
4. Documentation is complete
5. New tool can be added in <10 lines of code
6. Clear separation allows parallel development
