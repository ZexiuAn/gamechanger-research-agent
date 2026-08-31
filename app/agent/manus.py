from typing import Dict, List, Optional

from pydantic import Field, model_validator

from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.fetch_url import FetchUrl
from app.tool.python_execute import PythonExecute
from app.tool.research_kb import ResearchKB
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.web_search import WebSearch

# 浏览器为可选能力。默认关闭（ENABLE_BROWSER=1 才启用），避免演示被浏览器栈拖垮。
import os

try:
    from app.agent.browser import BrowserContextHelper
    from app.tool.browser_use_tool import BrowserUseTool

    _BROWSER_IMPORT_OK = True
except Exception as exc:  # pragma: no cover
    BrowserContextHelper = None  # type: ignore
    BrowserUseTool = None  # type: ignore
    _BROWSER_IMPORT_OK = False
    logger.warning(f"Browser tool unavailable, running without it: {exc}")

_BROWSER_AVAILABLE = _BROWSER_IMPORT_OK and os.getenv("ENABLE_BROWSER", "0") == "1"


def _default_tools() -> ToolCollection:
    # Web/演示路径不挂 ask_human：其 input() 会阻塞整个事件循环，表现为「思考卡住」
    tools = [
        PythonExecute(),
        WebSearch(),
        FetchUrl(),
        ResearchKB(),
        StrReplaceEditor(),
        Terminate(),
    ]
    if _BROWSER_AVAILABLE and BrowserUseTool is not None:
        tools.insert(1, BrowserUseTool())
    return ToolCollection(*tools)


class Manus(ToolCallAgent):
    """R&D 调研 / 效能任务 Agent：规划 → 工具执行 → 落盘交付。"""

    name: str = "YidongAgent"
    description: str = (
        "易动纷享 R&D 调研效能 Agent 原型：支持联网检索、文件整理与多步工具编排"
    )

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # MCP 客户端延迟导入，避免无 MCP 配置时拖垮启动
    mcp_clients: Optional[object] = Field(default=None)

    available_tools: ToolCollection = Field(default_factory=_default_tools)

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])
    browser_context_helper: Optional[object] = None

    connected_servers: Dict[str, str] = Field(default_factory=dict)
    _initialized: bool = False

    @model_validator(mode="after")
    def initialize_helper(self) -> "Manus":
        if _BROWSER_AVAILABLE and BrowserContextHelper is not None:
            self.browser_context_helper = BrowserContextHelper(self)
        return self

    @classmethod
    async def create(cls, **kwargs) -> "Manus":
        instance = cls(**kwargs)
        await instance.initialize_mcp_servers()
        instance._initialized = True
        return instance

    async def initialize_mcp_servers(self) -> None:
        """初始化 MCP（若配置存在）；失败不影响主路径。"""
        try:
            from app.tool.mcp import MCPClients, MCPClientTool

            if self.mcp_clients is None:
                self.mcp_clients = MCPClients()
        except Exception as e:
            logger.debug(f"MCP not available: {e}")
            return

        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse":
                    if server_config.url:
                        await self.connect_mcp_server(server_config.url, server_id)
                        logger.info(
                            f"Connected to MCP server {server_id} at {server_config.url}"
                        )
                elif server_config.type == "stdio":
                    if server_config.command:
                        await self.connect_mcp_server(
                            server_config.command,
                            server_id,
                            use_stdio=True,
                            stdio_args=server_config.args,
                        )
                        logger.info(
                            f"Connected to MCP server {server_id} using command {server_config.command}"
                        )
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_id}: {e}")

    async def connect_mcp_server(
        self,
        server_url: str,
        server_id: str = "",
        use_stdio: bool = False,
        stdio_args: List[str] = None,
    ) -> None:
        from app.tool.mcp import MCPClientTool

        if self.mcp_clients is None:
            return
        if use_stdio:
            await self.mcp_clients.connect_stdio(
                server_url, stdio_args or [], server_id
            )
            self.connected_servers[server_id or server_url] = server_url
        else:
            await self.mcp_clients.connect_sse(server_url, server_id)
            self.connected_servers[server_id or server_url] = server_url

        new_tools = [
            tool for tool in self.mcp_clients.tools if tool.server_id == server_id
        ]
        self.available_tools.add_tools(*new_tools)

    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        from app.tool.mcp import MCPClientTool

        if self.mcp_clients is None:
            return
        await self.mcp_clients.disconnect(server_id)
        if server_id:
            self.connected_servers.pop(server_id, None)
        else:
            self.connected_servers.clear()

        base_tools = [
            tool
            for tool in self.available_tools.tools
            if not isinstance(tool, MCPClientTool)
        ]
        self.available_tools = ToolCollection(*base_tools)
        self.available_tools.add_tools(*self.mcp_clients.tools)

    async def cleanup(self):
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        if self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False

    async def think(self) -> bool:
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        original_prompt = self.next_step_prompt

        browser_tool_available = False
        if _BROWSER_AVAILABLE and BrowserUseTool is not None:
            browser_tool_available = BrowserUseTool().name in [
                tool.name for tool in self.available_tools.tools
            ]

        if browser_tool_available and self.browser_context_helper is not None:
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        result = await super().think()
        self.next_step_prompt = original_prompt
        return result
