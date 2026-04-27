#!/usr/bin/env python3
"""nanocode - minimal agentic coding harness for any OpenAI-compatible endpoint"""

import glob as globlib, json, os, re, subprocess, urllib.error, urllib.request


def load_dotenv(path=".env"):
    """Load KEY=VALUE lines from a .env file into os.environ (does not overwrite)."""
    if not os.path.isfile(path):
        return
    for raw in open(path):
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

# ANSI colors
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, YELLOW, RED = (
    "\033[34m",
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
)


# --- Tool implementations ---

MAX_LINES = 2000
MAX_LINE_LEN = 2000


def read(args):
    path = args["path"]
    offset = max(1, args.get("offset", 1))  # 1-indexed
    limit = args.get("limit", MAX_LINES)

    with open(path, "rb") as f:
        if b"\x00" in f.read(4096):
            return f"error: {path} looks binary"

    with open(path, errors="replace") as f:
        all_lines = f.read().splitlines()
    total = len(all_lines)
    if total and offset > total:
        return f"error: offset {offset} exceeds file length ({total} lines)"

    selected = all_lines[offset - 1 : offset - 1 + limit]
    out = []
    for idx, line in enumerate(selected):
        if len(line) > MAX_LINE_LEN:
            line = line[:MAX_LINE_LEN] + "... (line truncated)"
        out.append(f"{offset + idx:4}| {line}")

    end = offset + len(selected) - 1
    if end >= total:
        out.append(f"\n(end of file - {total} lines total)")
    else:
        out.append(f"\n(showing {offset}-{end} of {total}, use offset={end + 1} to continue)")
    return "\n".join(out)


def write(args):
    with open(args["path"], "w") as f:
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
        with open(path, "w") as f:
            f.write(new)
        return "ok (created)"

    text = open(path).read()
    candidate, count = _find_match(text, old)
    if candidate is None:
        return "error: old not found in file"
    if count > 1 and not args.get("all"):
        return f"error: old matches {count} places, add more context or pass all=true"

    replacement = (
        text.replace(candidate, new)
        if args.get("all")
        else text.replace(candidate, new, 1)
    )
    with open(path, "w") as f:
        f.write(replacement)
    return "ok"


def glob(args):
    pattern = (args.get("path", ".") + "/" + args["pat"]).replace("//", "/")
    files = globlib.glob(pattern, recursive=True)
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,
    )
    return "\n".join(files) or "none"


def grep(args):
    pattern = re.compile(args["pat"])
    hits = []
    for filepath in globlib.glob(args.get("path", ".") + "/**", recursive=True):
        try:
            for line_num, line in enumerate(open(filepath), 1):
                if pattern.search(line):
                    hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
        except Exception:
            pass
    return "\n".join(hits[:50]) or "none"


def bash(args):
    proc = subprocess.Popen(
        args["cmd"], shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True
    )
    output_lines = []
    try:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                print(f"  {DIM}│ {line.rstrip()}{RESET}", flush=True)
                output_lines.append(line)
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append("\n(timed out after 30s)")
    return "".join(output_lines).strip() or "(empty)"


# --- Tool definitions: (description, schema, function) ---

TOOLS = {
    "read": (
        "Read file with line numbers. offset is 1-indexed; default limit 2000 lines. "
        "Output format is 'N| <content>' - the 'N| ' prefix is NOT part of the file.",
        {"path": "string", "offset": "number?", "limit": "number?"},
        read,
    ),
    "write": (
        "Write content to file",
        {"path": "string", "content": "string"},
        write,
    ),
    "edit": (
        "Replace old with new in file. old must match uniquely unless all=true. "
        "Per-line leading/trailing whitespace is tolerated. If old is empty, the "
        "file is created/overwritten with new. Never include the 'N| ' line-number "
        "prefix from read output in old/new.",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        edit,
    ),
    "glob": (
        "Find files by pattern, sorted by mtime",
        {"pat": "string", "path": "string?"},
        glob,
    ),
    "grep": (
        "Search files for regex pattern",
        {"pat": "string", "path": "string?"},
        grep,
    ),
    "bash": (
        "Run shell command",
        {"cmd": "string"},
        bash,
    ),
}


def run_tool(name, args):
    if name not in TOOLS:
        return f"error: unknown tool {name!r}"
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"


def make_schema():
    result = []
    for name, (description, params, _fn) in TOOLS.items():
        properties = {}
        required = []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            properties[param_name] = {
                "type": "integer" if base_type == "number" else base_type
            }
            if not is_optional:
                required.append(param_name)
        result.append(
            {
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
            }
        )
    return result


def call_api(messages):
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(
            {
                "model": MODEL_NAME,
                "messages": messages,
                "tools": make_schema(),
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    try:
        response = urllib.request.urlopen(request)
        return json.loads(response.read())
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code}: {body}") from None


def separator():
    return f"{DIM}{'─' * min(os.get_terminal_size().columns, 80)}{RESET}"


def render_markdown(text):
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)


def main():
    print(f"{BOLD}nanocode{RESET} | {DIM}{MODEL_NAME} | {BASE_URL} | {os.getcwd()}{RESET}\n")
    system_prompt = f"Concise coding assistant. cwd: {os.getcwd()}"
    messages = [{"role": "system", "content": system_prompt}]

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
                messages = [{"role": "system", "content": system_prompt}]
                print(f"{GREEN}⏺ Cleared conversation{RESET}")
                continue

            messages.append({"role": "user", "content": user_input})

            # agentic loop: keep calling API until no more tool calls
            while True:
                response = call_api(messages)
                message = response["choices"][0]["message"]
                content = message.get("content") or ""
                tool_calls = message.get("tool_calls") or []

                if content:
                    print(f"\n{CYAN}⏺{RESET} {render_markdown(content)}")

                # Preserve reasoning across tool calls. Providers use different
                # field names for interleaved thinking; pass through whichever
                # the server returned, verbatim. (DeepSeek/Qwen/older vLLM:
                # 'reasoning_content'; newer vLLM/OpenRouter: 'reasoning';
                # MiniMax M2 with reasoning_split=true: 'reasoning_details'.)
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
                    print(
                        f"\n{GREEN}⏺ {tool_name.capitalize()}{RESET}({DIM}{arg_preview}{RESET})"
                    )

                    result = run_tool(tool_name, tool_args)
                    result_lines = result.split("\n")
                    preview = result_lines[0][:60]
                    if len(result_lines) > 1:
                        preview += f" ... +{len(result_lines) - 1} lines"
                    elif len(result_lines[0]) > 60:
                        preview += "..."
                    print(f"  {DIM}⎿  {preview}{RESET}")

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": result,
                        }
                    )

            print()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}⏺ Error: {err}{RESET}")


if __name__ == "__main__":
    main()
