# GameChanger Research Agent · Market & Tech Research Autonomous Agent

> Autonomous market & technical research Agent prototype developed for GameChanger R&D AI Lab.  
> Powered by [OpenManus](https://github.com/FoundationAgents/OpenManus) architecture, Anthropic Claude 3.5 Sonnet / OpenAI GPT-4o, Model Context Protocol (MCP), and FastAPI SSE stream observability.

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Anthropic](https://img.shields.io/badge/LLM-Claude%203.5%20Sonnet-purple.svg)](https://www.anthropic.com/)
[![MCP](https://img.shields.io/badge/Protocol-MCP%20(FastMCP)-orange.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI%20%2B%20SSE-009688.svg)](https://fastapi.tiangolo.com/)

---

## 🌟 Key Features

* **Multi-step ReAct & Tool Calling**: Autonomous orchestration of task planning, web search, deep page reading (`fetch_url`), and structured Markdown persistence.
* **Model Context Protocol (MCP)**: Native stdio-based `gamechanger_research` MCP server exposing domain competitor benchmarks, technical glossary, and briefing templates.
* **Observable Thought Traces**: Real-time streaming of Agent planning steps, tool execution arguments, and results via Server-Sent Events (SSE).
* **Two-Phase Executive Summarization**: Post-hoc LLM distillation pass synthesizes concise, user-facing executive takeaways directly from workspace deliverables.
* **Dual Task Presets**: Out-of-the-box support for both market competitor briefings and internal memo action item digestion.

---

## 🏗️ Architecture

```
User Query ──► FastAPI SSE Stream ──► OpenManus Agent Runtime
                                           │
         ┌─────────────────── ReAct Tool Calling Loop ───────────────────┐
         ▼                                  ▼                            ▼
  Web Search & Deep Read           MCP Knowledge Service         StrReplace Editor
 (web_search / fetch_url)   (list_competitors / glossary)    (workspace/*.md Artifact)
         │                                  │                            │
         └──────────────────────────────────┴────────────────────────────┘
                                           │
                                     terminate
                                           │
                                           ▼
                      Post-hoc Executive Summary Pass (Claude/GPT)
                                           │
                                           ▼
                       Rendered Deliverable & Citations
```

---

## 🚀 Quick Start

### 1. Setup Virtual Environment

```bash
git clone https://github.com/ZexiuAn/gamechanger-research-agent.git
cd gamechanger-research-agent

python3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-demo.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env to set your LLM API Key:
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# or OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Launch Web Workbench

```bash
python app.py
```

Visit `http://127.0.0.1:5172` in your browser.

---

## 📁 Repository Layout

```
.
├── app.py                     # FastAPI backend & SSE event dispatcher
├── app/
│   ├── agent/manus.py         # Main Agent class & tool collection
│   ├── branding.py            # Unified branding definitions
│   ├── config.py              # LLM & MCP configuration loader
│   ├── tool/                  # Custom tools (fetch_url, research_kb, etc.)
│   └── prompt/manus.py        # System prompt & step reasoning prompts
├── mcp_servers/
│   └── gamechanger_research_mcp.py # FastMCP stdio tool server
├── config/
│   ├── config.toml            # Runtime model settings
│   └── mcp.json               # MCP server registration manifest
├── data/research_assets.json  # Benchmark seed knowledge
├── templates/index.html       # Web workspace interface
├── static/                    # Frontend styling, trace formatting & SSE client
├── tests/                     # Unit & integration pytest suite
└── workspace/                 # Persisted Markdown deliverables & task digests
```

---

## 📜 Compliance & Data Policy

* This repository is an **engineering prototype** built for evaluation and demonstration.
* Seed assets in `data/research_assets.json` and `workspace/` are synthetic and de-identified in full compliance with corporate confidentiality (NDA) guidelines.
