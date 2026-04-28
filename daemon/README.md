# daemon

Minimal agentic coding harness for any OpenAI-compatible endpoint.

daemon is a lightweight, modular CLI tool that brings AI assistance to your terminal. It provides file operations, code search, shell execution, and recursive research capabilities—all powered by OpenAI-compatible APIs.

## Features

- **File Operations**: Read, write, and edit files with smart whitespace tolerance
- **Code Search**: Find files by pattern or grep for regex matches
- **Shell Execution**: Run bash commands with safety confirmations
- **Recursive Research**: Spawn sub-agents for open-ended investigation
- **Safety First**: Dangerous commands require human confirmation
- **Modular Design**: Easy to add new tools and extend functionality

## Installation

```bash
# Clone the repository
git clone https://github.com/naserjamal/daemon.git
cd daemon

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

### Configuration

Create a `.env` file in your project directory:

```bash
BASE_URL=https://api.openai.com/v1
API_KEY=your-api-key-here
MODEL_NAME=gpt-4o-mini
```

Or set environment variables directly:

```bash
export BASE_URL=https://api.openai.com/v1
export API_KEY=your-api-key-here
export MODEL_NAME=gpt-4o-mini
```

### Running

```bash
# Using the module
python -m daemon

# Or if installed
daemon
```

### REPL Commands

| Command | Description |
|---------|-------------|
| `/q`, `/quit`, `/exit` | Exit the REPL |
| `/c`, `/clear` | Clear conversation history |
| `/help` | Show help message |
| `/tools` | List available tools |
| `/env` | Show current configuration |

## Available Tools

### read
Read a text file with line numbers. Supports pagination via `offset` and `limit`.

```python
# Usage in conversation:
# read(path="file.py", offset=1, limit=100)
```

### write
Write content to a file. Creates new files or overwrites existing ones.

```python
# Usage in conversation:
# write(path="output.txt", content="Hello, world!")
```

### edit
Replace text in files with whitespace tolerance. If the pattern matches multiple locations, provide more context or use `all=true`.

```python
# Usage in conversation:
# edit(path="config.py", old="DEBUG = True", new="DEBUG = False")
```

### glob
Find files matching glob patterns, sorted by modification time.

```python
# Usage in conversation:
# glob(pattern="**/*.py", path="src/")
```

### grep
Search files using Python regex patterns, skipping binaries and hidden directories.

```python
# Usage in conversation:
# grep(pattern="def.*\\(", path="src/")
```

### bash
Execute shell commands with configurable timeout.

```python
# Usage in conversation:
# bash(cmd="ls -la", timeout=30)
```

### task
Spawn a sub-agent to delegate a task. Only shows the final summary.

```python
# Usage in conversation:
# task(prompt="Investigate how the auth system works")
```

## Safety

daemon includes danger detection for potentially harmful commands. When a dangerous command is detected, you'll be prompted for confirmation:

- File deletion (`rm -rf`, etc.)
- System modifications (`sudo`, `chmod -R`, etc.)
- Git operations (`git reset --hard`, etc.)
- Network downloads piped to shell (`curl | sh`, etc.)

Set `daemon_YOLO=1` to skip confirmations (use with caution).

## Configuration Options

| Variable | Default | Description |
|---------|---------|-------------|
| `BASE_URL` | `https://api.openai.com/v1` | API endpoint URL |
| `API_KEY` | (empty) | API authentication key |
| `MODEL_NAME` | `gpt-4o-mini` | Model identifier |
| `daemon_YOLO` | `false` | Skip dangerous command confirmations |

## Architecture

```
daemon/
├── core/           # Core functionality
│   ├── config.py   # Configuration management (Pydantic)
│   ├── api.py      # API client
│   ├── session.py  # Message session management
│   └── prompt.py   # System prompt handling
├── tools/          # Tool implementations
│   ├── base.py     # BaseTool abstract class
│   ├── read.py     # File reading
│   ├── write.py    # File writing
│   ├── edit.py     # Smart editing
│   ├── glob.py     # Pattern matching
│   ├── grep.py     # Regex search
│   ├── bash.py     # Shell execution
│   └── task.py     # Sub-agent delegation
├── cli/            # CLI interface
│   ├── main.py     # REPL loop
│   ├── io.py       # Terminal I/O
│   └── commands.py # Slash commands
└── safety/         # Safety features
    ├── danger.py   # Danger pattern detection
    └── confirm.py  # User confirmation
```

## License

MIT License - see [LICENSE](LICENSE) for details.
