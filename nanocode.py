#!/usr/bin/env python3
"""nanocode - minimal agentic coding harness for any OpenAI-compatible endpoint"""

import glob as globlib, json, os, re, subprocess, threading, urllib.error, urllib.request


def load_dotenv(path=".env"):
    """Load KEY=VALUE lines from a .env file into os.environ (does not overwrite)."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            os.environ.setdefault(key, value)


load_dotenv()

BASE_URL = os.environ.get("BASE_URL", "https://api.openai.com/v1").rstrip("/")
API_KEY = os.environ.get("API_KEY", "")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, RED = "\033[34m", "\033[36m", "\033[32m", "\033[31m"

MAX_LINES = 2000
MAX_LINE_LEN = 2000
BASH_TIMEOUT_DEFAULT = 120
GREP_CAP = 50

YOLO = os.environ.get("NANOCODE_YOLO", "").lower() in ("1", "true", "yes")

# Patterns that warrant a human confirmation before bash execution.
# Detection is best-effort - a determined model can obfuscate around regex.
DANGER_PATTERNS = [
    (r"\brm\s+(-[a-zA-Z]*[rRfF][a-zA-Z]*\s+)?", "rm"),
    (r"\brmdir\b", "rmdir"),
    (r"\bmv\s+[^|;&]*\s+/(?:\s|$)", "mv to /"),
    (r"\bdd\b.*\bof=", "dd"),
    (r"\bmkfs\.[a-z0-9]+\b", "mkfs"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", "system power"),
    (r"\bkill(all)?\s+-9\b", "kill -9"),
    (r":\(\)\s*\{.*\}\s*;", "fork bomb"),
    (r">\s*/dev/(sd[a-z]|nvme|disk)", "raw disk write"),
    (r">\s*/etc/", "overwrite /etc"),
    (r"\bchmod\s+-R\b", "recursive chmod"),
    (r"\bchown\s+-R\b", "recursive chown"),
    (r"\bsudo\b", "sudo"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+clean\s+-[a-z]*f", "git clean -f"),
    (r"\bgit\s+push\s+(-[a-zA-Z]*f|--force)", "git force push"),
    (r"\bgit\s+branch\s+-D\b", "git branch -D"),
    (r"\bgit\s+checkout\s+\.", "git checkout ."),
    (r"\bgit\s+restore\s+\.", "git restore ."),
    (r"\bdrop\s+(table|database|schema)\b", "SQL drop"),
    (r"\btruncate\s+table\b", "SQL truncate"),
    (r"\bdocker\s+(rm|rmi|system\s+prune|volume\s+rm)", "docker destructive"),
    (r"\bkubectl\s+delete\b", "kubectl delete"),
    (r"\bterraform\s+(destroy|apply)\b", "terraform destroy/apply"),
    (r"\bnpm\s+publish\b", "npm publish"),
    (r"\b(curl|wget)\b[^|;&]*\|\s*(sh|bash|zsh)\b", "curl | sh"),
    (r"\beval\b", "eval"),
]


def danger_reason(cmd):
    for pattern, label in DANGER_PATTERNS:
        if re.search(pattern, cmd):
            return label
    return None


def confirm(cmd, reason):
    print(f"\n{RED}⚠  Dangerous command detected ({reason}):{RESET}")
    print(f"  {BOLD}{cmd}{RESET}")
    try:
        answer = input(f"{RED}Approve? [y/N] {RESET}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return False
    return answer in ("y", "yes")


def read(args):
    path = args["path"]
    offset = max(1, args.get("offset", 1))
    limit = args.get("limit", MAX_LINES)

    with open(path, "rb") as f:
        if b"\x00" in f.read(4096):
            return f"error: {path} looks binary"

    selected = []
    total = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for total, line in enumerate(f, 1):
            if offset <= total < offset + limit:
                line = line.rstrip("\n")
                if len(line) > MAX_LINE_LEN:
                    line = line[:MAX_LINE_LEN] + "... (line truncated)"
                selected.append(f"{total:4}| {line}")

    if total and offset > total:
        return f"error: offset {offset} exceeds file length ({total} lines)"

    end = offset + len(selected) - 1
    footer = (
        f"\n(end of file - {total} lines total)"
        if end >= total
        else f"\n(showing {offset}-{end} of {total}, use offset={end + 1} to continue)"
    )
    return "\n".join(selected) + footer


def write(args):
    with open(args["path"], "w", encoding="utf-8") as f:
        f.write(args["content"])
    return "ok"


def _find_match(text, old):
    """Locate `old` in `text`. Returns (candidate_substring, occurrence_count).

    Tries: (1) exact match, (2) line-trimmed match (tolerates per-line
    leading/trailing whitespace differences). Returns (None, 0) on miss.
    """
    if old in text:
        return old, text.count(old)

    file_lines = text.split("\n")
    old_lines = old.split("\n")
    if not old_lines or len(old_lines) > len(file_lines):
        return None, 0

    target = [l.strip() for l in old_lines]
    matches = []
    for i in range(len(file_lines) - len(old_lines) + 1):
        window = file_lines[i : i + len(old_lines)]
        if [l.strip() for l in window] == target:
            candidate = "\n".join(window)
            if candidate in text:
                matches.append(candidate)

    if not matches:
        return None, 0
    unique = [c for c in matches if text.count(c) == 1]
    chosen = unique[0] if unique else matches[0]
    return chosen, text.count(chosen)


def edit(args):
    path, old, new = args["path"], args["old"], args["new"]
    if old == new:
        return "error: old and new are identical"

    if old == "":
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return "ok (created)"

    with open(path, encoding="utf-8") as f:
        text = f.read()
    candidate, count = _find_match(text, old)
    if candidate is None:
        return "error: old not found in file"
    if count > 1 and not args.get("all"):
        return f"error: old matches {count} places, add more context or pass all=true"

    n = -1 if args.get("all") else 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace(candidate, new, n))
    return "ok"


def glob(args):
    pattern = os.path.join(args.get("path", "."), args["pattern"])
    files = globlib.glob(pattern, recursive=True)

    def mtime(p):
        try:
            return os.path.getmtime(p)
        except OSError:
            return 0

    return "\n".join(sorted(files, key=mtime, reverse=True)) or "none"


def grep(args):
    pattern = re.compile(args["pattern"])
    hits = []
    for dirpath, dirnames, filenames in os.walk(args.get("path", ".")):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                with open(path, "rb") as f:
                    if b"\x00" in f.read(4096):
                        continue
                with open(path, encoding="utf-8", errors="replace") as f:
                    for n, line in enumerate(f, 1):
                        if pattern.search(line):
                            hits.append(f"{path}:{n}:{line.rstrip()}")
                            if len(hits) >= GREP_CAP:
                                return "\n".join(hits) + f"\n(truncated at {GREP_CAP} matches)"
            except OSError:
                continue
    return "\n".join(hits) or "none"


def explore(args):
    """Spawn a sub-agent with the same tools; return only its final text."""
    sub = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": args["prompt"]},
    ]
    while True:
        message = call_api(sub)["choices"][0]["message"]
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls") or []

        assistant_msg = {"role": "assistant", "content": content}
        for key in ("reasoning_content", "reasoning", "reasoning_details"):
            if message.get(key) is not None:
                assistant_msg[key] = message[key]
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        sub.append(assistant_msg)

        if not tool_calls:
            return content or "(no response)"

        for call in tool_calls:
            try:
                tool_args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                tool_args = {}
            sub.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": run_tool(call["function"]["name"], tool_args),
            })


def bash(args):
    cmd = args["cmd"]
    if not YOLO:
        reason = danger_reason(cmd)
        if reason and not confirm(cmd, reason):
            return "error: user denied execution"

    timeout = max(0, args.get("timeout", BASH_TIMEOUT_DEFAULT))
    proc = subprocess.Popen(
        cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    timer = threading.Timer(timeout, proc.kill) if timeout else None
    if timer:
        timer.start()
    lines = []
    try:
        for line in proc.stdout:
            print(f"  {DIM}│ {line.rstrip()}{RESET}", flush=True)
            lines.append(line)
    finally:
        if timer:
            timer.cancel()
        proc.wait()
    out = "".join(lines).strip() or "(empty)"
    if proc.returncode < 0:
        out += f"\n(killed by signal {-proc.returncode}; may be {timeout}s timeout)"
    return out


# Tool registry: name -> (description, param schema, function).
# Param types use "?" suffix to mark optional. Descriptions are what the LLM sees.
TOOLS = {
    "read": (
        "Read a text file with line numbers. offset is 1-indexed; default limit 2000 lines. "
        "Output format is 'N| <content>' - the 'N| ' prefix is NOT part of the file content.",
        {"path": "string", "offset": "integer?", "limit": "integer?"},
        read,
    ),
    "write": (
        "Write content to file (overwrites if it exists; does not create parent directories).",
        {"path": "string", "content": "string"},
        write,
    ),
    "edit": (
        "Replace `old` with `new` in file. `old` must match uniquely unless all=true. "
        "Per-line leading/trailing whitespace is tolerated. If `old` is empty, the file "
        "is created/overwritten with `new`. Never include the 'N| ' line-number prefix "
        "from read() output in `old` or `new`.",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        edit,
    ),
    "glob": (
        "Find files matching a glob pattern (e.g. '**/*.py'), sorted newest first. "
        "`pattern` is joined onto `path` (default '.').",
        {"pattern": "string", "path": "string?"},
        glob,
    ),
    "grep": (
        f"Search files under `path` (default '.') for a Python regex. Skips binaries "
        f"and hidden dirs (.git, .venv, etc). Caps at {GREP_CAP} matches.",
        {"pattern": "string", "path": "string?"},
        grep,
    ),
    "explore": (
        "Spawn a sub-agent with the same tools to investigate something. "
        "You only see its final summary - tool calls and intermediate steps are hidden. "
        "Use for open-ended research ('find where X is handled', 'summarize module Y') "
        "to keep your own context clean.",
        {"prompt": "string"},
        explore,
    ),
    "bash": (
        f"Run a shell command in the harness cwd. stderr is merged into stdout. "
        f"Killed after `timeout` seconds (default {BASH_TIMEOUT_DEFAULT}, "
        f"pass 0 to disable for long-running commands).",
        {"cmd": "string", "timeout": "integer?"},
        bash,
    ),
}


def run_tool(name, args):
    if name not in TOOLS:
        return f"error: unknown tool {name!r}"
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {type(err).__name__}: {err}"


def make_schema():
    schema = []
    for name, (description, params, _fn) in TOOLS.items():
        properties, required = {}, []
        for param_name, param_type in params.items():
            optional = param_type.endswith("?")
            properties[param_name] = {"type": param_type.rstrip("?")}
            if not optional:
                required.append(param_name)
        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return schema


SCHEMA = make_schema()


def call_api(messages):
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps({"model": MODEL_NAME, "messages": messages, "tools": SCHEMA}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code}: {body}") from None


def separator():
    try:
        cols = min(os.get_terminal_size().columns, 80)
    except OSError:
        cols = 80
    return f"{DIM}{'─' * cols}{RESET}"


def render_markdown(text):
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)


SYSTEM_PROMPT = (
    "You are a concise coding assistant operating in a terminal.\n"
    f"cwd: {os.getcwd()}"
)


def main():
    yolo_tag = f" | {RED}YOLO{RESET}" if YOLO else ""
    print(f"{BOLD}nanocode{RESET} | {DIM}{MODEL_NAME} | {BASE_URL} | {os.getcwd()}{RESET}{yolo_tag}\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            print(separator())
            user_input = input(f"{BOLD}{BLUE}❯{RESET} ").strip()
            print(separator())
            if not user_input:
                continue
            if user_input in ("/q", "exit"):
                break
            if user_input == "/c":
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                print(f"{GREEN}⏺ Cleared conversation{RESET}")
                continue

            messages.append({"role": "user", "content": user_input})

            while True:
                response = call_api(messages)
                message = response["choices"][0]["message"]
                content = message.get("content") or ""
                tool_calls = message.get("tool_calls") or []

                if content:
                    print(f"\n{CYAN}⏺{RESET} {render_markdown(content)}")

                # Providers disagree on the field name for interleaved reasoning;
                # pass through whichever the server returned, verbatim.
                assistant_msg = {"role": "assistant", "content": content}
                for key in ("reasoning_content", "reasoning", "reasoning_details"):
                    if message.get(key) is not None:
                        assistant_msg[key] = message[key]
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                messages.append(assistant_msg)

                if not tool_calls:
                    break

                for call in tool_calls:
                    tool_name = call["function"]["name"]
                    try:
                        tool_args = json.loads(call["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        tool_args = {}

                    arg_preview = str(next(iter(tool_args.values()), ""))[:50]
                    print(f"\n{GREEN}⏺ {tool_name.capitalize()}{RESET}({DIM}{arg_preview}{RESET})")

                    result = run_tool(tool_name, tool_args)
                    result_lines = result.split("\n")
                    preview = result_lines[0][:60]
                    if len(result_lines) > 1:
                        preview += f" ... +{len(result_lines) - 1} lines"
                    elif len(result_lines[0]) > 60:
                        preview += "..."
                    print(f"  {DIM}⎿  {preview}{RESET}")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.get("id", ""),
                        "content": result,
                    })

            print()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}⏺ Error: {err}{RESET}")


if __name__ == "__main__":
    main()
