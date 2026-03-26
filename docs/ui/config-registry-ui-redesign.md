# 配置中心 UI 重设计

## 审核状态：待审核

---

## 1. 问题诊断

### 1.1 当前状态

| 方面 | 现状 | 问题 |
|------|------|------|
| 编辑方式 | 纯 JSON textarea | 用户必须理解完整 DTO |
| 详情展示 | 摘要化（变量数量、技能数量） | 看不到 prompt、schema、绑定关系 |
| 侧边栏 | 无搜索/过滤/分组 | 配置多时难以定位 |
| 校验 | 仅 JSON 解析 + 后端 422 | 无字段级提示、无 diff 预览 |
| 脏状态 | 有 `isDirty` | 无离页提醒、无切换确认 |

### 1.2 后端能力边界

| 能力 | 状态 | 设计约束 |
|------|------|----------|
| CRUD | 仅 list / detail / update | 不设计新建/删除/复制 |
| MCP 传输 | 仅 `streamable_http` | 不设计 stdio/sse/websocket 选择 |
| Agent 类型 | 仅 `writer` / `reviewer` / `checker` | 不设计 assistant/custom |
| 模型发现 | 无后端接口 | 不设计自动发现/测试 |
| MCP 工具发现 | 无后端接口 | 不设计工具发现 UI |

---

## 2. 设计方案

### 2.1 整体布局

保留三栏布局，调整职责：

```
┌─────────────────────────────────────────────────────────────────────────┐
│  配置中心                                                                 │
├──────────────┬────────────────────────┬────────────────────────────────┤
│  左栏        │  中栏：可读详情         │  右栏：编辑区                   │
│  ────        │  ─────────────         │  ──────────                     │
│  [搜索框]    │  配置名称               │  [表单视图] [JSON 高级模式]     │
│  [过滤标签]  │  描述                   │                                 │
│  [类型切换]  │  核心字段（只读展示）    │  结构化表单 / JSON 编辑器       │
│              │  标签                   │                                 │
│  Skills (12) │  原始 JSON（折叠）       │  [保存] [还原]                  │
│  Agents (5)  │                         │                                 │
│  Hooks (8)   │                         │                                 │
│  MCP (3)     │                         │                                 │
│  Workflows(2)│                         │                                 │
│              │                         │                                 │
│  配置列表    │                         │                                 │
│  ────────    │                         │                                 │
│  □ skill-1   │                         │                                 │
│  ■ skill-2   │                         │                                 │
│  □ skill-3   │                         │                                 │
└──────────────┴────────────────────────┴────────────────────────────────┘
```

### 2.2 核心改动

#### 2.2.1 双模式编辑器

| 模式 | 说明 |
|------|------|
| 表单视图 | 默认模式，结构化表单，类型感知，实时校验 |
| JSON 高级模式 | 保留现有 textarea，高级用户使用 |

切换逻辑：
- `表单 → JSON`：格式化输出
- `JSON → 表单`：解析 + 校验，解析失败则提示但允许切换

#### 2.2.2 侧边栏增强

**注意**：过滤选项按类型区分，因为字段并不通用：
- `enabled` 字段仅存在于 Hook 和 MCP
- `tags` 字段仅存在于 Skill、Agent、Workflow
- Summary/Detail DTO 无 `updated_at` 字段，不支持按更新时间排序

```
┌─────────────────────────────┐
│  [🔍 搜索配置名称、ID...]    │
├─────────────────────────────┤
│  排序：[名称 A-Z ▼]         │
│  ○ 名称 A-Z                 │
│  ○ 名称 Z-A                 │
├─────────────────────────────┤
│  [Skills] [Agents] [Hooks]  │
│  [MCP] [Workflows]          │
├─────────────────────────────┤
│  当前类型：Skills            │
│  描述：Prompt 模板、输入输出 │
│        契约与模型设置        │
├─────────────────────────────┤
│  类型过滤（按当前类型显示）  │
│  ────────────────────────   │
│  Skills/Agents/Workflows:   │
│    标签：[generation][polish]│
│  Hooks/MCP:                 │
│    状态：[全部][已启用][停用]│
├─────────────────────────────┤
│  配置列表                    │
│  ────────                    │
│  ■ draft-generation          │
│    分类：generation          │
│    模型：claude-sonnet       │
│                              │
│  □ content-polish            │
│    分类：polish              │
│    模型：gpt-4o              │
└─────────────────────────────┘
```

#### 2.2.3 URL 状态同步

**要求**：所有 UI 状态必须同步到 URL query params，确保：
- 刷新页面后状态保持
- 分享链接可直接定位到特定配置
- 浏览器前进/后退正常工作

**同步字段**：
| 状态 | Query Param | 示例 |
|------|-------------|------|
| 当前类型 | `type` | `?type=skills` |
| 当前配置项 | `item` | `?type=skills&item=draft-generation` |
| 搜索关键词 | `q` | `?type=skills&q=draft` |
| 排序方式 | `sort` | `?type=skills&sort=name_desc` |
| 标签过滤 | `tags` | `?type=skills&tags=generation,polish` |
| 状态过滤 | `status` | `?type=hooks&status=enabled` |

**实现方式**：
```typescript
// 使用 router.replace 同步状态到 URL
const updateQuery = useCallback((updates: Record<string, string | null>) => {
  const params = new URLSearchParams(searchParams);
  Object.entries(updates).forEach(([key, value]) => {
    if (value) params.set(key, value);
    else params.delete(key);
  });
  router.replace(`?${params.toString()}`);
}, [router, searchParams]);
```

#### 2.2.4 离页保护

- 切换配置项时：拦截 `onSelectItem`，未保存则弹窗确认
- 切换类型时：拦截 `onSelectType`，未保存则弹窗确认
- 关闭页面/刷新时：`beforeunload` 提醒

**注意**：当前页面是 Next App Router 客户端页面，导航通过 `router.replace(...)` 改变 query 参数实现，不依赖 middleware。实现时应拦截本地导航动作而非寄托给 middleware。

---

## 3. 各类型配置面设计

### 3.1 Skill 配置面

**后端 Schema 对齐**：
```python
class SkillConfig:
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    category: str
    author: str | None = None
    tags: list[str]
    prompt: str
    variables: dict[str, SchemaField]  # 与 inputs/outputs 互斥
    inputs: dict[str, SchemaField]     # 与 variables 互斥
    outputs: dict[str, SchemaField]    # 与 variables 互斥
    model: ModelConfig | None
```

**表单设计**：

```
┌─────────────────────────────────────────────────────────────┐
│  Skill 配置编辑                                              │
├─────────────────────────────────────────────────────────────┤
│  基本信息                                                    │
│  ────────                                                    │
│  名称 *        [draft-generation          ]                 │
│  版本          [1.0.0                     ]                 │
│  描述          [生成章节草稿的技能模板      ]                 │
│  分类 *        [generation             ▼]                   │
│  作者          [easyStory Team             ]                 │
│  标签          [generation, draft          ]                 │
│                                                             │
│  Prompt 模板 *                                               │
│  ────────────                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  你是一个专业的小说创作助手。                         │   │
│  │  请根据以下上下文生成章节内容：                       │   │
│  │                                                      │   │
│  │  大纲: {{outline}}                                   │   │
│  │  角色: {{characters}}                                │   │
│  │  前情: {{previous_content}}                          │   │
│  │                                                      │   │
│  │  [变量高亮] [插入变量]                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  变量定义                                                    │
│  ────────                                                    │
│  模式：○ 简单模式 (variables)  ● 增强模式 (inputs/outputs)   │
│                                                             │
│  输入定义 (inputs)                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  变量名      类型        必填    描述        默认值   │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  outline     string      ☑      大纲内容    -        │   │
│  │  characters  array       ☐      角色列表    []       │   │
│  │  chapter_id  integer     ☐      章节ID      1        │   │
│  │                                                      │   │
│  │  [+ 添加输入]                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  输出定义 (outputs)                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  变量名      类型        必填    描述                  │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  content     string      ☑      生成的章节内容        │   │
│  │                                                      │   │
│  │  [+ 添加输出]                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  模型配置                                                    │
│  ────────                                                    │
│  [展开/折叠]  ▶ 使用自定义模型配置                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Provider        [openrouter           ▼]            │   │
│  │  Model Name      [claude-sonnet-4         ]          │   │
│  │  Temperature     [0.7                    ]           │   │
│  │  Max Tokens      [4000                   ]           │   │
│  │  Top P           [1.0                    ]           │   │
│  │                                                      │   │
│  │  高级参数 [展开]                                      │   │
│  │  ─────────────────────────────────────               │   │
│  │  Frequency Penalty  [                              ] │   │
│  │  Presence Penalty   [                              ] │   │
│  │  Stop Sequences     [                              ] │   │
│  │  Required Capabilities [                          ] │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**字段说明**：
- `variables` 与 `inputs/outputs` 互斥，表单需做模式切换
- `SchemaField` 支持类型：`string` / `integer` / `boolean` / `array` / `object`
- Prompt 编辑器：纯文本 + 变量高亮 + 变量插入辅助

---

### 3.2 Agent 配置面

**后端 Schema 对齐**：
```python
class AgentConfig:
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    agent_type: Literal["writer", "reviewer", "checker"]  # alias: "type"
    author: str | None = None
    tags: list[str]
    system_prompt: str
    skills: list[str]
    model: ModelConfig | None
    output_schema: dict[str, Any] | None  # reviewer 不能定义
    mcp_servers: list[str]
```

**表单设计**：

```
┌─────────────────────────────────────────────────────────────┐
│  Agent 配置编辑                                              │
├─────────────────────────────────────────────────────────────┤
│  基本信息                                                    │
│  ────────                                                    │
│  名称 *        [story-writer              ]                 │
│  版本          [1.0.0                     ]                 │
│  描述          [负责章节内容创作的 Agent    ]                 │
│  类型 *        ● writer  ○ reviewer  ○ checker              │
│  作者          [easyStory Team             ]                 │
│  标签          [writer, content            ]                 │
│                                                             │
│  系统提示词 *                                                │
│  ────────────                                                │
│  ⚠ 注意：系统提示词为纯文本，不支持模板变量渲染              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  你是本项目的专职作家。                               │   │
│  │  你的职责是根据大纲和角色设定创作章节内容。            │   │
│  │                                                      │   │
│  │  提示：模板变量（如 {{variable}}）仅 Skill prompt     │   │
│  │  支持渲染，此处不会被替换。                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  技能绑定                                                    │
│  ────────                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  已绑定技能 (2)                                       │   │
│  │  ─────────────                                        │   │
│  │  ☑ draft-generation    生成草稿                      │   │
│  │  ☑ content-polish      内容润色                      │   │
│  │  ☐ style-transfer      风格迁移                      │   │
│  │                                                      │   │
│  │  从可用技能中选择...                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  MCP Server 绑定                                             │
│  ────────────────                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  已绑定 MCP Server (1)                                │   │
│  │  ─────────────────                                    │   │
│  │  ☑ filesystem          文件系统操作                   │   │
│  │  ☐ web-search          网络搜索                       │   │
│  │                                                      │   │
│  │  从可用 MCP Server 中选择...                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  输出 Schema                                                 │
│  ────────────                                                │
│  ⚠ reviewer 类型不能定义 output_schema                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  {                                                   │   │
│  │    "content": "string",                              │   │
│  │    "word_count": "integer",                          │   │
│  │    "metadata": {                                     │   │
│  │      "style": "string"                               │   │
│  │    }                                                 │   │
│  │  }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  模型配置                                                    │
│  ────────                                                    │
│  [同 Skill 模型配置组件]                                     │
└─────────────────────────────────────────────────────────────┘
```

**字段说明**：
- `agent_type` 使用 `type` 作为 JSON 字段名，表单显示为"类型"
- `output_schema` 仅在 `writer` / `checker` 类型时可编辑
- `skills` 和 `mcp_servers` 从已注册配置中选择

---

### 3.3 Hook 配置面

**后端 Schema 对齐**：
```python
class HookTrigger:
    event: Literal[
        "before_workflow_start", "after_workflow_end",
        "before_node_start", "after_node_end",
        "before_generate", "after_generate",
        "before_review", "after_review", "on_review_fail",
        "before_fix", "after_fix",
        "before_assistant_response", "after_assistant_response",
        "on_error"
    ]
    node_types: list[str]

class HookAction:
    action_type: Literal["script", "webhook", "agent", "mcp"]  # alias: "type"
    config: dict[str, Any]

class HookRetryConfig:
    max_attempts: int = 3
    delay: int = 1

class HookConfig:
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    author: str | None = None
    enabled: bool = True
    trigger: HookTrigger
    condition: HookCondition | None  # field, operator, value
    action: HookAction
    priority: int = 10
    timeout: int = 30
    retry: HookRetryConfig | None
```

**表单设计**：

```
┌─────────────────────────────────────────────────────────────┐
│  Hook 配置编辑                                               │
├─────────────────────────────────────────────────────────────┤
│  基本信息                                                    │
│  ────────                                                    │
│  名称 *        [pre-generate-check        ]                 │
│  版本          [1.0.0                     ]                 │
│  描述          [生成前检查钩子              ]                 │
│  作者          [easyStory Team             ]                 │
│  状态          ● 已启用  ○ 已停用                            │
│  优先级        [10                        ]                 │
│                                                             │
│  触发条件                                                    │
│  ────────                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  触发事件 *                                           │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │ Workflow 事件                                │   │   │
│  │  │   ○ before_workflow_start                   │   │   │
│  │  │   ○ after_workflow_end                      │   │   │
│  │  │ Workflow 节点事件                            │   │   │
│  │  │   ○ before_node_start                       │   │   │
│  │  │   ○ after_node_end                          │   │   │
│  │  │   ● before_generate                         │   │   │
│  │  │   ○ after_generate                          │   │   │
│  │  │   ○ before_review                           │   │   │
│  │  │   ○ after_review                            │   │   │
│  │  │   ○ on_review_fail                          │   │   │
│  │  │   ○ before_fix                              │   │   │
│  │  │   ○ after_fix                               │   │   │
│  │  │ Assistant 事件                               │   │   │
│  │  │   ○ before_assistant_response               │   │   │
│  │  │   ○ after_assistant_response                │   │   │
│  │  │ 系统事件                                     │   │   │
│  │  │   ○ on_error                                │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  │  节点类型过滤 (可选)                                  │   │
│  │  ☑ generate    ☑ review    ☐ export                 │   │
│  │  注：custom 节点类型当前不支持                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  执行条件 (可选)                                             │
│  ────────────                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  字段路径    [node.type                   ]           │   │
│  │  操作符      [==                       ▼]             │   │
│  │  值          [generate                     ]          │   │
│  │                                                      │   │
│  │  路径语法：纯点路径，不支持 {{...}} 包裹             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  动作配置                                                    │
│  ────────                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  动作类型 *                                           │   │
│  │  ● script    ○ webhook    ○ agent    ○ mcp          │   │
│  │                                                      │   │
│  │  [Script 配置面板]                                    │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │  模块路径 *                                   │   │   │
│  │  │  [hooks.pre_check                         ] │   │   │
│  │  │                                             │   │   │
│  │  │  函数名 *                                     │   │   │
│  │  │  [run_check                               ] │   │   │
│  │  │                                             │   │   │
│  │  │  执行参数 (params)                           │   │   │
│  │  │  ┌─────────────────────────────────────┐   │   │   │
│  │  │  │ {                                   │   │   │   │
│  │  │  │   "threshold": 1000,                │   │   │   │
│  │  │  │   "check_type": "word_count"        │   │   │   │
│  │  │  │ }                                   │   │   │   │
│  │  │  └─────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  │  [Webhook 配置面板]                                  │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │  URL *        [https://hooks.example.com  ] │   │   │
│  │  │  Method       [POST                     ▼] │   │   │
│  │  │  Headers      (键值对编辑器)                  │   │   │
│  │  │  Body         (JSON 编辑器)                  │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  │  [Agent 配置面板]                                    │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │  Agent ID *   [content-validator          ] │   │   │
│  │  │                                             │   │   │
│  │  │  输入映射 (input_mapping)                   │   │   │
│  │  │  ┌─────────────────────────────────────┐   │   │   │
│  │  │  │ 目标变量    源路径                    │   │   │   │
│  │  │  │ project_id  workflow.project_id      │   │   │   │
│  │  │  │ node_id     node.id                  │   │   │   │
│  │  │  └─────────────────────────────────────┘   │   │   │
│  │  │                                             │   │   │
│  │  │  路径语法：纯点路径，不支持 {{...}} 包裹      │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  │  [MCP 配置面板]                                      │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │  Server ID *  [filesystem                ] │   │   │
│  │  │  Tool Name *  [read_file                ] │   │   │
│  │  │  Arguments    (JSON 编辑器)                  │   │   │
│  │  │  Input Mapping (同 Agent 面板)               │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  执行设置                                                    │
│  ────────                                                    │
│  超时时间      [30                        ] 秒               │
│                                                             │
│  重试配置                                                    │
│  ────────                                                    │
│  ☑ 启用重试                                                  │
│  最大重试次数  [3                         ]                  │
│  重试间隔      [1                         ] 秒               │
└─────────────────────────────────────────────────────────────┘
```

**字段说明**：
- `event` 分组展示：Workflow 事件 / Workflow 节点事件 / Assistant 事件 / 系统事件
- `node_types` 可选值：`generate` / `review` / `export`（`custom` 当前不支持）
- `action_type` 切换时显示不同的配置面板
- Script 配置：`module` / `function` / `params`（不是脚本路径）
- `input_mapping` 路径语法：纯点路径，**不支持** `{{...}}` 包裹

**Payload 路径参考（按事件类型分组）**：

Workflow 事件 payload 结构（`workflow` 和 `node` 平级）：
```
{
  "event": "before_generate",
  "workflow": {
    "execution_id": "...",
    "workflow_id": "...",
    "workflow_name": "...",
    "project_id": "..."
  },
  "node": {
    "id": "...",
    "name": "...",
    "type": "generate"
  },
  "node_execution_id": "...",  // 可选
  // 额外字段按事件类型添加
}
```

| 事件类型 | 可用路径示例 | 说明 |
|----------|--------------|------|
| 所有 Workflow 事件 | `workflow.execution_id` | 执行 ID |
| 所有 Workflow 事件 | `workflow.project_id` | 项目 ID |
| 所有 Workflow 事件 | `node.id` | 节点 ID |
| 所有 Workflow 事件 | `node.type` | 节点类型 |
| `before_generate` / `after_generate` | `chapter.number` | 章节号 |
| `before_generate` / `after_generate` | `chapter.task_id` | 章节任务 ID |

Assistant 事件 payload 结构：
```
{
  "event": "before_assistant_response",
  "assistant": {
    "agent_id": "...",
    "skill_id": "...",
    "project_id": "...",
    "mcp_servers": [...]
  },
  "conversation": {
    "message_count": 3,
    "messages": [...]
  },
  "request": {
    "input_data": {...},
    "user_input": "..."
  }
}
```

| 事件类型 | 可用路径示例 | 说明 |
|----------|--------------|------|
| 所有 Assistant 事件 | `assistant.agent_id` | Agent ID |
| 所有 Assistant 事件 | `assistant.skill_id` | Skill ID |
| 所有 Assistant 事件 | `request.user_input` | 用户输入 |
| `after_assistant_response` | `response.content` | 响应内容 |

**注意**：不存在 `workflow.node.*` 这种嵌套路径，`workflow` 和 `node` 是平级的。

---

### 3.4 MCP Server 配置面

**后端 Schema 对齐**：
```python
class McpServerConfig:
    id: str
    name: str
    version: str = "1.0.0"
    description: str | None = None
    transport: Literal["streamable_http"] = "streamable_http"  # 固定值
    url: str
    headers: dict[str, str]
    timeout: int = 30
    enabled: bool = True
```

**表单设计**：

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Server 配置编辑                                         │
├─────────────────────────────────────────────────────────────┤
│  基本信息                                                    │
│  ────────                                                    │
│  名称 *        [filesystem                 ]                 │
│  版本          [1.0.0                     ]                 │
│  描述          [文件系统操作 MCP Server     ]                 │
│                                                             │
│  连接配置                                                    │
│  ────────                                                    │
│  传输方式      streamable_http (固定)                        │
│  地址 *        [http://localhost:8080/mcp  ]                 │
│  超时          [30                        ] 秒               │
│                                                             │
│  请求头配置                                                  │
│  ────────                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Key                    Value              操作      │   │
│  │  ─────────────────────────────────────────────────  │   │
│  │  Authorization          ••••••••           [👁] [🗑] │   │
│  │  X-Custom-Header        custom-value       [🗑]      │   │
│  │                                                      │   │
│  │  [+ 添加请求头]                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  状态                                                        │
│  ────                                                        │
│  ● 已启用  ○ 已停用                                          │
└─────────────────────────────────────────────────────────────┘
```

**字段说明**：
- `transport` 固定为 `streamable_http`，表单中只读展示
- `headers` 使用键值对编辑器，敏感值默认掩码
- 不设计工具发现/连通性测试（后端无接口）

---

### 3.5 Workflow 配置面

**设计决策**：保留 JSON 高级模式，不做深表单

**原因**：
- Workflow 结构复杂（nodes、edges、策略配置）
- 成本高，收益相对较低
- 当前优先级：Skill > Agent > Hook > MCP > Workflow

**表单设计**：

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow 配置编辑                                           │
├─────────────────────────────────────────────────────────────┤
│  基本信息                                                    │
│  ────────                                                    │
│  名称 *        [chapter-generation       ]                  │
│  版本          [1.0.0                     ]                  │
│  描述          [章节生成工作流             ]                  │
│                                                             │
│  ⚠ Workflow 结构复杂，建议使用 JSON 高级模式编辑             │
│                                                             │
│  当前模式：JSON 高级模式                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  {                                                   │   │
│  │    "id": "chapter-generation",                       │   │
│  │    "name": "章节生成工作流",                          │   │
│  │    "mode": "auto",                                   │   │
│  │    "nodes": [...]                                    │   │
│  │  }                                                   │   │
│  │                                                      │   │
│  │  注：mode 合法值为 "manual" 或 "auto"                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 模型配置统一组件

### 4.1 设计目标

- 统一凭证页和配置中心的模型配置心智模型
- 展示默认来源、是否覆写、最终生效值
- 不做远端模型自动发现（后端无接口）

### 4.2 组件设计

```
┌─────────────────────────────────────────────────────────────┐
│  模型配置                                                    │
├─────────────────────────────────────────────────────────────┤
│  ☐ 使用自定义模型配置（不勾选则使用全局/凭证默认）            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Provider                                             │   │
│  │  [openrouter                              ▼]         │   │
│  │                                                      │   │
│  │  Model Name                                           │   │
│  │  [claude-sonnet-4-20250514                 ]         │   │
│  │                                                      │   │
│  │  Temperature                                          │   │
│  │  [0.7    ] 滑块: 0.0 ──●────────────── 2.0           │   │
│  │                                                      │   │
│  │  Max Tokens                                           │   │
│  │  [4000   ]                                           │   │
│  │                                                      │   │
│  │  Top P                                                │   │
│  │  [1.0    ] 滑块: 0.0 ─────────────●── 1.0            │   │
│  │                                                      │   │
│  │  ▶ 高级参数                                           │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │  Frequency Penalty  [                    ]   │   │
│  │  │  Presence Penalty   [                    ]   │   │
│  │  │  Stop Sequences     [                    ]   │   │
│  │  │  Required Capabilities [                  ]   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 字段映射

| 表单字段 | Schema 字段 | 类型 | 默认值 |
|----------|-------------|------|--------|
| Provider | `provider` | `string \| None` | - |
| Model Name | `name` | `string \| None` | - |
| Temperature | `temperature` | `float` | 0.7 |
| Max Tokens | `max_tokens` | `int` | 4000 |
| Top P | `top_p` | `float \| None` | - |
| Frequency Penalty | `frequency_penalty` | `float \| None` | - |
| Presence Penalty | `presence_penalty` | `float \| None` | - |
| Stop Sequences | `stop` | `list[str] \| None` | - |
| Required Capabilities | `required_capabilities` | `list[str]` | [] |

---

## 5. 通用增强

### 5.1 侧边栏搜索与过滤

**注意**：过滤选项需按类型区分，因为字段并不通用：
- `enabled` 字段仅存在于 Hook 和 MCP Summary
- `tags` 字段仅存在于 Skill、Agent、Workflow Summary
- Summary/Detail DTO 无 `updated_at` 字段，不支持按更新时间排序

```
┌─────────────────────────────┐
│  [🔍 搜索配置名称、ID...]    │
├─────────────────────────────┤
│  排序方式                    │
│  [名称 A-Z ▼]               │
│  ○ 名称 A-Z                 │
│  ○ 名称 Z-A                 │
├─────────────────────────────┤
│  类型过滤（按当前类型显示）  │
│  ────────────────────────   │
│  Skills/Agents/Workflows:   │
│    标签过滤                  │
│    [generation] [polish]    │
│    [review] [export]        │
│                              │
│  Hooks/MCP:                 │
│    状态过滤                  │
│    [全部] [已启用] [已停用]  │
└─────────────────────────────┘
```

### 5.2 离页保护

**触发场景**：
1. 切换配置项（拦截 `onSelectItem`）
2. 切换配置类型（拦截 `onSelectType`）
3. 关闭页面/刷新（`beforeunload`）

**实现方式**：
```typescript
// 当前页面入口：config-registry-page.tsx
// 导航通过 router.replace(...) 改变 query 参数

const { isDirty } = useUnsavedChanges(editorValue, originalValue);

// 拦截本地导航动作
const handleSelectItem = useCallback((id: string) => {
  if (isDirty) {
    showConfirmDialog({
      message: "有未保存的更改，确定要离开吗？",
      onConfirm: () => router.replace(`?type=${type}&item=${id}`),
    });
  } else {
    router.replace(`?type=${type}&item=${id}`);
  }
}, [isDirty, type, router]);

// beforeunload 处理页面关闭/刷新
useEffect(() => {
  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (isDirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  };
  window.addEventListener("beforeunload", handleBeforeUnload);
  return () => window.removeEventListener("beforeunload", handleBeforeUnload);
}, [isDirty]);
```

**注意**：不要使用 middleware 处理 dirty-state 保护，因为当前页面是客户端渲染，所有导航都是本地 `router.replace(...)` 调用。

### 5.3 字段级错误提示

**前端校验**：
- 必填字段非空
- 类型格式校验（integer、float、url）
- Schema JSON 格式校验
- 变量名格式校验（字母开头，允许下划线）

**后端错误映射**：
- 解析 422 错误
- 映射到对应字段
- 显示错误提示

### 5.4 异步反馈 aria-live

```tsx
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className={feedback.tone === "danger" ? "error-banner" : "info-banner"}
>
  {feedback.message}
</div>
```

---

## 6. 实施路线

### 阶段 1：基础架构（1-2 天）

1. **双模式编辑器框架**
   - 创建 `ConfigEditorProvider` 上下文
   - 实现 `form` / `json` 模式切换
   - 添加模式切换时的数据转换

2. **侧边栏增强**
   - 添加搜索框
   - 添加状态过滤
   - 添加排序选项

3. **离页保护**
   - 实现 `useUnsavedChanges` hook
   - 添加 `beforeunload` 事件
   - 添加切换确认弹窗

### 阶段 2：Skill + Agent 配置面（2-3 天）

1. **Skill 配置面**
   - 基本信息表单
   - Prompt 编辑器（纯文本 + 变量高亮）
   - 变量定义表（variables / inputs/outputs 模式切换）
   - 模型配置组件

2. **Agent 配置面**
   - 基本信息表单
   - 类型选择（writer/reviewer/checker）
   - 系统提示词编辑器
   - 技能绑定选择器
   - MCP Server 绑定选择器
   - 输出 Schema 编辑器
   - 模型配置组件

### 阶段 3：Hook + MCP 配置面（1-2 天）

1. **Hook 配置面**
   - 基本信息表单
   - 触发事件选择（分组展示）
   - 节点类型过滤
   - 执行条件编辑
   - 动作类型切换面板
   - 重试配置

2. **MCP 配置面**
   - 基本信息表单
   - 连接配置
   - 请求头键值对编辑器

### 阶段 4：校验与体验优化（1 天）

1. **字段级校验**
   - 前端实时校验
   - 后端错误映射

2. **可访问性**
   - aria-live 到异步反馈
   - name / autocomplete 到表单字段

---

## 7. 组件结构

```
apps/web/src/features/config-registry/components/
├── config-registry-page.tsx           # 主页面（保留）
├── config-registry-sidebar.tsx        # 侧边栏（增强）
├── config-registry-detail-panel.tsx   # 中栏详情（保留）
├── config-registry-editor-panel.tsx   # 右栏编辑器（重构）
├── config-registry-support.ts         # 工具函数（保留）
│
├── editors/
│   ├── config-editor-provider.tsx     # 编辑器上下文
│   ├── config-editor-toolbar.tsx      # 模式切换工具栏
│   ├── json-editor.tsx                # JSON 模式编辑器
│   └── form-editor.tsx                # 表单模式入口
│
├── panels/
│   ├── skill-form-panel.tsx           # Skill 表单
│   ├── agent-form-panel.tsx           # Agent 表单
│   ├── hook-form-panel.tsx            # Hook 表单
│   ├── mcp-form-panel.tsx             # MCP 表单
│   └── workflow-json-panel.tsx        # Workflow JSON 编辑器
│
├── fields/
│   ├── prompt-editor-field.tsx        # Prompt 编辑器
│   ├── schema-field-table.tsx         # SchemaField 表格编辑器
│   ├── model-config-field.tsx         # 模型配置组件
│   ├── headers-editor-field.tsx       # 请求头编辑器
│   ├── binding-selector-field.tsx     # 绑定选择器
│   └── event-selector-field.tsx       # 事件选择器
│
└── hooks/
    ├── use-unsaved-changes.ts         # 离页保护
    ├── use-field-validation.ts        # 字段校验
    └── use-config-editor.ts           # 编辑器状态管理
```

---

## 8. 依赖决策

### 8.1 不引入的依赖

| 依赖 | 原因 |
|------|------|
| `monaco-editor` | 当前 textarea 可用，优先做结构化表单 |
| `react-hook-form` | 表单复杂度可控，先用原生 React 状态管理 |
| `zod` | 后端已有 Pydantic 校验，前端做基础校验即可 |

### 8.2 可考虑引入的依赖

| 依赖 | 场景 | 决策 |
|------|------|------|
| `@uiw/react-textarea-code-editor` | JSON 编辑器语法高亮 | 可选，阶段 4 考虑 |
| `react-hotkeys-hook` | 快捷键支持 | 可选，阶段 4 考虑 |

---

## 9. 风险与约束

### 9.1 后端约束

| 约束 | 影响 |
|------|------|
| 无 create/delete API | 不设计新建/删除功能 |
| MCP 仅 streamable_http | 不设计传输方式选择 |
| 无模型发现 API | 不设计自动发现功能 |
| 无 MCP 工具发现 API | 不设计工具发现 UI |

### 9.2 设计约束

| 约束 | 原因 |
|------|------|
| Workflow 保留 JSON 模式 | 结构复杂，成本高 |
| 不做富文本编辑器 | Prompt 是模板文本，不是文档 |
| 不设计失败处理开关 | 后端 schema 无此字段 |

---

## 10. 验收标准

### 10.1 功能验收

- [ ] 双模式编辑器可正常切换
- [ ] 侧边栏搜索/过滤/排序可用
- [ ] 离页保护正常触发
- [ ] Skill 表单可正确提交
- [ ] Agent 表单可正确提交
- [ ] Hook 表单可正确提交
- [ ] MCP 表单可正确提交
- [ ] Workflow JSON 编辑器可用

### 10.2 体验验收

- [ ] 字段级错误提示清晰
- [ ] 异步反馈有 aria-live
- [ ] 表单字段有 name/autocomplete
- [ ] 切换配置项时未保存提醒
- [ ] 关闭页面时未保存提醒

---

## 审核记录

| 日期 | 审核人 | 状态 | 备注 |
|------|--------|------|------|
| 2026-03-26 | - | 待审核 | 初始版本 |
| 2026-03-26 | - | 待审核 | 修正 7 个文档级错误：1) Hook script 配置改为 module/function/params；2) Hook 路径语法改为纯点路径；3) Agent system_prompt 说明不支持模板变量；4) Hook node_types 改为 generate/review/export；5) Workflow mode 改为 manual/auto；6) 移除更新时间排序；7) 过滤选项按类型区分 |
| 2026-03-26 | - | 待审核 | 修正 4 个遗留问题：1) Hook payload 路径按事件分组，明确 workflow/node 平级；2) 离页保护改为拦截本地导航动作；3) 添加 URL 状态同步要求；4) 修正审核记录日期 |
