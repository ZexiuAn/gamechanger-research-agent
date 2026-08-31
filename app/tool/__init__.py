from app.tool.base import BaseTool
from app.tool.bash import Bash
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.planning import PlanningTool
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate
from app.tool.tool_collection import ToolCollection
from app.tool.web_search import WebSearch

# 浏览器 / Crawl4AI 为可选依赖，缺包时不影响「调研简报」主路径
try:
    from app.tool.browser_use_tool import BrowserUseTool
except Exception:  # pragma: no cover
    BrowserUseTool = None  # type: ignore

try:
    from app.tool.crawl4ai import Crawl4aiTool
except Exception:  # pragma: no cover
    Crawl4aiTool = None  # type: ignore


__all__ = [
    "BaseTool",
    "Bash",
    "BrowserUseTool",
    "Terminate",
    "StrReplaceEditor",
    "WebSearch",
    "ToolCollection",
    "CreateChatCompletion",
    "PlanningTool",
    "Crawl4aiTool",
]
