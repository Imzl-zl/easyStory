# MCP 架构预留设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🔴 MVP 预留扩展点，第二阶段实现 |
| 关联文档 | [核心工作流](./01-core-workflow.md)、[跨模块契约](./17-cross-module-contracts.md) |

---

## 1. 概述

MCP (Model Context Protocol) 是 AI 生态基础设施协议。MVP 不实现完整 MCP，但**必须在架构中预留三个方向的扩展点**。

---

## 2. 三方向总览

```
┌─────────────────────────────────────────────────────┐
│                     easyStory                        │
│                                                      │
│  方向1: Client  — Agent/Hook 调用外部 MCP Server    │
│  方向2: Server  — 暴露自身能力给外部 AI 客户端       │
│  方向3: 插件    — MCP 作为统一插件协议               │
└─────────────────────────────────────────────────────┘
```

---

## 3. 方向 1: MCP Client

### 3.1 场景

| 场景 | 外部 MCP Server | 用途 |
|------|----------------|------|
| 查史实 | 网络搜索 MCP | Agent 验证历史细节 |
| 一致性检查 | 知识库 MCP | 审核 Agent 查设定库 |
| 自动发布 | 起点/晋江 API MCP | Hook 上传稿件 |
| 实时通知 | Slack/飞书 MCP | 完成/失败通知 |

### 3.2 MVP 预留：ToolProvider 抽象层

```python
class ToolProvider(ABC):
    @abstractmethod
    async def execute(self, tool_name: str, params: dict) -> ToolResult: ...
    @abstractmethod
    async def list_tools(self) -> list[ToolDefinition]: ...

class LLMToolProvider(ToolProvider):       # MVP 实现
    async def execute(self, tool_name, params): return await self.llm_client.generate(params["prompt"])

class MCPToolProvider(ToolProvider):        # 第二阶段
    async def execute(self, tool_name, params): return await self.client.call_tool(tool_name, params)
```

### 3.3 Agent 配置预留

```yaml
agent:
  id: "agent.fact_checker"
  mcp_servers: []                # MVP: 空; 第二阶段: 配置 MCP Server
```

---

## 4. 方向 2: MCP Server

### 4.1 MVP 预留：Service 层规范化

**关键：所有业务逻辑封装在 Service 层，API 和 MCP Server 都调用同一 Service。**

```
MVP:      FastAPI Router → Service Layer → Database/Engine
第二阶段:  FastAPI Router ──┐
                            ├──→ Service Layer → Database/Engine
           MCP Server 层  ──┘
```

Service 层约束：不依赖 HTTP Request/Response，入参/返回用 DTO，异常用业务异常类。

### 4.2 未来暴露的能力

- Resources: 项目列表、内容、章节、大纲、事实库
- Tools: 生成章节、触发审核、启动工作流、修改设定、导出

---

## 5. 方向 3: 统一插件协议

### 5.1 MVP 预留：PluginRegistry

```python
class PluginRegistry:
    def register(self, name: str, provider: PluginProvider): ...
    async def execute(self, plugin_type: str, config: dict) -> PluginResult: ...

# MVP 注册
registry.register("script", ScriptPluginProvider())
registry.register("webhook", WebhookPluginProvider())
registry.register("agent", AgentPluginProvider())
# 第二阶段: registry.register("mcp", MCPPluginProvider())
```

---

## 6. MVP 必须遵守的架构约束

| 约束 | 说明 | 违反后果 |
|------|------|---------|
| Service 层不依赖 HTTP | 入参/返回用 DTO | MCP Server 无法复用 |
| Agent 通过 ToolProvider | 不直接 import litellm | 无法插入 MCP 工具 |
| Hook 通过 PluginRegistry | 不硬编码 action type | 无法增加新类型 |
| 内容操作通过 Service 层 | Router 不直接操作 DB | MCP 无法复用逻辑 |
| 认证在入口层处理 | Service 不检查 HTTP header | MCP 用不同认证 |

---

## 7. 架构分层图（带 MCP 预留）

```
┌─────────────────────────────────────────────────────┐
│                    入口层 (Entry Layer)               │
│  FastAPI (REST+SSE) │ MCP Server (二期) │ CLI (三期) │
└─────────────────────┼────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│              Service Layer (业务逻辑)                 │
│  ProjectService │ WorkflowService │ ContentService   │
└─────────────────────┼────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│              Engine Layer (创作引擎)                   │
│  WorkflowEngine │ ContextBuilder │ ReviewExecutor    │
│  ToolProvider (LLM → MCP)  │  PluginRegistry        │
└─────────────────────┼────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│           Infrastructure Layer (基础设施)              │
│  Database │ LiteLLM │ FileSystem │ ConfigLoader      │
└─────────────────────────────────────────────────────┘
```

---

## 8. 实施路线图

| 阶段 | 内容 | 工作量 |
|------|------|--------|
| MVP | 抽象层 + Service 规范化 | 架构约束，无额外工作量 |
| 二期 A | MCP Client: Agent 调外部工具 | 中等 |
| 二期 B | MCP Server: 暴露 Resource/Tool | 中等 |
| 三期 | MCP 插件生态 + 市场 | 较大 |

---

*最后更新: 2026-03-16*
