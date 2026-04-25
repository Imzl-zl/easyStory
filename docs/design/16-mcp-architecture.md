# MCP 架构预留设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🟡 第一阶段已落地 MCP Client / Hook 插件，MCP Server 仍为第二阶段 |
| 关联文档 | [核心工作流](./01-core-workflow.md)、[跨模块契约](./17-cross-module-contracts.md) |

---

## 1. 概述

MCP (Model Context Protocol) 是 AI 生态基础设施协议。当前已落地 **MCP Client 的最小可用闭环**：`streamable_http` client、`mcp_server` 配置、`mcp` hook provider、assistant/workflow runtime 统一通过 `PluginRegistry` 调用。MCP Server 暴露与通用 agent tool-calling 仍保留为后续阶段。

本文档的定位是：

- 记录 MCP client / plugin / server 三方向的总体预留
- 记录当前已落地的 MCP client 与 PluginRegistry 基线

本文档不再作为 ordinary chat native tool-calling runtime 的未来真值。

ordinary chat 的正式未来口径统一以下列文档为准：

- [20-assistant-runtime-chat-mode](./20-assistant-runtime-chat-mode.md)
- [21-assistant-project-document-tools](./21-assistant-project-document-tools.md)
- [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)

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

### 3.2 当前实现：PluginRegistry + MCP Client

这一节只描述当前已落地基线，不代表 ordinary chat 的长期目标架构。

当前现状是：

- Agent 通过 ToolProvider 抽象层调用 LLM
- Hook / Assistant runtime 通过 PluginRegistry 调用 MCP
- 这条路径当前主要服务 hook/plugin 场景

后续 ordinary chat native tool-calling 的正式目标，不再以“通过 PluginRegistry 旁路执行 MCP”作为主骨架，而以 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md) 为准。

| 实现 | 阶段 | 说明 |
|------|------|------|
| LLMToolProvider | 已实现 | 通过项目内 LLM HTTP 方言适配层直连主流接口 |
| McpPluginProvider | 已实现 | 通过官方 MCP Python SDK 调用外部 `streamable_http` 工具 |
| MCPToolProvider | 后续 | 面向 agent 通用 tool-calling 的统一 ToolProvider |

MCP Client 出站地址执行统一 endpoint 策略：默认只允许公网 `https`，本地 / 私网地址和公网 `http` 必须通过 MCP 专属运行时环境变量显式放开；该策略同时作用于用户 / 项目 MCP 写入入口和运行时调用出口。

ToolProvider 接口提供两个方法：
- `execute(tool_name, params)` — 执行工具调用
- `list_tools()` — 列出可用工具

### 3.3 Agent 配置预留

```yaml
agent:
  id: "agent.fact_checker"
  mcp_servers: []                # 当前可配置，用于 assistant / hook runtime 能力装配
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

Hook 通过 PluginRegistry 执行，不在 Hook 逻辑里硬编码 action type。

当前内置四种 Provider：script、webhook、agent、mcp。

PluginRegistry 接口：
- `register(name, provider)` — 注册插件类型
- `execute(plugin_type, config)` — 执行插件

---

## 6. MVP 必须遵守的架构约束

| 约束 | 说明 | 违反后果 |
|------|------|---------|
| Service 层不依赖 HTTP | 入参/返回用 DTO | MCP Server 无法复用 |
| Agent 通过 ToolProvider | 不直接依赖具体模型 SDK/方言细节 | 无法插入 MCP 工具 |
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
│  Database │ LLM HTTP Dialect Adapter │ FileSystem │ ConfigLoader │
└─────────────────────────────────────────────────────┘
```

---

## 8. 实施路线图

| 阶段 | 内容 | 工作量 |
|------|------|--------|
| 第一阶段 | MCP Client for Hook/Assistant + 配置落地 | 已完成 |
| 第二阶段 A | MCP Client: Agent 通用 tool-calling | 中等 |
| 第二阶段 B | MCP Server: 暴露 Resource/Tool | 中等 |
| 第三阶段 | MCP 插件生态 + 市场 | 较大 |

---

*最后更新: 2026-03-26*
