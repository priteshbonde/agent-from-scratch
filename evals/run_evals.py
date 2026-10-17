"""Tiny eval: run every task in evals/tasks.jsonl against the REAL model and score it.

    python -m evals.run_evals            # all tasks
    python -m evals.run_evals --only 3   # just task 3

Costs a few cents with Haiku. Grader is deliberately crude for Week 1:
pass = the expected string appears in the answer (case-insensitive).
Week 5 replaces this with proper graders.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from agent.llm import AnthropicLLM
from agent.log import RunLogger
from agent.loop import run_agent

HERE = Path(__file__).resolve().parent


def grade(answer: str, expected: str) -> bool:
    return expected.lower() in answer.lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, help="run a single task id")
    args = ap.parse_args()
    load_dotenv()

    tasks = [json.loads(line) for line in (HERE / "tasks.jsonl").read_text().splitlines() if line.strip()]
    if args.only:
        tasks = [t for t in tasks if t["id"] == args.only]

    llm = AnthropicLLM()
    rows = []
    for t in tasks:
        logger = RunLogger(t["task"])
        try:
            r = run_agent(t["task"], llm, logger=logger)
            ok = grade(r.answer, t["expected"])
            row = {"id": t["id"], "pass": ok, "steps": r.steps,
                   "tokens": r.input_tokens + r.output_tokens, "answer": r.answer}
        except Exception as e:  # a crash is a fail, not a stop
            row = {"id": t["id"], "pass": False, "steps": None, "tokens": None,
                   "answer": f"CRASH {type(e).__name__}: {e}"}
        row["log"] = str(logger.path)
        rows.append(row)
        mark = "PASS" if row["pass"] else "FAIL"
        print(f"[{mark}] #{t['id']:>2} steps={row['steps']} tokens={row['tokens']}  {t['task'][:60]}")
        if not row["pass"]:
            print(f"        expected '{t['expected']}' in: {row['answer'][:160]!r}")

    score = sum(r["pass"] for r in rows)
    print(f"\nScore: {score}/{len(rows)}  model={llm.model}")

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"{stamp}.json").write_text(json.dumps(
        {"model": llm.model, "score": score, "total": len(rows), "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
