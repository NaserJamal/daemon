# nanocode

Minimal agentic coding harness for any OpenAI-compatible API. Single Python file, zero dependencies, ~250 lines.

## Features

- Full agentic loop with tool use
- Tools: `read`, `write`, `edit`, `glob`, `grep`, `bash`
- Conversation history
- Colored terminal output
- Works with any OpenAI-compatible endpoint (OpenAI, OpenRouter, Groq, Together, Ollama, vLLM, ...)

## Usage

Set three environment variables and run:

```bash
export BASE_URL="https://api.openai.com/v1"
export API_KEY="your-key"
export MODEL_NAME="gpt-4o-mini"
python nanocode.py
```

### Optional Environment Variables

| Variable | Description |
|----------|-------------|
| `NANOCODE_YOLO` | Set to `1`, `true`, or `yes` to skip confirmation prompts for dangerous bash commands (e.g., `rm`, `sudo`, git force-push) |

### Examples

**OpenAI**
```bash
export BASE_URL="https://api.openai.com/v1"
export API_KEY="sk-..."
export MODEL_NAME="gpt-4o-mini"
```

**OpenRouter**
```bash
export BASE_URL="https://openrouter.ai/api/v1"
export API_KEY="sk-or-..."
export MODEL_NAME="anthropic/claude-opus-4.5"
```

**Local (Ollama / vLLM / LM Studio)**
```bash
export BASE_URL="http://localhost:11434/v1"
export API_KEY="ollama"
export MODEL_NAME="qwen2.5-coder"
```

## Commands

- `/c` - Clear conversation
- `/q` or `exit` - Quit

## Tools

| Tool | Description |
|------|-------------|
| `read` | Read file with line numbers, offset/limit |
| `write` | Write content to file |
| `edit` | Replace string in file (must be unique) |
| `glob` | Find files by pattern, sorted by mtime |
| `grep` | Search files for regex |
| `bash` | Run shell command |

## Example

```
────────────────────────────────────────
❯ what files are here?
────────────────────────────────────────

⏺ Glob(**/*.py)
  ⎿  nanocode.py

⏺ There's one Python file: nanocode.py
```

## License

MIT
