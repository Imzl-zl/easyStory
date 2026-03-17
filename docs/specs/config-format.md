# easyStory 配置格式规范

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-14 |
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
│   ├── chapter/                   # 章节类
│   │   └── *.yaml
│   ├── character/                 # 人物类
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
| `category` | string | ✅ | 分类：outline/chapter/character/world_setting/review |
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
    protagonist:
      type: "string"
      required: true
      min_length: 2
      max_length: 500
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
| `chapter` | 章节生成 | `skill.chapter.*` |
| `character` | 人物设定 | `skill.character.*` |
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
    
    请给出评分（0-1）和具体建议。
  
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

**类型说明**：

| 类型 | 说明 | ID 前缀示例 |
|-----|------|------------|
| `writer` | 写作类 | `agent.writers.*` |
| `reviewer` | 审核类 | `agent.reviewers.*` |
| `checker` | 检查类 | `agent.checkers.*` |

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
    type: "script"                    # 类型：script/webhook/agent
    config:
      module: "app.hooks.builtin"     # 模块路径（script 类型）
      function: "auto_save_content"   # 函数名
      params:                         # 参数
        save_version: true
  
  priority: 10                        # 可选，优先级，数字越小越先执行
  timeout: 30                         # 可选，超时时间（秒）
  retry:                              # 可选，重试配置
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
| `action.type` | string | ✅ | 动作类型：script/webhook/agent |
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
| `on_error` | 错误发生 | 任何错误时 |

**动作类型说明**：

| 类型 | 说明 | config 字段 |
|-----|------|------------|
| `script` | 执行 Python 函数 | `module`, `function`, `params` |
| `webhook` | 调用 HTTP 接口 | `url`, `method`, `headers`, `body` |
| `agent` | 调用 Agent | `agent_id`, `input_mapping` |

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

  mode: "auto"                        # 必填，工作模式：manual / auto

  settings:                           # 可选，全局设置
    auto_proceed: true                # 审核通过后自动进入下一步
    max_retry: 3                      # 最大重试次数
    save_on_step: true                # 每步自动保存
    timeout: 300                      # 单节点超时（秒）
    default_pass_rule: "no_critical"  # 默认审核聚合规则

  budget:                             # 可选，Token 预算配置
    max_tokens_per_node: 50000        # 单节点最大 token
    max_tokens_per_workflow: 500000   # 单次工作流最大 token
    max_tokens_per_day: 2000000       # 每日最大 token（项目级）
    max_tokens_per_day_per_user: 3000000  # 每日最大 token（用户级，可选）
    warning_threshold: 0.8            # 80% 时告警
    on_exceed: "pause"                # 超预算策略: pause / skip / fail

  safety:                             # 可选，执行安全阀
    max_retry_per_node: 3             # 单节点最大重试
    max_fix_attempts: 3               # 最大精修次数
    max_total_retries: 10             # 整个工作流最大重试总数
    execution_timeout: 3600           # 工作流超时（秒）
    node_timeout: 300                 # 单节点超时（秒）

  retry:                              # 可选，重试策略
    backoff: "exponential"            # 退避策略: fixed / exponential
    base_delay: 5                     # 基础延迟（秒）
    max_delay: 60                     # 最大延迟（秒）

  model_fallback:                     # 可选，模型降级策略
    enabled: false                    # 默认关闭
    chain:                            # 降级链
      - "claude-sonnet-4-20250514"
      - "gpt-4o"
      - "deepseek-v3"
    on_all_fail: "pause"              # 全部失败后的动作：pause / fail / skip
  
  context_injection:                  # 可选，上下文注入规则
    enabled: true
    rules:
      - node_pattern: "chapter_*"     # 匹配章节节点（支持通配符）
        inject:
          - type: "outline"           # 注入类型
            required: true            # 是否必填
          - type: "chapter_list"
            required: true
          - type: "previous_chapters"
            count: 2                  # 前 2 章
            required: true
          - type: "character_profile"
            required: false
  
  nodes:                              # 必填，节点列表
    - id: "outline"                   # 节点 ID
      name: "生成大纲"                 # 节点名称
      type: "generate"                # 节点类型
      skill: "skill.outline.xuanhuan" # 使用的技能

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
      fix_skill: "skill.fix.xuanhuan" # 精修 Skill（可选，无则用内置默认）
      fix_strategy:                   # 精修策略
        mode: "targeted"              # targeted（局部）/ full_rewrite（整篇）
        targeted_threshold: 3         # 问题 ≤ 3 → 局部修改
        rewrite_threshold: 6          # 问题 > 6 → 整篇重写
      on_fix_fail: "pause"            # 精修失败后动作：pause/skip/fail

    - id: "chapter_plan"
      name: "规划章节"
      type: "generate"
      skill: "skill.chapter_plan"
      depends_on: ["outline"]         # 依赖的节点

      auto_review: true
      reviewers:
        - "agent.consistency_checker"

    - id: "chapter_gen"
      name: "生成章节"
      type: "generate"
      skill: "skill.chapter.xuanhuan"
      depends_on: ["chapter_plan"]

      loop:                           # 循环配置
        enabled: true
        count_from: "chapter_plan"    # 从章节规划获取数量
        item_var: "chapter_index"     # 循环变量名
      
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
        - "markdown"
        - "docx"
```

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
| `model_fallback` | object | ❌ | 模型降级策略 |
| `context_injection` | object | ❌ | 上下文注入规则 |
| `nodes` | array | ✅ | 节点列表 |

> 运行时执行 `model_fallback` 前，系统会先按当前 Skill / Agent / Node 的 `model.required_capabilities` 过滤不兼容的备选模型。

**节点类型说明**：

| 类型 | 说明 | 必填字段 |
|-----|------|---------|
| `generate` | 生成内容 | `skill` |
| `review` | 审核内容 | `reviewers` |
| `export` | 导出文件 | `formats` |
| `custom` | 自定义节点（**MVP 延期，v0.2 实现**） | `action` |

**上下文注入类型**：

| 类型 | 说明 | 参数 |
|-----|------|------|
| `project_setting` | 项目设定（结构化设定文档） | - |
| `outline` | 大纲 | - |
| `chapter_list` | 章节目录 | - |
| `chapter_task` | 当前章节任务（来自 ChapterTask） | - |
| `previous_chapters` | 前 N 章 | `count` |
| `character_profile` | 人物设定 | - |
| `world_setting` | 世界观设定 | - |
| `story_bible` | Story Bible 事实库 | `include`, `max_tokens` |
| `chapter_summary` | 章节摘要（代替原文堆叠） | `count`, `max_tokens_per_summary` |
| `style_reference` | 小说分析结果（文风参考） | `analysis_id`, `inject_fields` |
| `custom` | 自定义 | `key`, `source`, `query` |

---

## 7. 模型配置与凭证（约束）

**决策**：任何 API Key/凭证不允许出现在 YAML（包括 `${ENV}` 引用）。凭证统一存于数据库 `model_credentials`（AES-256-GCM 加密），通过 Web UI 管理，详见 `docs/design/10-user-and-credentials.md`。

### 7.1 model 对象（在 Skill/Agent/Workflow/Node 中复用）

```yaml
model:
  provider: "anthropic"             # openai/anthropic/deepseek/...
  name: "claude-sonnet-4-20250514"  # 具体模型名
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

> 当工作流配置了 `model_fallback.chain` 时，运行时会先过滤不满足 `required_capabilities` 的模型，再按降级链顺序尝试。

### 7.2 选择优先级（高 → 低）

```
节点级 model > Skill 级 model > 工作流级 model > 项目级默认 model > 全局默认 model
```

> `provider` 用于选择凭证（项目级 > 用户级 > 系统级），`name` 用于选择具体模型。

---

## 8. 配置加载机制

**加载流程**：
```
启动时：
1. 扫描 /config/ 目录
2. 解析所有 YAML 文件
3. 校验配置格式
4. 注册到内存注册表
5. 启动文件监听（热更新）

运行时：
1. Web UI 编辑配置
2. 写入 YAML 文件
3. 文件监听触发
4. 重新加载配置
5. 通知 Web UI 刷新
```

**校验规则**：
- 必填字段检查
- 类型检查
- ID 唯一性检查
- 引用完整性检查（如 skill 引用的 agent 是否存在）

**错误处理**：
- 配置错误：记录日志，跳过该配置
- 引用缺失：记录警告，延迟加载
- 格式错误：返回详细错误信息

---

*文档版本: 1.0.0*  
*创建日期: 2026-03-14*  
*更新日期: 2026-03-17*
