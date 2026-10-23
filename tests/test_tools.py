"""Spec for agent/tools.py. No network, no API key.

Run:  pytest -q tests/test_tools.py
"""

import pytest

from agent import tools
from agent.tools import REGISTRY, TOOLS, ToolError, list_dir, read_file, safe_path


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """A throwaway workspace so tests never depend on the real one."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("hello")
    (tmp_path / "big.txt").write_text("x" * 20_000)
    (tmp_path / "top.txt").write_text("top")
    monkeypatch.setattr(tools, "WORKSPACE", tmp_path)
    return tmp_path


# --- safe_path: the most important function in this file --------------------

def test_safe_path_allows_inside(ws):
    assert safe_path("docs/a.md") == (ws / "docs" / "a.md").resolve()


@pytest.mark.parametrize("bad", ["../secret.txt", "/etc/passwd", "docs/../../x", "docs/../../../etc"])
def test_safe_path_blocks_escape(ws, bad):
    with pytest.raises(ToolError):
        safe_path(bad)


# --- read_file / list_dir ---------------------------------------------------

def test_read_file(ws):
    assert read_file("docs/a.md") == "hello"


def test_read_file_missing_is_tool_error(ws):
    with pytest.raises(ToolError):
        read_file("nope.md")


def test_read_file_folder_is_tool_error(ws):
    with pytest.raises(ToolError):
        read_file("docs")


def test_read_file_truncates_big_files(ws):
    out = read_file("big.txt")
    assert len(out) < 6_000
    assert "truncated" in out


def test_list_dir(ws):
    assert list_dir(".").splitlines() == ["big.txt", "docs/", "top.txt"]


def test_list_dir_missing_is_tool_error(ws):
    with pytest.raises(ToolError):
        list_dir("nope")


# --- fetch_url safety (no real network call) --------------------------------

@pytest.mark.parametrize("bad", ["file:///etc/passwd", "ftp://example.com", "example.com"])
def test_fetch_url_rejects_non_http(bad):
    with pytest.raises(ToolError):
        tools.fetch_url(bad)


# --- schemas ----------------------------------------------------------------

def test_every_registered_tool_has_a_schema():
    assert {t["name"] for t in TOOLS} == set(REGISTRY)


@pytest.mark.parametrize("schema", TOOLS, ids=lambda s: s["name"])
def test_schema_shape(schema):
    assert schema["description"].strip()
    assert schema["input_schema"]["type"] == "object"
    assert "properties" in schema["input_schema"]


def test_list_dir_empty_folder(ws):
    (ws / "empty").mkdir()
    assert list_dir("empty") == "(empty folder)"
