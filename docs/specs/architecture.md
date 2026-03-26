# easyStory 系统架构设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 架构设计 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-13 |
| 更新时间 | 2026-03-26 |
| 关联文档 | [技术栈确定](./tech-stack.md)、[数据库设计](./database-design.md)、[配置格式规范](./config-format.md) |

---

## 1. 产品定位

easyStory 是一个 **AI 小说创作平台**，核心特点：

1. 有核心的 AI 能力
2. 可以通过配置文件自定义行为
3. 可以集成外部工具
4. 可以定义 Hooks（在特定时机执行操作）

类比参考：
- **Cursor**（AI 代码编辑器）→ 可以自定义 rules、MCP 工具
- **Claude Code**（AI CLI 工具）→ 可以自定义 commands、hooks

---

## 2. 核心概念

### 工作流（Workflow）

工作流是"做事的步骤"，把完整写作过程拆成多个可生成、审核、精修和回退的节点。每个步骤就是一个**节点**。

```
输入题材和设定 → 生成大纲 → 生成开篇设计 → 确认前置资产 → 拆分章节任务 → 生成章节 → 审核章节 → 导出成稿
```

v0.1 只支持线性流程（节点顺序执行），并行节点为后续版本能力。

### Skill（技能包）

Skill 是"AI 的技能包"，包含提示词模板和模型参数，告诉 AI "怎么写"某类内容。

示例：`skill.chapter.xuanhuan`、`skill.outline.suspense`、`skill.character.design`

### Agent（智能体）

Agent 是"有特定角色的 AI 助手"，每个 Agent 专注于特定任务，可以关联多个 Skills。

示例：`agent.outline_writer`（写大纲）、`agent.style_checker`（文风审核）

### Hook（钩子）

Hook 是"在某个时机自动执行的操作"，用于自动化流程中的重复性动作。

示例：`before_generate`（生成前检查输入）、`after_generate`（生成后自动保存）

### 插件（Plugin）

插件是"按需扩展功能的模块"，不用的不加载。

示例：`plugin.export.docx`（导出 Word）、`plugin.check.grammar`（语法检查）

### MCP（Model Context Protocol）

让 AI 能够调用外部工具的协议，使 AI 不只是"聊天"，还能"做事"（调用搜索、数据库、文件工具等）。

---

## 3. 分层架构

> **概念视图**：以下 5 层架构展示系统的概念分层，便于理解各层职责。实际后端实现以 4 层架构为准（Entry → Service → Engine → Infrastructure），详见 [§7 MCP 预留架构分层](#7-mcp-预留架构分层)。

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户界面层 (UI Layer)                     │
│  项目管理 | 创作工作台 | Assistant 对话 | 配置中心 | 插件市场     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        平台核心层 (Platform Core)                │
│  项目管理 | 内容管理 | 版本管理 | 导出管理                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        创作引擎层 (Engine Layer)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 流程编排器   │  │ 提示词引擎   │  │ 模型路由器   │          │
│  │ (工作流)     │  │ (Skills)     │  │ (LLM Dialect)│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Agent 管理   │  │ Hook 系统    │  │ MCP 集成     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        配置系统层 (Config Layer)                 │
│  Skills 配置 | Hooks 配置 | Agents 配置 | Workflow 配置          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        插件系统层 (Plugin Layer)                 │
│  内置插件 | 用户插件 | 第三方插件                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 4. 各层职责

| 层级 | 职责 | 关键技术 |
|-----|------|---------|
| 用户界面层 | 用户交互、状态展示 | Next.js、React、Zustand |
| 平台核心层 | 项目管理、内容管理 | Python、FastAPI |
| 创作引擎层 | 工作流执行、模型调用 | LangGraph、ToolProvider、LLM 方言适配层 |
| 配置系统层 | 配置加载、热更新、校验 | YAML、文件监听 |
| 插件系统层 | 功能扩展 | 受控配置扩展（MVP）；pluggy（v0.2+） |

---

## 5. 核心功能

### 5.1 自动化工作流

支持完全自动化的创作流水线，用户通过配置决定自动化程度：

```
生成大纲 → 自动审核（并行）→ 不通过则自动精修 → 精修失败则暂停等待用户
    ↓
生成开篇设计 → 自动审核 → 不通过则自动精修 → 精修失败则暂停等待用户
    ↓
拆分章节任务（chapter_split）→ 生成章节（循环）→ 自动审核 → 自动精修 → 导出
```

关键配置项：`auto_review`、`auto_fix`、`max_fix_attempts`、`on_fix_fail`

标准创作链路统一为 `ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter`，其中 `chapter_split` 是 `ChapterTask` 生成的硬前置步骤。

### 5.2 上下文注入

生成每章时，自动注入相关上下文，避免剧情漂移：

| 当前已实现注入类型 | 说明 |
|---------|------|
| `project_setting` | 项目设定（结构化设定文档） |
| `outline` | 大纲 |
| `opening_plan` | 开篇设计（前 1-3 章的阶段约束） |
| `world_setting` | 从 `ProjectSetting.world_setting` 投影出的世界观视图 |
| `character_profile` | 从 `ProjectSetting.protagonist/key_supporting_roles` 投影出的人物设定视图 |
| `chapter_task` | 当前章节任务（来自 ChapterTask） |
| `previous_chapters` | 前 N 章内容 |
| `chapter_summary` | 基于既有章节 current version 派生的轻量摘要视图 |
| `story_bible` | Story Bible 事实库（人物状态/时间线/伏笔） |
| `style_reference` | 文风参考样本，运行时按 section 独立限额注入 |

`chapter_list` 等仍是后续规划项，当前运行时未开放配置。

### 5.3 多 Agent 审核

支持多个 Agent 并行审核，每个 Agent 专注不同维度：

| Agent | 职责 |
|-------|------|
| `agent.style_checker` | 文风一致性检查 |

其余 reviewer（如违禁词、AI 味、剧情一致性）仍属于后续扩展项，当前默认配置未内置。

### 5.4 版本管理

每次内容变更保存全量快照（v0.1），支持查看历史版本和回退。

---

## 6. 关键决策汇总

| 决策 | 结论 | 说明 |
|------|------|------|
| 工作流形态 | v0.1 线性流程，后续支持 DAG | - |
| 节点状态持久化 | 实时持久化（每次变更写库） | - |
| 前后端通信 | REST API + SSE | API 文档由 FastAPI 自动生成 |
| 配置存储 | 文件系统（YAML），数据库做缓存索引 | 详见 [配置格式规范](./config-format.md) |
| 导出文件存储 | 文件系统存储，数据库只存路径和元数据 | 详见 [数据库设计](./database-design.md) |
| 向量数据库/知识库 | v0.1 不需要，直接注入上下文即可 | - |

---

## 7. MCP 预留架构分层

为确保第二阶段能平滑接入 MCP，MVP 开发必须遵守以下约束：

| 约束 | 说明 | 违反后果 |
|------|------|---------|
| Service 层不依赖 HTTP | 入参/返回用 DTO，不用 Request/Response | MCP Server 无法复用 Service |
| Agent 通过 ToolProvider 调用 LLM | 不直接依赖具体模型 SDK / HTTP 方言 | 无法插入 MCP 工具 |
| Hook 通过 PluginRegistry 执行 | 不在 Hook 逻辑里硬编码 action type | 无法增加新 action type |
| 内容操作通过 Service 层 | API Router 不直接操作数据库 | MCP Server 无法复用逻辑 |
| 认证在入口层处理 | Service 层不检查 HTTP header | MCP 和 REST 用不同认证方式 |

### 架构分层图（带 MCP 预留）

```
┌─────────────────────────────────────────────────────────────────┐
│                        入口层 (Entry Layer)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ FastAPI      │  │ MCP Server   │  │ CLI (可选)   │          │
│  │ (REST + SSE) │  │ (第二阶段)    │  │ (第三阶段)   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼──────────────────┼─────────────────┘
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Service Layer (业务逻辑)                     │
│  ProjectService | WorkflowService | AssistantService | ContentService | ... │
│  入参: DTO/基础类型   返回: DTO   异常: BusinessException        │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Engine Layer (创作引擎)                       │
│  WorkflowEngine | ContextBuilder | ReviewExecutor               │
│  ToolProvider (LLM→MCP) | PluginRegistry                       │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer (基础设施)                 │
│  Database | LLM HTTP Dialect Adapter | FileSystem | ConfigLoader │
└─────────────────────────────────────────────────────────────────┘
```

详见 [MCP 架构预留设计](../design/16-mcp-architecture.md)。

### 当前后端目录约束

为避免业务继续堆回根级扁平目录，后端代码组织以以下结构为准：

```text
apps/api/
  alembic/
    versions/
apps/api/app/
  main.py
  entry/
    http/
      router.py                 # 根路由装配，只负责聚合模块路由
  shared/
    db/
      base.py                  # Declarative Base / 通用 mixin
    runtime/
      plugin_registry.py        # 跨模块运行时抽象
      tool_provider.py
  modules/
    model_registry.py           # ORM 模型集中注册，仅用于 metadata 装配
    system/
      entry/http/router.py
    user/
      models/
    project/
      models/
    content/
      models/
    workflow/
      models/
      service/
      engine/
    assistant/
      entry/http/
      service/
    context/
      models/
      engine/
    review/
      models/
      engine/
    config_registry/
      entry/http/
      service/
      infrastructure/
      schemas/
```

约束：

- 数据库迁移资产统一放在 `apps/api/alembic/`
- 根级 `entry` 只做装配，不承载具体业务规则
- 跨模块基础抽象进入 `shared`
- 业务实现优先进入 `modules/<domain>/...`
- ORM 基类统一位于 `shared/db/base.py`
- ORM 模型只允许位于 `modules/<domain>/models/`
- `modules/model_registry.py` 作为 `Base.metadata` 的集中注册入口
- `shared/db/bootstrap.py` 只负责开发期初始化与遗留 schema reconcile；正式 schema 演进通过 Alembic revision 管理
- 根级 `service / engine / infrastructure / schemas / models` 不再继续承载业务代码
