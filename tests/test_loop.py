"""Spec for agent/loop.py. All free: FakeLLM plays the model, a stub plays the tools.

Run:  pytest -q tests/test_loop.py
"""

import pytest

from agent.llm import FakeLLM, say, use
from agent.loop import TooManySteps, run_agent


def stub_tools(name, args):
    """Pretend tools, so loop tests don't depend on tools.py."""
    if name == "read_file":
        return f"<contents of {args['path']}>"
    if name == "boom":
        raise RuntimeError("disk on fire")
    raise KeyError(f"Unknown tool: {name}")


def run(script, **kw):
    llm = FakeLLM(script)
    result = run_agent("test task", llm, tools=[], run_tool=stub_tools, **kw)
    return result, llm


def test_answers_directly_when_no_tool_needed():
    result, llm = run([say("Paris")])
    assert result.answer == "Paris"
    assert result.steps == 1
    assert llm.calls[0] == [{"role": "user", "content": "test task"}]


def test_tool_result_goes_back_to_the_model():
    result, llm = run([
        use(("read_file", {"path": "a.md"}, "toolu_A")),
        say("a.md says hello"),
    ])
    assert result.answer == "a.md says hello"
    assert result.steps == 2

    second_call = llm.calls[1]
    # 1) the task, 2) the model's own tool request, 3) our tool result
    assert [m["role"] for m in second_call] == ["user", "assistant", "user"]
    assert second_call[1]["content"][0]["type"] == "tool_use"

    tool_result = second_call[2]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_A"
    assert tool_result["content"] == "<contents of a.md>"
    assert tool_result["is_error"] is False


def test_parallel_tool_calls_return_in_one_message():
    _, llm = run([
        use(("read_file", {"path": "a.md"}, "id1"), ("read_file", {"path": "b.md"}, "id2")),
        say("done"),
    ])
    results_msg = llm.calls[1][-1]
    assert results_msg["role"] == "user"
    assert [r["tool_use_id"] for r in results_msg["content"]] == ["id1", "id2"]


def test_tool_error_is_sent_back_not_raised():
    result, llm = run([
        use(("boom", {}, "id1")),
        say("recovered"),
    ])
    assert result.answer == "recovered"
    tool_result = llm.calls[1][-1]["content"][0]
    assert tool_result["is_error"] is True
    assert "disk on fire" in tool_result["content"]


def test_unknown_tool_is_an_error_result_too():
    _, llm = run([use(("teleport", {}, "id1")), say("ok")])
    tool_result = llm.calls[1][-1]["content"][0]
    assert tool_result["is_error"] is True


def test_gives_up_after_max_steps():
    forever = [use(("read_file", {"path": "a.md"}, f"id{i}")) for i in range(5)]
    with pytest.raises(TooManySteps):
        run(forever, max_steps=3)


def test_counts_tokens_across_steps():
    result, _ = run([
        use(("read_file", {"path": "a.md"}, "id1"), input_tokens=100, output_tokens=20),
        say("done", input_tokens=150, output_tokens=10),
    ])
    assert result.input_tokens == 250
    assert result.output_tokens == 30
