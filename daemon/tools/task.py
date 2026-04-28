"""Task tool: spawn a sub-agent and return only its final answer."""

from __future__ import annotations

import json
from typing import Any

from daemon.tools.base import BaseTool
from daemon.tools.registry import register_tool


@register_tool
class TaskTool(BaseTool):
    name = "task"
    description = (
        "Spawn a sub-agent with the same tools to handle a delegated task. "
        "You only see its final summary - tool calls and intermediate steps are hidden. "
        "Use for open-ended research ('find where X is handled', 'summarize module Y'), "
        "refactoring, or any other sub-task you want to offload to keep your own context clean."
    )
    parameters = {"prompt": "string"}

    def execute(self, args: dict[str, Any]) -> str:
        # Local imports keep the module load order clean: this tool is
        # registered at package import, but the API client and registry
        # only need to resolve when a `task` call actually fires.
        from daemon.core.api import call_api
        from daemon.core.prompt import get_default_system_prompt
        from daemon.tools.registry import get_schema, run_tool

        sub: list[dict[str, Any]] = [
            {"role": "system", "content": get_default_system_prompt()},
            {"role": "user", "content": args["prompt"]},
        ]
        schema = get_schema()

        while True:
            message = call_api(sub, tools=schema)["choices"][0]["message"]
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}
            # Providers disagree on the field name for interleaved reasoning;
            # echo whichever the server returned.
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
