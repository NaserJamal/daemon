# daemon

Minimal agentic coding harness for any OpenAI-compatible API. Single Python file, zero dependencies, ~250 lines.

## Features

- Full agentic loop with tool use
- Tools: `read`, `write`, `edit`, `glob`, `grep`, `bash`
- Conversation history
- Colored terminal output
- Works with any OpenAI-compatible endpoint (OpenAI, OpenRouter, Groq, Together, Ollama, vLLM, ...)

## Usage

Run `daemon` and you'll be prompted to set up your credentials on first launch:

```bash
daemon
```

Credentials are stored in a per-user config file (locked to mode `0600` on
Unix), so once configured you can run `daemon` from anywhere on the machine.

| OS      | Config location                                              |
|---------|--------------------------------------------------------------|
| Linux   | `$XDG_CONFIG_HOME/daemon/config` (default `~/.config/daemon/config`) |
| macOS   | `~/Library/Application Support/daemon/config`                |
| Windows | `%APPDATA%\daemon\config` (typically `…\AppData\Roaming\daemon\config`) |

### Reconfiguring

| Command                  | What it does                                      |
|--------------------------|---------------------------------------------------|
| `daemon configure`       | Interactive prompt to update all values           |
| `daemon config show`     | Print current values (API key masked)             |
| `daemon config path`     | Print the config file path                        |
| `daemon config edit`     | Open the file in `$EDITOR` (or notepad/nano)      |
| `daemon yolo`            | Toggle YOLO mode (also accepts `on`/`off`)        |
| `/config` (in REPL)      | Re-run the interactive setup without leaving      |

### YOLO mode

When YOLO is on, daemon skips the confirmation prompts before running
dangerous bash commands (e.g. `rm`, `sudo`, force-push). It is persisted in
the config file. Toggle it with `daemon yolo`, or set it explicitly:

```bash
daemon yolo on
daemon yolo off
```

### Provider Examples

When you run `daemon configure`, supply values such as:

**OpenAI**
- `BASE_URL`: `https://api.openai.com/v1`
- `API_KEY`: `sk-...`
- `MODEL_NAME`: `gpt-4o-mini`

**OpenRouter**
- `BASE_URL`: `https://openrouter.ai/api/v1`
- `API_KEY`: `sk-or-...`
- `MODEL_NAME`: `anthropic/claude-opus-4.5`

**Local (Ollama / vLLM / LM Studio)**
- `BASE_URL`: `http://localhost:11434/v1`
- `API_KEY`: `ollama`
- `MODEL_NAME`: `qwen2.5-coder`

## Commands

- `/c` - Clear conversation
- `/config` - Reconfigure credentials
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
  ⎿  daemon.py

⏺ There's one Python file: daemon.py
```

## License

MIT
