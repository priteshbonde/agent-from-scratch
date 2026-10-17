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
    """Run one task to completion.

    TODO(week1-step3). The recipe:

    1. messages = [{"role": "user", "content": task}]
    2. Repeat up to max_steps times:
       a. response = llm.create(system=SYSTEM_PROMPT, messages=messages, tools=tools)
          Add response.input_tokens / output_tokens to running totals.
       b. Append the model's reply FIRST:
              {"role": "assistant", "content": response.content}
          (Beginner bug #1: forgetting this. The API then rejects your tool results.)
       c. If response.stop_reason != "tool_use": you're done.
          Return AgentResult(answer=response.text(), steps=..., tokens..., messages=messages)
       d. For EACH block in response.tool_uses():
              try:  output = run_tool(block["name"], block["input"]); is_error = False
              except Exception as e:  output = f"{type(e).__name__}: {e}"; is_error = True
          Build a result:
              {"type": "tool_result", "tool_use_id": block["id"],
               "content": output, "is_error": is_error}
          (Beginner bug #2: a tool_use_id that doesn't match block["id"].)
          (Beginner bug #3: letting the exception crash the loop. Send it back;
           the model often fixes its own mistake.)
       e. Append ONE user message holding ALL the results from this turn:
              {"role": "user", "content": [result1, result2, ...]}
       f. If logger: logger.log(...) what happened this step (see agent/log.py).
    3. Out of steps: raise TooManySteps(f"No answer after {max_steps} steps")
    """
    raise NotImplementedError("Week 1, Step 3: write the loop. Read the docstring above.")
