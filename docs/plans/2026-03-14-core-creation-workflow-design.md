# easyStory 核心创作流程设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 设计文档 |
| 文档状态 | 已确认 |
| 创建时间 | 2026-03-14 |
| 设计目标 | 定义 AI 小说创作平台的核心创作流程和工作模式 |

---

## 1. 设计目标

本设计文档定义 easyStory 的核心创作流程，包括：

1. 创作起点的交互方式
2. 工作流节点系统的架构
3. 上下文注入机制
4. 审核与精修流程
5. 双工作模式（手动/自动）

**核心设计原则：**
- **平台思维**：不预设固定流程，用户自定义节点和流程
- **灵活性优先**：支持从简单到复杂的各种使用场景
- **渐进式复杂度**：新手可以快速上手，高级用户可以深度定制

---

## 2. 创作起点：自由对话式设定

### 2.1 设计决策

**采用方案：自由文本对话**

用户通过自然语言对话确定创作方向，而不是填写结构化表单。

**理由：**
- 更符合 AI 创作的自然交互方式
- 不限制用户的创作自由度
- 可以通过多轮对话逐步细化设定

### 2.2 交互流程

```
用户输入："我想写一个修仙小说，主角是个废柴逆袭的..."
  ↓
AI 理解并提取关键信息：
  - 题材：修仙
  - 主角设定：废柴逆袭
  - ...
  ↓
AI 追问细节："主角的起点是什么？有什么特殊机遇吗？"
  ↓
用户补充细节
  ↓
生成初始设定文档（后续可修改）
```

### 2.3 技术实现要点

- 使用 LLM 进行意图理解和信息提取
- 支持多轮对话，逐步完善设定
- 生成的设定文档可以作为后续节点的上下文注入内容

---

## 3. 工作流节点系统

### 3.1 核心理念

**平台思维：用户自定义流程**

系统不预设固定的创作流程，而是提供节点系统，让用户根据需求自由组合。

### 3.2 节点定义

每个节点代表一个创作步骤，可以配置：

| 配置项 | 说明 | 是否必填 |
|-------|------|---------|
| `id` | 节点唯一标识 | ✅ |
| `name` | 节点名称 | ✅ |
| `type` | 节点类型（generate/review/export/custom） | ✅ |
| `skill` | 关联的 Skill ID | ❌ 可选，没有则用临时 Prompt |
| `hooks` | 关联的 Hooks | ❌ |
| `reviewers` | 审核 Agents 列表 | ❌ |
| `auto_proceed` | 是否自动进入下一节点 | ❌ |
| `auto_review` | 是否自动审核 | ❌ |
| `auto_fix` | 审核失败是否自动精修 | ❌ |

### 3.3 节点配置示例

```yaml
- id: "outline"
  name: "生成大纲"
  type: "generate"
  skill: "skill.outline.xuanhuan"  # 可选

  hooks:
    after:
      - "hook.auto_save"

  auto_review: true
  reviewers:
    - "agent.consistency_checker"

  auto_proceed: false  # 需要人工确认
```

### 3.4 Skill 的作用

**Skill = 可复用的提示词模板**

- **有 Skill 配置**：每次执行节点时，自动使用 Skill 的提示词模板
- **没有 Skill 配置**：用户每次手动输入 Prompt

类比：
- 就像 Claude Code 的 `/commit` skill
- 有 skill → 自动按规则生成
- 没有 skill → 每次手动输入

### 3.5 节点创建方式

**混合界面（兼顾不同用户群体）：**

1. **表单式配置界面**（新手友好）
   - 逐步添加节点
   - 填写表单配置各项参数
   - 实时预览生成的 YAML

2. **YAML 编辑模式**（高级用户）
   - 直接编辑配置文件
   - 支持语法高亮和自动补全
   - 易于版本管理和分享

3. **两种方式实时同步**
   - 表单修改 → 自动更新 YAML
   - YAML 修改 → 自动更新表单

---

## 4. 上下文注入机制

### 4.1 设计目标

**避免内容漂移和不连贯**

在生成章节时，自动注入相关上下文（大纲、前几章、人物设定等），确保内容连贯性。

### 4.2 三层优先级架构

**优先级：节点级 > 模式匹配 > 全局规则**

#### 层级 1：全局规则（Workflow 级别）

```yaml
workflow:
  context_injection:
    enabled: true
    default_inject:
      - type: "outline"      # 所有节点都注入大纲
      - type: "chapter_list" # 所有节点都注入章节目录
```

#### 层级 2：模式匹配规则

```yaml
context_injection:
  rules:
    - node_pattern: "chapter_*"  # 匹配所有章节节点
      inject:
        - type: "previous_chapters"
          count: 2  # 注入前2章
        - type: "character_profile"
          required: true
```

#### 层级 3：节点级覆盖

```yaml
- id: "chapter_10"
  context_injection:
    - type: "previous_chapters"
      count: 5  # 覆盖全局的2章，这个节点注入前5章
    - type: "world_setting"
      required: true
```

### 4.3 支持的注入类型

| 类型 | 说明 | 参数 |
|-----|------|------|
| `outline` | 大纲 | - |
| `chapter_list` | 章节目录 | - |
| `previous_chapters` | 前 N 章内容 | `count` |
| `character_profile` | 人物设定 | - |
| `world_setting` | 世界观设定 | - |
| `custom` | 自定义内容 | `source`, `query` |

### 4.4 注入内容的构建

```
上下文构建器
  ↓
1. 加载大纲
2. 加载章节目录
3. 加载前 N 章（按配置）
4. 加载人物设定
5. 加载世界观设定
  ↓
组装成完整上下文
  ↓
注入到 Skill 的提示词模板中
```

### 4.5 实现复杂度

**难度：中等偏低**

- 配置解析：简单
- 优先级合并：标准的配置覆盖逻辑
- 内容加载：数据库查询
- 模板注入：Jinja2 模板引擎

---

## 5. 审核与精修流程

### 5.1 审核执行方式

**支持串行和并行两种模式**

#### 并行审核配置

```yaml
- id: "chapter_1"
  auto_review: true
  review_mode: "parallel"  # 或 "serial"
  max_concurrent_reviewers: 3  # 最多同时运行3个 Agent

  reviewers:
    - "agent.style_checker"
    - "agent.banned_words_checker"
    - "agent.ai_flavor_checker"
    - "agent.plot_consistency_checker"
```

#### 串行审核配置

```yaml
- id: "outline"
  auto_review: true
  review_mode: "serial"  # 按顺序执行

  reviewers:
    - "agent.consistency_checker"  # 先执行
    - "agent.logic_checker"        # 后执行
```

### 5.2 审核结果处理

```yaml
- id: "chapter_1"
  auto_review: true
  auto_fix: true           # 审核失败自动精修
  max_fix_attempts: 3      # 最多精修3次
  on_fix_fail: "pause"     # 精修失败后：pause/skip/fail
```

**处理流程：**

```
生成内容
  ↓
自动审核（并行/串行）
  ↓
┌─────────────┬─────────────┐
│  全部通过   │   有问题    │
└─────────────┴─────────────┘
      ↓              ↓
  进入下一节点   自动精修
                     ↓
                 重新审核
                     ↓
            ┌────────┴────────┐
            │  通过  │  失败  │
            └────────┴────────┘
                ↓        ↓
          进入下一节点  暂停等待人工
```

### 5.3 技术实现

**并行审核实现：**

```python
# 伪代码示例
async def run_agents_parallel(agents, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_limit(agent):
        async with semaphore:
            return await agent.review(content)
    
    results = await asyncio.gather(*[run_with_limit(a) for a in agents])
    return results
```

**实现要点：**
- 使用 Python `asyncio` 实现异步并发
- 用 `Semaphore` 控制并发数
- 不是开线程，而是异步任务
- 实现难度：中等偏低

---

## 6. 双工作模式

### 6.1 设计理念

**工作流级默认 + 节点级覆盖**

支持两种工作模式，满足不同的使用场景：
- **手动模式**：精细打磨，逐步推进
- **自动模式**：批量生产，一键完成

### 6.2 模式 1：手动模式（Manual Mode）

**适用场景：**
- 精细打磨内容
- 实验性创作
- 学习和探索

**配置示例：**

```yaml
workflow:
  mode: "manual"
  settings:
    auto_proceed: false  # 每个节点都需要人工确认
    auto_review: false   # 不自动审核
```

**用户操作流程：**

```
生成内容
  ↓
暂停，等待用户操作
  ↓
用户可以：
  - 查看内容
  - 与 AI 对话修改（"把这段改得更激烈一些"）
  - 手动编辑内容
  - 手动触发审核（可选）
  - 确认通过
  ↓
进入下一节点
```

### 6.3 模式 2：自动模式（Auto Mode）

**适用场景：**
- 批量生产内容
- 成熟流程复用
- 快速出稿

**配置示例：**

```yaml
workflow:
  mode: "auto"
  settings:
    auto_proceed: true   # 自动进入下一节点
    auto_review: true    # 自动审核
    auto_fix: true       # 审核失败自动精修
    max_retry: 3         # 最大重试次数
```

**执行流程：**

```
生成内容
  ↓
自动审核
  ↓
┌──────────┬──────────┐
│ 审核通过 │ 审核失败 │
└──────────┴──────────┘
     ↓          ↓
自动进入    自动精修
下一节点       ↓
          重新审核（最多3次）
               ↓
        ┌──────┴──────┐
        │ 通过 │ 失败 │
        └──────┴──────┘
           ↓      ↓
      自动进入  暂停
      下一节点  等待人工
```

### 6.4 节点级覆盖

**灵活性：部分节点可以覆盖全局设置**

```yaml
workflow:
  mode: "auto"  # 默认自动模式

nodes:
  - id: "outline"
    name: "生成大纲"
    auto_proceed: false  # 大纲节点强制人工确认

  - id: "chapter_1"
    # 继承 auto 模式，自动执行

  - id: "chapter_10"
    auto_proceed: false  # 第10章需要人工检查
```

### 6.5 运行时切换

**支持执行过程中动态切换模式：**

1. **自动模式 → 手动模式**
   - 自动执行过程中，用户可以随时暂停
   - 切换到手动模式，逐步操作

2. **手动模式 → 自动模式**
   - 手动模式下，用户可以选择"从这里开始自动执行"
   - 系统切换到自动模式，继续执行剩余节点

**实现要点：**
- 在工作流执行状态中记录当前模式
- 提供 UI 按钮支持模式切换
- 切换时保持当前节点状态

---

## 7. 配置资源管理

### 7.1 Skills/Agents/Hooks 的存储

**决策：本地配置文件 + 导入导出**

**存储位置：**

```
/config/
├── skills/
│   ├── outline/
│   │   └── xuanhuan.yaml
│   └── chapter/
│       └── xuanhuan.yaml
├── agents/
│   ├── writers/
│   └── reviewers/
│       └── style-checker.yaml
├── hooks/
│   └── auto-save.yaml
└── workflows/
    └── xuanhuan-auto.yaml
```

**管理方式：**
- 用户通过 Web UI 创建/编辑配置
- 配置自动保存为 YAML 文件
- 支持 Git 版本管理
- 支持导入/导出配置文件（分享给他人）

**不做社区市场的理由：**
- 维护压力大
- 第一阶段聚焦核心功能
- 本地配置 + 导入导出已经满足分享需求

---

## 8. 技术实现要点

### 8.1 实现难度评估

| 功能模块 | 实现难度 | 说明 |
|---------|---------|------|
| 自由对话式设定 | 中等 | LLM 意图理解 + 多轮对话管理 |
| 节点系统 | 中等 | 配置解析 + 执行引擎 |
| 上下文注入 | 中等偏低 | 配置优先级合并 + 模板引擎 |
| 并行审核 | 中等偏低 | asyncio + Semaphore |
| 双工作模式 | 中等 | 状态管理 + 模式切换 |
| 混合 UI | 中等偏高 | 表单 ↔ YAML 双向同步 |

### 8.2 关键技术选型

| 技术点 | 推荐方案 | 理由 |
|-------|---------|------|
| 工作流引擎 | LangGraph | 原生支持状态管理和节点编排 |
| 模板引擎 | Jinja2 | Python 标准，支持变量注入 |
| 异步并发 | asyncio | Python 原生，适合 I/O 密集型任务 |
| 配置格式 | YAML | 可读性好，支持多行字符串 |
| 前端框架 | Next.js + React | 现代化，生态完善 |

### 8.3 实现优先级

**第一阶段（MVP）：**
1. ✅ 节点系统基础架构
2. ✅ 手动模式
3. ✅ 基础上下文注入（全局规则）
4. ✅ 串行审核
5. ✅ 表单式配置 UI

**第二阶段：**
1. ⬜ 自动模式
2. ⬜ 并行审核
3. ⬜ 三层优先级注入
4. ⬜ YAML 编辑模式
5. ⬜ 运行时模式切换

**第三阶段：**
1. ⬜ 可视化拖拽编排
2. ⬜ 高级 Hook 系统
3. ⬜ 性能优化

---

## 9. 总结

本设计文档定义了 easyStory 核心创作流程的五个关键模块：

1. **自由对话式创作起点** - 自然交互，不限制创作自由
2. **灵活的节点系统** - 平台思维，用户自定义流程
3. **三层优先级的上下文注入** - 避免内容漂移
4. **可配置的并行审核机制** - 提升审核效率
5. **双工作模式** - 兼顾精细打磨和批量生产

**核心设计原则：**
- ✅ 平台思维，不预设固定流程
- ✅ 灵活性优先，支持多种使用场景
- ✅ 渐进式复杂度，新手和高级用户都能使用

**下一步：**
- 编写详细的实施计划
- 定义数据模型和 API 接口
- 开始 MVP 开发

---

*文档版本: 1.0.0*  
*创建日期: 2026-03-14*  
*确认状态: 已与用户确认*
