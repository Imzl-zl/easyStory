# easyStory 配置格式规范

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-14 |
| 更新时间 | 2026-03-23 |
| 关联文档 | [系统架构设计](./architecture.md)、[数据库设计](./database-design.md) |

---

## 1. 配置存储位置

**决策**：文件系统存储

**目录结构**：
```
/config/                           # 配置根目录（Git 管理）
├── skills/                        # Skills 配置
│   ├── outline/                   # 大纲类
│   │   └── *.yaml
│   ├── opening_plan/              # 开篇设计类
│   │   └── *.yaml
│   ├── chapter/                   # 章节类
│   │   └── *.yaml
│   ├── character/                 # 人物类
│   │   └── *.yaml
│   ├── project_setting/           # 项目设定提取/整理类
│   │   └── *.yaml
│   ├── world_setting/             # 世界观类
│   │   └── *.yaml
│   └── review/                    # 审核类
│       └── *.yaml
│
├── agents/                        # Agents 配置
│   ├── writers/                   # 写作类
│   │   └── *.yaml
│   └── reviewers/                 # 审核类
│       └── *.yaml
│
├── hooks/                         # Hooks 配置
│   └── *.yaml
│
├── mcp_servers/                   # MCP Server 配置
│   └── *.yaml
│
├── workflows/                     # Workflows 配置
│   └── *.yaml
```

**选择理由**：
1. **Git 版本管理**：配置变更可追踪、可回滚
2. **分享简单**：直接分享 YAML 文件
3. **开发方便**：IDE 语法高亮、本地调试
4. **Web UI 同步**：编辑后自动更新文件

**命名规范**：
- 文件名：`{name}.yaml`（小写字母 + 连字符）
- ID 在文件内部定义
- 示例：`style-checker.yaml` → `id: "agent.style_checker"`

> 本节约束的是 Git 管理的业务配置目录 `/config`。后端运行时环境配置不放在 `/config`，而是通过 `apps/api/.env` 注入，详见 [8.1 后端运行时 Settings](#81-后端运行时-settings)。

---

## 2. 配置文件格式

**决策**：YAML

**选择理由**：
1. **多行字符串**：提示词天然是多行文本，YAML 原生支持
2. **注释支持**：配置文件需要注释说明
3. **可读性好**：更接近自然语言
4. **业界标准**：GitHub Actions、Kubernetes 都用 YAML

**格式示例**：
```yaml
# 这是一个 Skill 配置示例
skill:
  id: "skill.chapter.xuanhuan"
  name: "玄幻章节生成"

  # 提示词模板（多行字符串）
  prompt: |
    你是一位资深的玄幻小说作家。

    请根据以下信息生成章节：
    - 世界观：{{ world_setting }}
    - 大纲：{{ outline }}

  # 模型配置（不含凭证）
  model:
    provider: "anthropic"
    name: "claude-sonnet-4-20250514"
    temperature: 0.8
    max_tokens: 4000
```

---

## 3. Skill 配置格式

**用途**：定义 AI 技能包，包含提示词模板和模型配置。

**完整格式**：
```yaml
skill:
  id: "skill.chapter.xuanhuan"        # 必填，唯一标识
  name: "玄幻章节生成"                 # 必填，显示名称
  version: "1.0.0"                    # 可选，版本号
  description: "生成玄幻小说章节"       # 可选，描述
  category: "chapter"                 # 必填，分类
  author: "user"                      # 可选，作者
  tags: ["玄幻", "章节"]              # 可选，标签
  
  prompt: |                           # 必填，提示词模板
    你是一位资深的玄幻小说作家。
    
    请根据以下信息生成章节：
    【世界观设定】
    {{ world_setting }}
    
    【大纲】
    {{ outline }}
    
    【前文回顾】
    {{ previous_content }}
    
    【本章任务】
    {{ chapter_task }}
    
    要求：
    1. 字数控制在 {{ target_words }} 字左右
    2. 保持文风一致
  
  variables:                          # 可选，模板变量定义
    world_setting:
      type: "string"                  # 类型：string/integer/boolean/array/object
      required: true                  # 是否必填
      description: "世界观设定"        # 描述
    outline:
      type: "string"
      required: true
    previous_content:
      type: "string"
      required: false
      default: ""                     # 默认值
    chapter_task:
      type: "string"
      required: true
    target_words:
      type: "integer"
      required: false
      default: 3000
  
  model:                              # 可选，模型配置（不含凭证）
    provider: "anthropic"             # 可选：openai/anthropic/deepseek/...
    name: "claude-sonnet-4-20250514"  # 可选：具体模型名（可被 workflow/node 覆盖）
    required_capabilities:            # 可选：运行该 Skill 所需能力
      - "streaming"
      - "long_context"
    temperature: 0.8                  # 温度（0-2）
    max_tokens: 4000                  # 最大 token 数
    top_p: 0.9                        # Top-p 采样
    frequency_penalty: 0.0            # 频率惩罚
    presence_penalty: 0.0             # 存在惩罚
    stop: ["---END---"]               # 停止词
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `id` | string | ✅ | 唯一标识，格式：`skill.{category}.{name}` |
| `name` | string | ✅ | 显示名称 |
| `version` | string | ❌ | 版本号，默认 `1.0.0` |
| `description` | string | ❌ | 描述 |
| `category` | string | ✅ | 分类：outline/opening_plan/chapter/character/world_setting/review |
| `author` | string | ❌ | 作者 |
| `tags` | array | ❌ | 标签列表 |
| `prompt` | string | ✅ | 提示词模板，支持 Jinja2 语法 |
| `variables` | object | ❌ | 简单模式：模板变量定义（与 `inputs`/`outputs` **互斥**） |
| `inputs` | object | ❌ | 增强模式：输入 Schema（严格校验，与 `variables` **互斥**，见下） |
| `outputs` | object | ❌ | 增强模式：输出 Schema（与 `variables` **互斥**，见下） |
| `model` | object | ❌ | 模型配置（不含凭证，含 provider/name、参数，以及可选 `required_capabilities`） |

> **`variables` vs `inputs`/`outputs`**：两者是互斥的配置模式。`variables` 是简单模式，只定义类型和默认值；`inputs`/`outputs` 是增强模式，支持 enum、min/max、min_length 等约束校验。同一个 Skill 中不可同时使用两种模式，编译时校验会报错。

### Skill 输入输出 Schema（增强版）

当需要更严格的校验时，可以用 `inputs`/`outputs` 替代简单的 `variables`：

```yaml
skill:
  id: "skill.outline.xuanhuan"
  inputs:
    genre:
      type: "string"
      required: true
      description: "小说题材"
      enum: ["玄幻", "都市", "科幻", "言情"]
    character_profile:
      type: "string"
      required: true
      description: "人物设定投影视图"
      min_length: 2
      max_length: 1200
    target_chapters:
      type: "integer"
      required: false
      default: 50
      min: 10
      max: 500

  outputs:
    outline_text:
      type: "string"
      required: true
      min_length: 100
    chapter_count:
      type: "integer"
      required: true
    chapter_list:
      type: "array"
      items:
        type: "object"
        properties:
          number: { type: "integer" }
          title: { type: "string" }
          brief: { type: "string" }
```

工作流启动前会对 Skill 的 inputs/outputs 进行编译校验，详见 [跨模块契约](../design/17-cross-module-contracts.md)。

**分类说明**：

| 分类 | 说明 | ID 前缀示例 |
|-----|------|------------|
| `outline` | 大纲生成 | `skill.outline.*` |
| `opening_plan` | 开篇设计生成 | `skill.opening_plan.*` |
| `chapter` | 章节生成 | `skill.chapter.*` |
| `character` | 人物设定 | `skill.character.*` |
| `project_setting` | 项目设定提取/整理 | `skill.project_setting.*` |
| `world_setting` | 世界观设定 | `skill.world_setting.*` |
| `review` | 审核 | `skill.review.*` |

---

## 4. Agent 配置格式

**用途**：定义 AI 智能体，包含系统提示词和关联技能。

**完整格式**：
```yaml
agent:
  id: "agent.style_checker"           # 必填，唯一标识
  name: "文风检查员"                   # 必填，显示名称
  version: "1.0.0"                    # 可选，版本号
  description: "检查内容文风是否符合设定" # 可选，描述
  type: "reviewer"                    # 必填，类型
  author: "user"                      # 可选，作者
  tags: ["审核", "文风"]              # 可选，标签
  
  system_prompt: |                    # 必填，系统提示词
    你是一位专业的小说文风审核专家。
    你的任务是检查内容是否符合以下要求：
    1. 文风是否一致
    2. 是否有突兀的转折
    3. 是否有重复的表达
    4. 是否有不当的用词
    
    请给出评分（0-100）和具体建议。
  
  skills:                             # 可选，关联的技能
    - "skill.review.style"
  
  model:                              # 可选，模型配置（不含凭证）
    provider: "openai"
    name: "gpt-4o"
    required_capabilities:
      - "json_schema_output"
    temperature: 0.3                  # 审核用低温度
    max_tokens: 1000

  # reviewer 类型输出固定为 ReviewResult（不允许自定义 output_schema，见 docs/design/03-review-and-fix.md）

  mcp_servers: []                     # 可选，MCP Server 列表（MVP 为空，第二阶段启用）
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `id` | string | ✅ | 唯一标识，格式：`agent.{name}`（如 `agent.style_checker`） |
| `name` | string | ✅ | 显示名称 |
| `version` | string | ❌ | 版本号 |
| `description` | string | ❌ | 描述 |
| `type` | string | ✅ | 类型：writer/reviewer/checker |
| `system_prompt` | string | ✅ | 系统提示词 |
| `skills` | array | ❌ | 关联的技能 ID 列表 |
| `model` | object | ❌ | 模型配置（不含凭证，含 provider/name、参数，以及可选 `required_capabilities`） |
| `output_schema` | object | ❌ | 输出格式定义（JSON Schema）。仅 writer/checker 可用；reviewer 固定为 ReviewResult |
| `mcp_servers` | array | ❌ | MCP Server 列表；当前可用于 assistant / hook runtime 的能力装配 |

**类型说明**：

| 类型 | 说明 | ID 前缀示例 |
|-----|------|------------|
| `writer` | 写作类 | `agent.writers.*` |
| `reviewer` | 审核类 | `agent.reviewers.*` |
| `checker` | 检查类 | `agent.checkers.*` |

---

### MCP Server 配置格式

**用途**：定义可被 Hook / Assistant runtime 调用的外部 MCP Server。

```yaml
mcp_server:
  id: "mcp.news.lookup"
  name: "新闻检索 MCP"
  version: "1.0.0"
  description: "通过 streamable_http 暴露新闻检索工具"
  transport: "streamable_http"
  url: "https://example.com/mcp"
  headers: {}
  timeout: 30
  enabled: true
```

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `id` | string | ✅ | 唯一标识，格式：`mcp.{name}` |
| `name` | string | ✅ | 显示名称 |
| `transport` | string | ✅ | 当前支持 `streamable_http` |
| `url` | string | ✅ | MCP Server 地址 |
| `headers` | object | ❌ | 静态请求头 |
| `timeout` | integer | ❌ | 请求超时秒数，默认 30 |
| `enabled` | boolean | ❌ | 是否启用，默认 true |

---

## 5. Hook 配置格式

**用途**：定义钩子，在特定时机自动执行操作。

**完整格式**：
```yaml
hook:
  id: "hook.auto_save"                # 必填，唯一标识
  name: "自动保存"                     # 必填，显示名称
  version: "1.0.0"                    # 可选，版本号
  description: "生成后自动保存内容"     # 可选，描述
  author: "user"                      # 可选，作者
  enabled: true                       # 可选，是否启用，默认 true
  
  trigger:                            # 必填，触发条件
    event: "after_generate"           # 触发事件
    node_types:                       # 适用的节点类型（可选）
      - "generate"
      - "fix"
  
  condition:                          # 可选，额外触发条件
    field: "status"                   # 字段名
    operator: "=="                    # 操作符：==/!=/>/</>=/<=/in/not_in
    value: "completed"                # 值
  
  action:                             # 必填，执行动作
    type: "script"                    # 当前内置：script/webhook/agent/mcp
    config:
      module: "app.hooks.builtin"     # 模块路径（script 类型）
      function: "auto_save_content"   # 函数名
      params:                         # 参数
        save_version: true
  
  priority: 10                        # 可选，优先级，数字越小越先执行
  timeout: 30                         # 可选，超时时间（秒）
  retry:                              # 可选，重试配置（仅对当前 hook 的 action 生效，不等同 workflow.retry）
    max_attempts: 3
    delay: 1                          # 重试间隔（秒）
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `id` | string | ✅ | 唯一标识，格式：`hook.{name}` |
| `name` | string | ✅ | 显示名称 |
| `trigger.event` | string | ✅ | 触发事件 |
| `trigger.node_types` | array | ❌ | 适用的节点类型 |
| `condition` | object | ❌ | 额外触发条件 |
| `action.type` | string | ✅ | 动作类型（通过 PluginRegistry 分发，可扩展）。当前内置：script/webhook/agent/mcp |
| `action.config` | object | ✅ | 动作配置 |
| `priority` | integer | ❌ | 优先级，默认 10 |
| `enabled` | boolean | ❌ | 是否启用，默认 true |

**触发事件列表**：

| 事件 | 说明 | 触发时机 |
|-----|------|---------|
| `before_workflow_start` | 工作流开始前 | 用户点击开始 |
| `after_workflow_end` | 工作流结束后 | 所有节点完成 |
| `before_node_start` | 节点开始前 | 节点执行前 |
| `after_node_end` | 节点结束后 | 节点执行后 |
| `before_generate` | 生成前 | 调用 AI 前 |
| `after_generate` | 生成后 | AI 返回结果后 |
| `before_review` | 审核前 | 开始审核前 |
| `after_review` | 审核后 | 审核完成后 |
| `on_review_fail` | 审核失败 | 审核不通过时 |
| `before_fix` | 精修前 | 开始精修前 |
| `after_fix` | 精修后 | 精修完成后 |
| `before_assistant_response` | Assistant 回复前 | assistant 调用模型前 |
| `after_assistant_response` | Assistant 回复后 | assistant 返回结果后 |
| `on_error` | 错误发生 | 任何错误时 |

**动作类型说明**：

| 类型 | 说明 | config 字段 |
|-----|------|------------|
| `script` | 执行 Python 函数 | `module`, `function`, `params` |
| `webhook` | 调用 HTTP 接口 | `url`, `method`, `headers`, `body` |
| `agent` | 调用 Agent | `agent_id`, `input_mapping` |
| `mcp` | 调用 MCP 工具 | `server_id`, `tool_name`, `arguments`, `input_mapping` |

> `action.type` 通过 PluginRegistry 分发，支持扩展新类型。当前内置 script/webhook/agent/mcp 四种；其中 `mcp` 走官方 MCP client，当前仅支持 `streamable_http` transport。
> 事件适用边界：`before_assistant_response` / `after_assistant_response` 仅用于 assistant runtime；不能挂到 workflow 节点的 `hooks.before/after`。workflow 节点钩子的 stage 也必须与事件方向一致，例如 `before_generate` 只能放 `before`，`after_generate` 只能放 `after`。

---

## 6. Workflow 配置格式

**用途**：定义工作流，包含节点列表和执行规则。

**完整格式**：
```yaml
workflow:
  id: "workflow.xuanhuan_auto"        # 必填，唯一标识
  name: "玄幻小说自动创作"              # 必填，显示名称
  version: "1.0.0"                    # 可选，版本号
  description: "全自动玄幻小说创作流程" # 可选，描述
  author: "user"                      # 可选，作者
  tags: ["玄幻", "全自动"]            # 可选，标签

  mode: "auto"                        # 必填，工作模式：manual / auto（不引入 hybrid；混合体验用节点级覆盖 + loop.pause 表达）

  settings:                           # 可选，全局设置
    auto_proceed: true                # 审核通过后自动进入下一步
    auto_review: true                 # 默认是否自动审核（节点级可覆盖）
    auto_fix: true                    # 默认审核失败是否自动精修（节点级可覆盖）
    save_on_step: true                # 每步自动保存
    default_pass_rule: "no_critical"  # 默认审核聚合规则
    default_fix_skill: null           # 可选，工作流级默认精修 Skill（节点未配 fix_skill 时回退到此）

  budget:                             # 可选，Token 预算配置
    max_tokens_per_node: 50000        # 单节点最大 token
    max_tokens_per_workflow: 500000   # 单次工作流最大 token
    max_tokens_per_day: 2000000       # 每日最大 token（项目级）
    max_tokens_per_day_per_user: 3000000  # 每日最大 token（用户级，可选）
    warning_threshold: 0.8            # 80% 时告警；展示值和生效值一致，不静默偏移
    on_exceed: "pause"                # 超预算策略: pause / skip / fail

  safety:                             # 可选，执行安全阀
    max_retry_per_node: 3             # 单节点最大重试
    max_fix_attempts: 3               # 最大精修次数
    max_total_retries: 10             # 整个工作流最大重试总数
    execution_timeout: 3600           # 工作流超时（秒）
    node_timeout: 300                 # 单节点超时（秒）

  retry:                              # 可选，重试策略
    strategy: "exponential_backoff"   # 退避策略: exponential_backoff / fixed / none
    initial_delay: 1                  # 初始延迟（秒）
    max_delay: 30                     # 最大延迟（秒）
    max_attempts: 3                   # 最大重试次数
    retryable_errors:                 # 可重试错误白名单（仅这些会触发重试）
      - "timeout"
      - "rate_limit"
      - "server_error"

  # 说明：`workflow.retry` 只负责 LLM 调用层的瞬时错误重试（如 timeout/429/5xx），不影响节点级 `on_fail` 行为。
  # 节点执行级的“重跑次数”由 `workflow.safety.max_retry_per_node` 控制；精修轮次上限由 `workflow.safety.max_fix_attempts` / `nodes[].max_fix_attempts` 控制。

  model_fallback:                     # 可选，模型降级策略
    enabled: false                    # 默认关闭
    chain:                            # 降级链
      - model: "claude-sonnet-4-20250514"
      - model: "gpt-4o"
      - model: "deepseek-v3"
    on_all_fail: "pause"              # 全部失败后的动作：pause / fail
  
  context_injection:                  # 可选，上下文注入规则
    enabled: true
    rules:
      - node_pattern: "chapter_*"     # 匹配章节节点（支持通配符）
        inject:
          - type: "project_setting"   # 长期约束
            required: true
          - type: "outline"           # 主线约束
            required: true            # 是否必填
          - type: "opening_plan"      # 前 1-3 章通常高优先级注入，后续章节按需降级
            required: false
          - type: "chapter_task"      # 当前章节任务（ChapterTask）
            required: true
          - type: "previous_chapters"
            count: 2                  # 前 2 章
            required: false
          - type: "story_bible"
            required: false
          - type: "style_reference"  # 分析结果风格参考（项目级显式绑定）
            analysis_id: "00000000-0000-0000-0000-000000000001"
            inject_fields:
              - "writing_style"
              - "narrative_perspective"
            required: false
  
  nodes:                              # 必填，节点列表
    - id: "outline"                   # 节点 ID
      name: "生成大纲"                 # 节点名称
      type: "generate"                # 节点类型
      skill: "skill.outline.xuanhuan" # 使用的技能
      auto_proceed: false             # 节点级覆盖：强制人工确认

      hooks:                          # 节点级钩子
        before:
          - "hook.validate_input"
        after:
          - "hook.auto_save"

      auto_review: true               # 是否自动审核
      review_mode: "parallel"         # 审核模式：parallel / serial
      reviewers:                      # 审核 agents
        - "agent.consistency_checker"
      review_config:                  # 审核配置
        pass_rule: "no_critical"      # 聚合规则: all_pass / majority_pass / no_critical
        re_review_scope: "all"        # 精修后重审范围: all / failed_only

      auto_fix: true                  # 是否自动精修
      max_fix_attempts: 3             # 最大精修次数
      fix_skill: "skill.fix.xuanhuan" # 精修 Skill（回退链：节点 fix_skill → workflow.settings.default_fix_skill → 内置默认 Prompt）
      fix_strategy:                   # 精修策略
        selection_rule: "auto"        # auto / targeted / full_rewrite
        targeted_threshold: 3         # 问题 ≤ 3 → 局部修改
        rewrite_threshold: 6          # 问题 > 6 → 整篇重写
        # 3-6 个之间 → 当前 runtime 仍局部精修
      on_fix_fail: "pause"            # 精修失败后动作：pause/skip/fail

    - id: "opening_plan"
      name: "生成开篇设计"
      type: "generate"
      skill: "skill.opening_plan.xuanhuan"
      depends_on: ["outline"]         # 依赖的节点

      auto_review: true
      reviewers:
        - "agent.consistency_checker"

    - id: "chapter_split"
      name: "拆分章节任务"
      type: "generate"
      skill: "skill.chapter_split"
      depends_on: ["outline", "opening_plan"]

    - id: "chapter_gen"
      name: "生成章节"
      type: "generate"
      skill: "skill.chapter.xuanhuan"
      depends_on: ["chapter_split"]

      loop:                           # 循环配置
        enabled: true
        count_from: "chapter_split"   # 从章节任务拆分结果获取数量
        item_var: "chapter_index"     # 循环变量名
        pause:                        # 可选：循环内暂停策略（用于“自动 + 每 N 章人工检查”等混合体验）
          strategy: "every_n"         # none / every / every_n
          every_n: 10                 # strategy=every_n 时必填；每 10 章暂停一次
          # 未配置 pause 时：manual 模式默认 every；auto 模式默认 none

      hooks:
        before:
          - "hook.inject_context"
        after:
          - "hook.auto_save"
      
      auto_review: true
      reviewers:
        - "agent.style_checker"
        - "agent.banned_words_checker"
        - "agent.ai_flavor_checker"
        - "agent.plot_consistency_checker"
      auto_fix: true
      max_fix_attempts: 2
      on_fix_fail: "pause"
    
    - id: "export"
      name: "导出成稿"
      type: "export"
      depends_on: ["chapter_gen"]
      
      formats:
        - "txt"
        - "markdown"
        # - "docx"                   # 建议简化预留；PDF 延后，不进入 MVP 枚举
```

> 导出格式口径：MVP 必须支持 `txt`、`markdown`；`docx` 为建议简化预留；`pdf` 延后。

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| `id` | string | ✅ | 唯一标识，格式：`workflow.{name}` |
| `name` | string | ✅ | 显示名称 |
| `mode` | string | ✅ | 工作模式：`manual`（手动）/ `auto`（自动） |
| `settings` | object | ❌ | 全局设置 |
| `budget` | object | ❌ | Token 预算配置（详见 [08-cost-and-safety](../design/08-cost-and-safety.md)） |
| `safety` | object | ❌ | 执行安全阀配置（详见 [08-cost-and-safety](../design/08-cost-and-safety.md)） |
| `retry` | object | ❌ | 重试策略 |
| `model_fallback` | object | ❌ | 显式启用的模型切换策略（默认关闭） |
| `context_injection` | object | ❌ | 上下文注入规则 |
| `nodes` | array | ✅ | 节点列表 |

> 运行时只有在 `model_fallback.enabled=true` 时才会执行模型切换；执行前会先按当前 Skill / Agent / Node 的 `model.required_capabilities` 过滤不兼容的备选模型。

**节点类型说明**：

| 类型 | 说明 | 必填字段 |
|-----|------|---------|
| `generate` | 生成内容 | `skill` |
| `review` | 审核内容 | `reviewers` |
| `export` | 导出文件 | `formats` |
| `custom` | 自定义节点（**MVP 延期，v0.2 实现**） | `action` |

**当前 runtime 支持的上下文注入类型**：

| 类型 | 说明 | 参数 |
|-----|------|------|
| `project_setting` | 项目设定（结构化设定文档） | - |
| `outline` | 大纲 | - |
| `opening_plan` | 开篇设计（前 1-3 章的阶段约束） | - |
| `world_setting` | 基于 `ProjectSetting.world_setting` 的结构化投影视图 | - |
| `character_profile` | 基于 `ProjectSetting.protagonist/key_supporting_roles` 的人物设定投影视图 | - |
| `chapter_task` | 当前章节任务（来自 ChapterTask） | - |
| `previous_chapters` | 前 N 章 | `count` |
| `chapter_summary` | 基于 `chapter` 当前版本派生的轻量摘要视图 | `count` |
| `story_bible` | Story Bible 事实库 | - |
| `style_reference` | 基于分析结果的风格参考，仅允许引用 `analysis_type=style` 的记录；目标分析缺失时会直接报错；当前 runtime 默认最多 500 tokens，超出会先在 section 内裁剪并在上下文报告中暴露原始 token | `analysis_id`、`inject_fields` |

以下类型仍属扩展预留，**当前 schema 会直接拒绝**，不能写入现有 workflow 配置：
`chapter_list`、`writing_preferences`、`foreshadowing_reminder`、`custom`

> `chapter_summary` 当前实现采用 deterministic excerpt：直接基于既有 `chapter` 的 current version 生成轻量摘要视图，不新建摘要表，也不引入 LLM 自动摘要链路。
>
> `world_setting` 与 `character_profile` 当前实现也采用 deterministic projection：直接从 `ProjectSetting` 投影生成，不新建世界观/角色主表。

> `style_reference` 需要绑定项目内真实 `analysis_id`，且该记录必须是 `analysis_type=style`；若目标分析被删除或不属于当前项目，runtime 会直接报错而不是静默跳过。同时它属于体验型上下文，当前 runtime 默认会把单个 `style_reference` section 收敛到 500 tokens 以内，并在上下文报告中保留裁剪前后的 token 信息。因此更适合写入项目运行时 workflow snapshot 或用户显式保存的项目配置；不建议把仓库共享的内置 workflow YAML 固化为某个具体项目的分析 UUID。

---

## 7. 模型配置与凭证（约束）

**决策**：任何 API Key/凭证不允许出现在 YAML（包括 `${ENV}` 引用）。凭证统一存于数据库 `model_credentials`（AES-256-GCM 加密），通过 Web UI 管理，详见 `docs/design/10-user-and-credentials.md`。

### 7.1 model 对象（在 Skill/Agent/Workflow/Node 中复用）

```yaml
model:
  provider: "anthropic"             # 凭证渠道键 / Provider Key
  name: "claude-sonnet-4-20250514"  # 可选；未填时回退到凭证 default_model
  required_capabilities:            # 可选，能力要求
    - "streaming"
    - "json_schema_output"
  temperature: 0.7
  max_tokens: 4000
  top_p: 0.9
```

推荐能力标签：
- `json_schema_output`：稳定输出结构化 JSON / Schema
- `long_context`：支持大上下文
- `streaming`：支持流式输出
- `tool_calling`：支持工具调用

> 当工作流显式配置并启用了 `model_fallback.chain` 时，运行时会先过滤不满足 `required_capabilities` 的模型，再按切换链顺序尝试；所有候选失败后只允许 `pause/fail`，不允许自动跳过关键节点。

### 7.2 选择优先级（高 → 低）

```
节点级 model > Skill 级 model > 工作流级 model > 项目级默认 model > 全局默认 model
```

> `provider` 用于选择凭证（项目级 > 用户级 > 系统级默认凭证池[仅显式允许]），`name` 优先选择具体模型；未显式填写时，运行时回退到所解析凭证上的 `default_model`。HTTP 协议由凭证的 `api_dialect` 决定，而不是由 `provider` 猜测。

---

## 8. 配置加载机制

### 8.1 后端运行时 Settings

后端运行时环境配置与 `/config/*.yaml` 属于不同边界：

- `/config/*.yaml` 是业务配置真值源，受 Git 管理，由 `config_registry` 加载。
- `apps/api/.env` 是部署 / 本地运行时注入，不纳入 Git；仅提交 `apps/api/.env.example` 作为模板。
- 运行时代码统一通过 `apps/api/app/shared/settings.py` 暴露的 `get_settings()` / `validate_startup_settings()` 读取，禁止继续在模块内部散落 `os.getenv()`。

**当前环境变量约定**：

| 变量 | 必需性 | 默认值 | 说明 |
|---|---|---|---|
| `EASYSTORY_JWT_SECRET` | 必需 | 无 | 用户认证 JWT 签名密钥；应用启动时必须存在 |
| `EASYSTORY_CREDENTIAL_MASTER_KEY` | 条件必需 | 无 | 仅在使用 `Credential Center` 创建、加密或校验模型凭证时需要 |
| `EASYSTORY_DATABASE_URL` | 可选 | `sqlite:///apps/api/.runtime/easystory.db` | 数据库连接串 |
| `EASYSTORY_JWT_EXPIRE_HOURS` | 可选 | `24` | JWT 过期小时数，必须 `> 0` |
| `EASYSTORY_CORS_ALLOWED_ORIGINS` | 可选 | 空列表 | 逗号分隔 origin 白名单 |
| `EASYSTORY_CORS_ALLOWED_ORIGIN_REGEX` | 可选 | `^https?://(localhost|127\.0\.0\.1)(:\d+)?$` | CORS 正则白名单 |
| `EASYSTORY_ALLOW_PRIVATE_MODEL_ENDPOINTS` | 可选 | `false` | 是否允许 `localhost` / 私网 IP 等本地模型 endpoint；默认只允许公网 `https` endpoint |
| `EASYSTORY_ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS` | 可选 | `false` | 是否显式允许公网 `http` 模型 endpoint；仅用于兼容测试或受控代理环境 |
| `EASYSTORY_CONFIG_ADMIN_USERNAMES` | 可选 | 空列表 | 逗号分隔的控制面管理员用户名白名单；仅命中用户可访问 `/api/v1/config/*` 与模板写接口 |

**校验与暴露规则**：

- `EASYSTORY_JWT_SECRET` 由 `validate_startup_settings()` 在 FastAPI 启动阶段强制校验；缺失时直接启动失败，不做 silent fallback。
- `EASYSTORY_CREDENTIAL_MASTER_KEY` 保持按能力懒校验；只有真正触发凭证加密/解密路径时才显式报错。
- `EASYSTORY_CORS_ALLOWED_ORIGINS` 接受逗号分隔字符串；解析失败视为配置错误。
- 自定义模型 `base_url` 默认只允许公网 `https` endpoint；若确需访问本地 / 私网模型网关，必须显式设置 `EASYSTORY_ALLOW_PRIVATE_MODEL_ENDPOINTS=true`。
- 若确需访问公网 `http` 模型网关，必须显式设置 `EASYSTORY_ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS=true`；该能力默认关闭，且只应用于兼容测试或明确受控的代理环境。
- `EASYSTORY_CONFIG_ADMIN_USERNAMES` 为空时，控制面写入口默认全部拒绝；当前包括 `/api/v1/config/*` 与模板创建/修改/删除接口。只有命中白名单的已认证用户才能执行这些写操作。
- 新增运行时环境变量时，必须同时更新 `app/shared/settings.py`、`apps/api/.env.example`、本规范与 `docs/README.md`。

### 8.2 YAML 配置注册表加载

**加载流程**：
```
启动时：
1. 加载 `apps/api/.env` 并构建统一 settings
2. 扫描 /config/ 目录
3. 解析所有 YAML 文件
4. 校验配置格式
5. 注册到内存注册表
6. 启动完成；当前不默认开启文件监听

运行时：
1. Web UI、Config API 或外部工具编辑 YAML
2. 显式调用 `ConfigLoader.reload()` 或重建 `ConfigLoader`
3. 重新执行完整校验
4. 替换内存注册表
```

> 当前 v0.1 实现的是“启动加载 + 显式重载”，还没有内建文件监听和 UI 推送机制；热更新 watcher 属于后续扩展，不应默认假定已经存在。

**校验规则**：
- 必填字段检查
- 类型检查
- ID 唯一性检查
- 引用完整性检查（如 skill 引用的 agent 是否存在）

**错误处理**：
- 配置错误：记录详细错误（日志 + Web UI），拒绝加载该配置（不进入注册表）
- 引用缺失：视为配置错误（引用完整性不满足时禁止加载）
- 格式错误：返回详细错误信息并拒绝加载

---

*文档版本: 1.0.0*  
*创建日期: 2026-03-14*  
*更新日期: 2026-03-23*
