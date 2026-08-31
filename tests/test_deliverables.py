"""Deliverable extract and branding constants tests for GameChanger."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from app.branding import COMPANY_FULL, PRODUCT_NAME

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_webapp():
    path = ROOT / "app.py"
    spec = importlib.util.spec_from_file_location("gc_webapp_deliverables", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_branding_company():
    assert COMPANY_FULL == "GameChanger Media Inc."
    assert PRODUCT_NAME == "GameChanger Research Agent"


def test_collect_deliverable_snippets(tmp_path, monkeypatch):
    webapp = _load_webapp()
    ws = tmp_path / "workspace"
    ws.mkdir()
    brief = ws / "research_brief_demo.md"
    brief.write_text(
        "# demo\n\n## Key Findings\n- Hudl focuses on sports video and analytics\n- GameChanger leads mobile scoring\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(webapp, "__file__", str(tmp_path / "app.py"))

    text, rels = webapp._collect_deliverable_snippets(
        "saved workspace/research_brief_demo.md"
    )
    assert any("research_brief_demo.md" in r for r in rels)
    assert "Key Findings" in text or "Hudl" in text
