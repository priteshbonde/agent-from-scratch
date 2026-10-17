"""Talking to the model.

Two classes with the same shape:

- AnthropicLLM: the real model. Costs money, needs ANTHROPIC_API_KEY.
- FakeLLM:      replays replies you scripted. Free. Used in tests.

Your loop only ever calls `llm.create(...)`, so it can't tell which one it got.
That is the trick that lets you test agent logic without an API key.

Content blocks are plain dicts in the exact shape the Messages API uses, so you
can append `response.content` straight back into `messages`:

    {"type": "text", "text": "..."}
    {"type": "tool_use", "id": "toolu_...", "name": "read_file", "input": {...}}
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from typing import Any

DEFAULT_MODEL = "claude-haiku-5-5"  # cheapest; use it for all development


@dataclass
class LLMResponse:
    content: list[dict[str, Any]]
    stop_reason: str  # "end_turn" | "tool_use" | "max_tokens" | ...
    input_tokens: int = 0
    output_tokens: int = 0

    def tool_uses(self) -> list[dict[str, Any]]:
        return [b for b in self.content if b["type"] == "tool_use"]

    def text(self) -> str:
        return "".join(b["text"] for b in self.content if b["type"] == "text")


class AnthropicLLM:
    def __init__(self, model: str | None = None, max_tokens: int = 1024):
        import anthropic  # imported here so tests never need it

        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self.model = model or os.environ.get("AGENT_MODEL", DEFAULT_MODEL)
        self.max_tokens = max_tokens

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        )
        blocks: list[dict[str, Any]] = []
        for b in resp.content:
            if b.type == "text":
                blocks.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        return LLMResponse(
            content=blocks,
            stop_reason=resp.stop_reason,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )


class FakeLLM:
    """Returns scripted replies in order and records every `messages` it was sent."""

    def __init__(self, script: list[LLMResponse]):
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self.calls.append(copy.deepcopy(messages))  # snapshot: what the model "saw"
        if not self.script:
            raise AssertionError("FakeLLM ran out of scripted replies: the loop called the model too many times")
        return self.script.pop(0)


# --- helpers for writing scripts in tests -----------------------------------

def say(text: str, input_tokens: int = 10, output_tokens: int = 5) -> LLMResponse:
    """A final answer: the model is done."""
    return LLMResponse([{"type": "text", "text": text}], "end_turn", input_tokens, output_tokens)


def use(*calls: tuple[str, dict, str], text: str | None = None,
        input_tokens: int = 10, output_tokens: int = 5) -> LLMResponse:
    """The model asks for one or more tools. Each call is (name, input, id)."""
    blocks: list[dict[str, Any]] = [{"type": "text", "text": text}] if text else []
    for name, args, tool_id in calls:
        blocks.append({"type": "tool_use", "id": tool_id, "name": name, "input": args})
    return LLMResponse(blocks, "tool_use", input_tokens, output_tokens)
