from app.agent.base import BaseAgent
from app.agent.react import ReActAgent
from app.agent.toolcall import ToolCallAgent

try:
    from app.agent.browser import BrowserAgent
except Exception:  # pragma: no cover
    BrowserAgent = None  # type: ignore

try:
    from app.agent.mcp import MCPAgent
except Exception:  # pragma: no cover
    MCPAgent = None  # type: ignore

try:
    from app.agent.swe import SWEAgent
except Exception:  # pragma: no cover
    SWEAgent = None  # type: ignore


__all__ = [
    "BaseAgent",
    "BrowserAgent",
    "ReActAgent",
    "SWEAgent",
    "ToolCallAgent",
    "MCPAgent",
]
