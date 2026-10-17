"""Command line: python -m agent "How many .md files are in docs?" """

from __future__ import annotations

import sys

from dotenv import load_dotenv

from agent.llm import AnthropicLLM
from agent.log import RunLogger
from agent.loop import run_agent


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: python -m agent "your task"')
        return 2
    load_dotenv()
    task = " ".join(sys.argv[1:])
    logger = RunLogger(task)
    result = run_agent(task, AnthropicLLM(), logger=logger)
    print(result.answer)
    print(
        f"\n[{result.steps} model calls · {result.input_tokens} in / "
        f"{result.output_tokens} out tokens · log: {logger.path}]",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
