from __future__ import annotations

import json
from pathlib import Path

from app.tool.base import BaseTool

ASSETS = Path(__file__).resolve().parents[2] / "data" / "research_assets.json"


class ResearchKB(BaseTool):
    """Local Research Knowledge Base (Glossary / Competitor Benchmarks / Task Templates)."""

    name: str = "research_kb"
    description: str = (
        "Query GameChanger local research knowledge: competitors (benchmark list), glossary (terminology), "
        "template (task outline). Use it prior to web search to align scope and output structure."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["competitors", "glossary", "template"],
                "description": "The query type to execute.",
            },
            "query": {
                "type": "string",
                "description": "For glossary: term name; for template: research or docs.",
            },
        },
        "required": ["action"],
    }

    async def execute(self, action: str, query: str = "") -> str:
        data = json.loads(ASSETS.read_text(encoding="utf-8"))
        action = (action or "").strip().lower()
        query = (query or "").strip()

        if action == "competitors":
            lines = ["GameChanger Benchmark Competitors (Local Knowledge Base):"]
            for item in data.get("competitors", []):
                lines.append(
                    f"- {item['name']} | Focus: {item['focus']} | Notes: {item.get('notes', '')}"
                )
            return "\n".join(lines)

        if action == "glossary":
            glossary = data.get("glossary", {})
            if not query:
                return "Please provide query term. Known: " + ", ".join(glossary.keys())
            if query in glossary:
                return f"{query}: {glossary[query]}"
            for k, v in glossary.items():
                if query.lower() in k.lower() or k.lower() in query.lower():
                    return f"{k}: {v}"
            return f"Term '{query}' not found. Known: " + ", ".join(glossary.keys())

        if action == "template":
            templates = data.get("templates", {})
            tid = query or "research"
            tpl = templates.get(tid) or templates.get("research")
            outline = "\n".join(
                f"  {i+1}. {x}" for i, x in enumerate(tpl.get("outline", []))
            )
            return (
                f"Template: {tpl.get('title')} (id={tpl.get('id')})\n"
                f"Suggested Output: {tpl.get('output_file')}\n"
                f"Outline:\n{outline}"
            )

        return "action supports competitors / glossary / template"
