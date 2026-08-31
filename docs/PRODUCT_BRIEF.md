# Product Brief · GameChanger Research Agent

## 业务背景（GameChanger 包装口径）

| 项 | 内容 |
|:---|:---|
| 场景 / 部门 | **GameChanger Media Inc. · R&D AI Lab** |
| 产品定位 | **GameChanger Research Agent**：竞品 / 技术调研效能 Agent 原型 |
| 核心目标 | 自动化多步调研链路（检索→精读→MCP知识库对齐→结构化简报落盘），降低研发与产品团队调研耗时 |
| 泛化验证 | 同套编排泛化至内部备忘录待办提炼（Task Digest） |
| 项目性质 | 个人作品集 / 研发原型（脱敏与合成基准数据） |

## 亮点设计

1. **ReAct 多步工具编排**：动态调用 web_search、fetch_url 网页精读、str_replace_editor 文件落盘；
2. **标准 MCP 工具服务**：基于 FastMCP 实现 `gamechanger_research`，解耦业务知识与 Agent 核心逻辑；
3. **两阶段执行与蒸馏**：第一阶段 Agent 专注搜集与落盘，第二阶段轻量 LLM 专注提炼面向用户的决策要点；
4. **SSE 全过程可观测**：流式展示思考过程、工具调用参数与输出，解决黑盒等待痛点。
