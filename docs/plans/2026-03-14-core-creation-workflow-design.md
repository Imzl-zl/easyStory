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

## 7. 小说分析功能

### 7.1 设计目标

**用户上传小说,通过自然语言提问进行分析**

用户可以上传已有小说,系统分析其文风、剧情、人物等特征,并支持用户用自然语言提问。

### 7.2 核心挑战

**长文本处理问题:**
- 一本小说可能有几十万到上百万字
- LLM 上下文窗口有限(Claude 200K tokens ≈ 30-40 万字)
- 需要在保持分析质量的同时控制 token 消耗

### 7.3 MVP 方案

**采用方案:用户选择章节 + 智能采样**

#### 功能流程

```
1. 用户上传小说(TXT/EPUB 等格式)
   ↓
2. 系统自动按章节切分
   ↓
3. 显示章节列表,用户选择:
   - 选项 A: 选择具体章节范围(如 1-10 章)
   - 选项 B: 智能采样(系统自动选择代表性章节)
   ↓
4. 系统分析选中章节
   - 生成文风分析报告
   - 存储分析结果
   ↓
5. 用户用自然语言提问
   - "分析文风" → 返回文风特征
   - "总结剧情" → 返回剧情摘要
   - "分析人物" → 返回人物分析
```

#### 智能采样规则

```yaml
采样策略:
  触发条件: 章节数 > 30
  采样规则:
    - 开头: 前 5 章(建立基调)
    - 中间: 均匀采样 10 章(发展过程)
    - 结尾: 后 5 章(高潮结局)
    - 总计: 约 20 章

  采样算法:
    - 中间采样: 将剩余章节分成 10 段,每段取中间章节
    - 确保覆盖整个故事发展过程
```

### 7.4 分析维度

**系统生成的分析报告包含:**

| 维度 | 说明 | 示例 |
|-----|------|------|
| 文风特征 | 用词风格、句式特点、节奏感 | "用词华丽,多用四字成语;长短句结合,节奏明快" |
| 叙事视角 | 第一人称/第三人称,全知/限知 | "第三人称限知视角,主要跟随主角视角" |
| 情感基调 | 整体情感倾向 | "轻松幽默,偶有紧张刺激" |
| 剧情结构 | 故事发展脉络 | "开端-发展-高潮-结局,双线叙事" |
| 人物特征 | 主要人物性格和关系 | "主角:坚韧不拔;配角:忠诚可靠" |

### 7.5 存储设计

**数据模型:**

```python
class NovelAnalysis(Base):
    id: int
    project_id: int
    novel_title: str
    total_chapters: int
    analyzed_chapters: list[int]  # 分析的章节编号
    analysis_result: dict  # JSON 格式的分析结果
    created_at: datetime
```

**分析结果格式:**

```json
{
  "writing_style": {
    "vocabulary": "华丽,多用成语",
    "sentence_structure": "长短句结合",
    "rhythm": "节奏明快"
  },
  "narrative_perspective": "第三人称限知",
  "emotional_tone": "轻松幽默",
  "plot_structure": "双线叙事",
  "characters": [
    {"name": "主角", "traits": "坚韧不拔"}
  ]
}
```

### 7.6 用户交互

**上传后的操作流程:**

```
用户上传小说
  ↓
系统显示章节列表(共 50 章)
  ↓
用户选择:
  - [选择章节范围] 1-10 章
  - [智能采样] 系统自动选择 20 章
  ↓
系统分析中...
  ↓
生成分析报告
  ↓
用户提问:
  - "这本书的文风是什么样的?"
  - "主角的性格特点是什么?"
  - "适合什么类型的读者?"
```

### 7.7 技术实现要点

**章节切分:**
- 支持 TXT 格式(按"第X章"等标记切分)
- 支持 EPUB 格式(按 HTML 结构切分)
- 智能识别章节标题

**分析流程:**
```python
async def analyze_novel(chapters: list[str]) -> dict:
    # 1. 对每章生成简短摘要
    summaries = []
    for chapter in chapters:
        summary = await llm.summarize(chapter)
        summaries.append(summary)

    # 2. 基于摘要生成整体分析
    analysis = await llm.analyze(
        prompt=f"基于以下章节摘要,分析整体文风:\n{summaries}"
    )

    return analysis
```

**问答系统:**
```python
async def answer_question(question: str, analysis: dict) -> str:
    # 基于分析结果回答用户问题
    response = await llm.chat(
        context=f"小说分析结果:\n{analysis}",
        question=question
    )
    return response
```

### 7.8 后续扩展

**第二阶段可以加入:**
- ⬜ RAG 检索增强(向量化存储章节)
- ⬜ 更细粒度的分析(段落级、句子级)
- ⬜ 对比分析(与其他小说对比)
- ⬜ 风格迁移(学习某本小说的文风)

### 7.9 分析自动生成 Skill (MVP 功能)

**功能描述:**

基于小说分析结果,自动生成模仿该文风的 Skill,形成"分析-学习-创作"的完整闭环。

**实现流程:**

```
用户上传小说 → 分析文风
  ↓
提取文风特征(用词、句式、节奏)
  ↓
自动生成 Skill 配置文件
  ↓
用户可以直接使用生成的 Skill 创作新小说
```

**生成的 Skill 示例:**

```yaml
skill:
  id: "skill.style.金庸风格"
  name: "金庸武侠风格"
  category: "chapter"
  prompt: |
    你是一位武侠小说作家,模仿金庸的写作风格。

    【文风特征】
    - 用词风格: {{ analysis.vocabulary }}
    - 句式特点: {{ analysis.sentence_structure }}
    - 节奏感: {{ analysis.rhythm }}

    请按照以上风格创作内容:
    {{ user_input }}
```

**技术实现:**

```python
async def generate_skill_from_analysis(
    analysis: dict,
    novel_title: str
) -> SkillConfig:
    """基于分析结果生成 Skill"""
    prompt_template = f"""
你是一位小说作家,模仿《{novel_title}》的写作风格。

【文风特征】
- 用词风格: {analysis['vocabulary']}
- 句式特点: {analysis['sentence_structure']}
- 节奏感: {analysis['rhythm']}

请按照以上风格创作内容:
{{{{ user_input }}}}
"""

    skill = SkillConfig(
        id=f"skill.style.{novel_title}",
        name=f"{novel_title}风格",
        category="chapter",
        prompt=prompt_template
    )

    # 保存到配置目录
    save_skill_config(skill)

    return skill
```

**用户交互:**

```
分析完成后,系统提示:
"已生成《金庸武侠》风格的 Skill,是否保存?"
  ↓
用户确认保存
  ↓
Skill 自动添加到配置库
  ↓
用户在创建节点时可以选择使用该 Skill
```

---

## 8. 快速开始模板 (MVP 功能)

### 8.1 设计目标

**降低新手门槛,提供预设的创作模板**

新手用户可能不知道如何配置工作流,提供预设模板可以让他们快速开始创作。

### 8.2 模板内容

**MVP 提供 2-3 个基础模板:**

1. **玄幻小说模板**
   - 预配置的 Workflow(大纲 → 章节 → 审核)
   - 预设的 Skills(玄幻大纲生成、玄幻章节生成)
   - 预设的 Agents(逻辑审核、文风审核)

2. **都市小说模板**
   - 预配置的 Workflow
   - 预设的 Skills(都市大纲生成、都市章节生成)
   - 预设的 Agents

### 8.3 用户交互

```
创建新项目时,用户选择:
  ├─ 自由对话(高级用户)
  └─ 快速开始(新手友好)
      ├─ 玄幻小说模板
      ├─ 都市小说模板
      └─ 空白项目
```

**选择模板后:**

```
1. 系统加载预配置的 Workflow
2. 引导用户填写基础信息:
   - 小说题材
   - 主角设定
   - 世界观
3. 自动生成初始设定
4. 用户可以直接开始创作
```

### 8.4 模板配置示例

**玄幻小说模板配置:**

```yaml
template:
  id: "template.xuanhuan"
  name: "玄幻小说模板"
  description: "适合创作玄幻、修仙类小说"

  workflow:
    id: "workflow.xuanhuan_manual"
    nodes:
      - id: "outline"
        name: "生成大纲"
        type: "generate"
        skill: "skill.outline.xuanhuan"

      - id: "chapter_1"
        name: "生成第1章"
        type: "generate"
        skill: "skill.chapter.xuanhuan"

  guided_questions:
    - question: "主角是什么身份?"
      variable: "protagonist"
    - question: "故事发生在什么世界?"
      variable: "world_setting"
    - question: "主要冲突是什么?"
      variable: "conflict"
```

---

## 9. 工作流可视化 (MVP 简化版)

### 9.1 设计目标

**让用户直观看到工作流执行进度**

用户需要知道当前执行到哪个节点,每个节点的状态如何。

### 9.2 MVP 范围

**简化版:列表视图(不是图形化)**

```
工作流执行监控:
  ├─ [大纲] ✅ 已完成 (2分钟前)
  ├─ [第1章] 🔄 执行中 (生成内容...)
  ├─ [第2章] ⏸️ 等待中
  └─ [第3章] ⏸️ 等待中
```

**实时信息显示:**
- 节点状态(已完成/执行中/等待中/失败)
- 执行时间
- Token 消耗
- 审核结果(如果有)

### 9.3 技术实现

**使用 WebSocket 实时推送状态:**

```typescript
// 前端订阅工作流状态
const ws = new WebSocket(`ws://localhost:8000/ws/${projectId}`)

ws.onmessage = (event) => {
  const update = JSON.parse(event.data)
  // 更新 UI 显示
  updateNodeStatus(update.nodeId, update.status)
}
```

**后端推送状态更新:**

```python
async def execute_node(node_id: str):
    # 推送状态:开始执行
    await websocket.send_json({
        "nodeId": node_id,
        "status": "running",
        "message": "生成内容..."
    })

    # 执行节点
    result = await workflow_engine.execute_node(node_id)

    # 推送状态:完成
    await websocket.send_json({
        "nodeId": node_id,
        "status": "completed",
        "output": result
    })
```

### 9.4 不做的功能(留到第二阶段)

- ⬜ 拖拽式图形化编排
- ⬜ 复杂的流程图展示
- ⬜ 节点连线和依赖可视化

---

## 10. 内容管理 (MVP 核心功能)

### 10.1 设计目标

**组织和管理创作素材**

用户需要管理大纲、章节、人物设定、世界观等创作素材。

### 10.2 内容组织结构

```
项目内容库:
  ├─ 基础设定
  │   ├─ 题材
  │   ├─ 主角设定
  │   └─ 世界观
  ├─ 大纲
  ├─ 章节内容
  │   ├─ 第1章
  │   ├─ 第2章
  │   └─ ...
  ├─ 人物设定
  │   ├─ 主角
  │   ├─ 配角
  │   └─ 反派
  └─ 世界观设定
```

### 10.3 内容版本管理

**每次修改都创建新版本:**

```
第1章:
  ├─ 版本1 (初稿) - 2024-03-14 10:00
  ├─ 版本2 (精修) - 2024-03-14 11:30
  └─ 版本3 (当前) - 2024-03-14 14:20
```

**版本操作:**
- 查看历史版本
- 回滚到指定版本
- 对比两个版本(简单的文本 diff)

### 10.4 数据模型

**已在 Task 2 中定义:**

```python
class Content(Base):
    id: int
    project_id: int
    content_type: str  # "outline", "chapter", "character", "world_setting"
    title: str

class ContentVersion(Base):
    id: int
    content_id: int
    version: int
    content_text: str
    created_by: str
    is_current: bool
```

### 10.5 不做的功能(留到第二阶段)

- ⬜ 复杂的搜索功能
- ⬜ 跨项目复用素材
- ⬜ 高级的版本对比(可视化 diff)
- ⬜ 标签和分类系统

---

## 11. 后续扩展功能

以下功能不在 MVP 范围内,作为后续扩展:

### 11.1 第二阶段扩展

1. **批量操作功能**
   - 批量生成章节
   - 批量审核
   - 批量导出

2. **错误处理和重试机制**
   - 智能重试(指数退避)
   - 错误分类处理
   - 失败通知

3. **版本对比和回滚**
   - 可视化 diff 对比
   - 一键回滚
   - 版本分支

4. **导出功能增强**
   - 支持 EPUB/PDF 格式
   - 自定义模板和样式
   - 批量导出

5. **成本控制**
   - 成本估算
   - 预算管理
   - 成本报告

### 11.2 第三阶段扩展

6. **智能推荐系统**
   - 推荐合适的 Skill/Workflow
   - 基于使用习惯学习
   - 社区热门配置推荐

7. **A/B 测试功能**
   - 同一章节多版本生成
   - 对比选择最佳版本
   - 学习用户偏好

8. **协作功能**
   - 多人同时编辑
   - 评论和批注
   - 任务分配
   - 权限管理

9. **性能优化**
   - 缓存机制
   - 增量生成(流式输出)
   - 并行优化

10. **安全性增强**
    - 内容审核(敏感词过滤)
    - 数据加密
    - 访问控制

---

## 12. 配置资源管理

### 8.1 Skills/Agents/Hooks 的存储

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

## 13. 技术实现要点

### 13.1 实现难度评估

| 功能模块 | 实现难度 | 说明 |
|---------|---------|------|
| 自由对话式设定 | 中等 | LLM 意图理解 + 多轮对话管理 |
| 节点系统 | 中等 | 配置解析 + 执行引擎 |
| 上下文注入 | 中等偏低 | 配置优先级合并 + 模板引擎 |
| 并行审核 | 中等偏低 | asyncio + Semaphore |
| 双工作模式 | 中等 | 状态管理 + 模式切换 |
| 混合 UI | 中等偏高 | 表单 ↔ YAML 双向同步 |

### 13.2 关键技术选型

| 技术点 | 推荐方案 | 理由 |
|-------|---------|------|
| 工作流引擎 | LangGraph | 原生支持状态管理和节点编排 |
| 模板引擎 | Jinja2 | Python 标准，支持变量注入 |
| 异步并发 | asyncio | Python 原生，适合 I/O 密集型任务 |
| 配置格式 | YAML | 可读性好，支持多行字符串 |
| 前端框架 | Next.js + React | 现代化，生态完善 |

### 13.3 实现优先级

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

## 14. 总结

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
