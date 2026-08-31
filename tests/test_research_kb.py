"""research_kb and MCP tool consistency tests for GameChanger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "data" / "research_assets.json"


def test_research_assets_shape():
    data = json.loads(ASSETS.read_text(encoding="utf-8"))
    assert "glossary" in data and "competitors" in data and "templates" in data
    assert len(data["competitors"]) >= 3
    assert "research" in data["templates"]


@pytest.mark.asyncio
async def test_research_kb_competitors_and_glossary():
    from app.tool.research_kb import ResearchKB

    tool = ResearchKB()
    comps = await tool.execute(action="competitors")
    assert "Hudl" in comps or "GameChanger" in comps

    term = await tool.execute(action="glossary", query="MCP")
    assert "Model Context Protocol" in term or "MCP" in term

    tpl = await tool.execute(action="template", query="research")
    assert "Briefing" in tpl or "Template" in tpl


def test_mcp_tools_match_assets():
    import importlib.util

    path = ROOT / "mcp_servers" / "gamechanger_research_mcp.py"
    spec = importlib.util.spec_from_file_location("gamechanger_research_mcp", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    text = mod.list_competitors()
    assert "Hudl" in text or "GameChanger" in text
    assert "MCP" in mod.lookup_glossary("MCP")
    assert "Template" in mod.get_task_template("docs")
