"""Run logs: one JSON object per line in runs/<timestamp>.jsonl.

Why JSONL: you can append line by line while the agent runs, and if it crashes
you still have everything up to the crash. Every later week reads these logs.

Usage inside your loop:

    logger.log("model_call", step=1, stop_reason="tool_use", input_tokens=812, output_tokens=40)
    logger.log("tool_call", step=1, name="read_file", input={"path": "a.md"},
               is_error=False, output_preview=output[:200])
    logger.log("final", step=3, answer="...")
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


class RunLogger:
    def __init__(self, task: str, runs_dir: Path = RUNS_DIR):
        runs_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        self.path = runs_dir / f"{stamp}.jsonl"
        self._t0 = time.monotonic()
        self.log("start", task=task)

    def log(self, event: str, **fields: Any) -> None:
        row = {"t": round(time.monotonic() - self._t0, 3), "event": event, **fields}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
