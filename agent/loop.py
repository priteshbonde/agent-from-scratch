"""The agent loop. THE file of Week 1, and you write it.

Every agent framework (LangChain, CrewAI, the Agent SDK...) is this loop plus
extras. Write it by hand once and frameworks stop being magic.

Picture it:

    you ──task──▶ model ──"use read_file('a.md')"──▶ your code runs it
     ▲                                                   │
     └──────────── result goes back to the model ◀──────┘
                   ...repeat until the model just answers.

Tests: tests/test_loop.py. They use FakeLLM, so they're free. Run `pytest -q`
and turn them green one by one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from agent.tools import TOOLS, run_tool as default_run_tool

SYSTEM_PROMPT = (
    "You are a careful assistant with access to a small file workspace and the web. "
    "Use tools to find facts; never guess file contents. "
    "When you have the answer, reply with it directly and briefly."
)
MAX_STEPS = 10


class TooManySteps(Exception):
    """The model kept asking for tools and never finished."""


@dataclass
class AgentResult:
    answer: str
    steps: int                      # how many times we called the model
    input_tokens: int = 0
    output_tokens: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)


def run_agent(
    task: str,
    llm,                                            # AnthropicLLM or FakeLLM
    tools: list[dict[str, Any]] = TOOLS,
    run_tool: Callable[[str, dict], str] = default_run_tool,
    logger=None,                                    # agent.log.RunLogger or None
    max_steps: int = MAX_STEPS,
) -> AgentResult:
    """Run one task to completion."""

    messages = [{"role": "user", "content": task}]
    input_tokens = 0
    output_tokens = 0
    for step in range(1, max_steps + 1):
        response = llm.create(system=SYSTEM_PROMPT, messages=messages, tools=tools)
        input_tokens += response.input_tokens
        output_tokens += response.output_tokens
        if logger:
            logger.log("model_call", step=step, stop_reason=response.stop_reason, input_tokens=response.input_tokens, output_tokens=response.output_tokens)
        messages.append({"role": "assistant", "content": response.content})
        
        if response.stop_reason != "tool_use":
            if logger:
                logger.log("final", step=step, answer=response.text())
            return AgentResult(
                answer=response.text(),
                steps=step,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                messages=messages
            )
        
        tool_results = []
        for block in response.tool_uses():
            try:
                output = run_tool(block["name"], block["input"])
                is_error = False
            except Exception as e:
                output = f"{type(e).__name__}: {e}"
                is_error = True
            
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": output,
                "is_error": is_error
            })
            if logger:
                logger.log("tool_call", step=step, name=block["name"], input=block["input"], is_error=is_error, output_preview=output[:200])
        
        messages.append({"role": "user", "content": tool_results})
        
    raise TooManySteps(f"No answer after {max_steps} steps")
