# 简历要点（GameChanger 调研助手）

**AI软件产品开发实习生｜GameChanger Media Inc.｜2026.05 – 2026.09**

参与公司研发中心面向研发效能场景的大模型应用产品开发，方向覆盖 Agent、Tool Calling、MCP 等能力，服务内部研发同学日常竞品/技术调研与文档整理，并探索对外可演示的产品形态。

独立负责并落地「GameChanger调研助手」：基于 OpenManus 构建多步 Tool Calling Agent，完成任务规划、联网检索、网页精读、本地知识库/MCP 工具调用、Markdown 简报落盘与任务终止全链路；Web 端以 SSE 流式推送 Thought/Action 轨迹实现过程可观测，任务结束后通过轻量模型二次调用生成面向用户的结论摘要；自研 MCP Server（竞品清单 / 术语库 / 任务模板）支持标准热插拔，并验证同一编排可泛化到内部文档整理。公开网页结论需人工复核，演示知识库为 mock 数据。

**技术栈：** Python、OpenManus（ToolCallAgent / ReAct）、Anthropic Claude 3.5 Sonnet / Haiku、Function Calling / Tool Use、MCP（Model Context Protocol）、FastAPI、SSE、pytest。
**项目地址：** https://github.com/ZexiuAn/gamechanger-research-agent
