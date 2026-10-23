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
from urllib.parse import urlparse

import httpx

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
    """Turn a path from the model into a real path that is guaranteed to be inside root."""
    if root is None:
        root = WORKSPACE
    root = root.resolve()
    target = (root / rel).resolve()
    if not target.is_relative_to(root):
        raise ToolError(f"Path '{rel}' is outside the workspace")
    return target


def list_dir(path: str = ".") -> str:
    """List a workspace folder: one entry per line, sorted, folders end with '/'.

    Raises ToolError if the path is outside the workspace or is not a folder.
    """
    p = safe_path(path)
    if not p.is_dir():
        raise ToolError(f"Path '{path}' is not a directory")

    names = [entry.name + ("/" if entry.is_dir() else "") for entry in p.iterdir()]
    return "\n".join(sorted(names)) or "(empty folder)"


def read_file(path: str) -> str:
    """Return a workspace file's text, truncated to MAX_OUTPUT_CHARS.

    Raises ToolError if the path is outside the workspace or is not a file.
    """
    p = safe_path(path)
    if not p.is_file():
        raise ToolError(f"Path '{path}' is not a file")
    text = p.read_text(encoding="utf-8", errors="replace")
    return truncate(text)


def fetch_url(url: str) -> str:
    """Fetch an http(s) URL and return the response body, truncated.

    Raises ToolError for other URL schemes, network errors, or a non-2xx status.
    """
    if urlparse(url).scheme not in ("http", "https"):
        raise ToolError(f"URL '{url}' has unsupported scheme (only http:// and https:// allowed)")
    try:
        resp = httpx.get(url, timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True)
    except httpx.HTTPError as e:
        raise ToolError(f"Could not fetch '{url}': {e}") from e
    if not resp.is_success:
        raise ToolError(f"Fetching '{url}' failed with HTTP {resp.status_code}")
    return truncate(resp.text)


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
    {
        "name": "list_dir",
        "description": (
            "List the contents of a directory in the workspace. "
            "Paths are relative to the workspace root, e.g. 'docs'. "
            "Omit path or use '.' to list the workspace root. "
            "Returns one entry per line, sorted; folders end with '/'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path relative to the workspace root."}
            },
            "required": [],
        },
    },
    {
        "name": "fetch_url",
         "description": (
            "Fetch a web page over HTTP or HTTPS and return the raw response body "
            "(HTML for web pages). Other URL schemes are rejected. "
            "Long pages are truncated."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch."}
            },
            "required": ["url"],
        },
    },
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
