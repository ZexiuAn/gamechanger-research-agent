"""GameChanger Research MCP Service (stdio).

Provides: Competitors list, Glossary, Task Templates - standard hot-pluggable MCP tool service.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "data" / "research_assets.json"

mcp = FastMCP("gamechanger_research")


def _load() -> dict:
    return json.loads(ASSETS.read_text(encoding="utf-8"))


@mcp.tool()
def list_competitors() -> str:
    """List common benchmark competitors and focus areas (Local KB)."""
    data = _load()
    lines = ["GameChanger Benchmark Competitors (Local Knowledge Base):"]
    for item in data.get("competitors", []):
        lines.append(
            f"- {item['name']} | Focus: {item['focus']} | Notes: {item.get('notes', '')}"
        )
    return "\n".join(lines)


@mcp.tool()
def lookup_glossary(term: str) -> str:
    """Lookup technical/product glossary definitions."""
    data = _load()
    glossary = data.get("glossary", {})
    key = (term or "").strip()
    if not key:
        return "Please provide a search term."
    if key in glossary:
        return f"{key}: {glossary[key]}"
    for k, v in glossary.items():
        if key.lower() in k.lower() or k.lower() in query_term(key):
            return f"{k}: {v}"
    known = ", ".join(glossary.keys())
    return f"Term '{key}' not found. Known terms: {known}"


def query_term(k: str) -> str:
    return k.lower()


@mcp.tool()
def get_task_template(task_id: str = "research") -> str:
    """Get research or doc digest outline template and suggested output path."""
    data = _load()
    templates = data.get("templates", {})
    tid = (task_id or "research").strip()
    tpl = templates.get(tid) or templates.get("research")
    if not tpl:
        return "No template available."
    outline = "\n".join(f"  {i+1}. {x}" for i, x in enumerate(tpl.get("outline", [])))
    return (
        f"Template: {tpl.get('title')} (id={tpl.get('id')})\n"
        f"Output Target: {tpl.get('output_file')}\n"
        f"Outline:\n{outline}"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
