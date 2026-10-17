"""Tools: the hands you lend the model.

A tool has two halves:

1. A SCHEMA the model reads (name, description, input_schema). This is the
   menu card. The model never sees your Python code, only this card, so the
   description is a prompt: write it for a smart person who can't read code.
2. A FUNCTION your code runs when the model asks for it.

Safety rule for this file: the model is an untrusted user. Anything it sends
(paths, URLs) gets checked before you touch the disk or the network.

WEEK 1 TODOs (Step 2 + Step 4) are marked below. Tests in tests/test_tools.py
tell you when each one is right.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"
MAX_OUTPUT_CHARS = 5000   # big outputs blow up the context window (Week 2 problem)
FETCH_TIMEOUT_SECONDS = 10


class ToolError(Exception):
    """An error the model should see and can recover from (bad path, missing file...)."""


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated, {len(text) - limit} more chars]"


def safe_path(rel: str, root: Path | None = None) -> Path:
    """Turn a path from the model into a real path that is guaranteed to be inside root.

    TODO(week1-step4):
      - root defaults to WORKSPACE (read the global at call time, so tests can swap it)
      - resolve (root / rel) to an absolute path; .resolve() also follows symlinks
      - if the result is not root itself or inside root, raise ToolError
        hint: Path.is_relative_to()
      - "../README.md", "/etc/passwd" and "docs/../../x" must all be rejected
    """
    raise NotImplementedError("Week 1, Step 4: write safe_path")


def list_dir(path: str = ".") -> str:
    """TODO(week1-step4): one entry per line, sorted, folders end with "/".
    Use safe_path. Raise ToolError if the folder doesn't exist.
    """
    raise NotImplementedError("Week 1, Step 4: write list_dir")


def read_file(path: str) -> str:
    """TODO(week1-step4): return the file's text, passed through truncate().
    Use safe_path. Raise ToolError if it's missing or is a folder.
    """
    raise NotImplementedError("Week 1, Step 4: write read_file")


def fetch_url(url: str) -> str:
    """TODO(week1-step4): GET the page with httpx, return its text, truncated.
      - only http:// and https:// (reject file://, ftp://... with ToolError)
      - timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True
      - a non-2xx status becomes a ToolError the model can read
    """
    raise NotImplementedError("Week 1, Step 4: write fetch_url")


# --- schemas: what the model sees -------------------------------------------

TOOLS: list[dict[str, Any]] = [
    # Worked example. Copy its shape for the other two.
    {
        "name": "read_file",
        "description": (
            "Read a text file from the workspace and return its contents. "
            "Paths are relative to the workspace root, e.g. 'docs/intro.md'. "
            "Long files are truncated."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to the workspace root."}
            },
            "required": ["path"],
        },
    },
    # TODO(week1-step2): schema for list_dir   (path is optional, default ".")
    # TODO(week1-step2): schema for fetch_url  (url is required)
]

REGISTRY: dict[str, Callable[..., str]] = {
    "read_file": read_file,
    "list_dir": list_dir,
    "fetch_url": fetch_url,
}


def run_tool(name: str, args: dict[str, Any]) -> str:
    """Look up a tool by name and call it. Errors are raised; the loop decides what to do."""
    if name not in REGISTRY:
        raise ToolError(f"Unknown tool: {name}. Available: {', '.join(REGISTRY)}")
    return REGISTRY[name](**args)
