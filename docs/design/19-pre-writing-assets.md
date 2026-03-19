# 前置创作资产

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🔴 MVP 必须 |
| 关联文档 | [创作设定](./06-creative-setup.md)、[上下文注入](./02-context-injection.md)、[章节生成](./04-chapter-generation.md)、[内容编辑](./05-content-editor.md) |

> **优先级说明**：本模块整体为 🔴，但“为已导入的中后期项目跳过开篇设计”的兼容路径为 🟡 建议简化。

---

## 1. 概述

长篇小说生成质量不只取决于“有无章节任务”，更取决于章节开始前是否已经把长期约束、阶段约束和当前执行目标分清楚。

本模块定义 easyStory 的**前置创作资产链路**，统一回答以下问题：

- 世界观设定和角色设定放在哪里，谁是单一真值源
- 情节大纲在章节生成前处于什么位置
- “黄金开头”该如何产品化，避免变成含糊口号
- 哪些资产应长期注入，哪些只在前几章高权重生效

**标准创作链路：**

```text
ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter
```

---

## 2. 设计决策

### 2.1 单一真值源

**世界观设定**和**角色设定**都属于 `ProjectSetting` 的结构化子模块，不另起第二套真值源。

原因：

- 避免“项目设定里一份、角色卡里一份、Prompt 里又一份”导致长期漂移
- 便于完整度检查、上下文裁剪和后续变更传播
- 与现有 `project_setting / character_profile / world_setting` 注入模型兼容

### 2.2 “黄金开头”正式命名

需求中不使用“黄金开头”作为正式对象名，统一收敛为：

- 中文：`开篇设计`
- 英文：`OpeningPlan`

原因：

- “黄金开头”偏营销表达，边界模糊
- `OpeningPlan` 更适合作为结构化资产和工作流节点名称
- 它表达的是“开篇策略”，不是直接正文

### 2.3 最优边界

| 资产 | 角色 | 是否独立产物 | 说明 |
|------|------|-------------|------|
| `ProjectSetting` | 创作长期约束 | 否（项目主设定） | 包含题材、世界观、角色、核心冲突、基调、规模 |
| `Outline` | 故事主骨架 | 是 | 定义主线推进、阶段转折、结局承诺 |
| `OpeningPlan` | 前 1-3 章的阶段约束 | 是 | 定义开篇钩子、主角登场、世界露出、首个冲突 |
| `ChapterTask` | 当前章节执行指令 | 是 | 由前置资产拆分出的逐章任务 |
| `Chapter` | 正文产物 | 是 | 最终生成与编辑的正文内容 |

---

## 3. 资产定义

### 3.1 ProjectSetting

`ProjectSetting` 是前置创作资产的根对象，至少应包含：

| 维度 | 必要内容 |
|------|---------|
| 基础定位 | 题材、子类型、目标读者、基调 |
| 世界基线 | 时代背景 / 世界规则 / 力量体系 / 关键地点 |
| 角色设定 | 主角、关键配角、角色关系、动机、成长方向 |
| 核心冲突 | 主线矛盾、阶段目标、主要阻力 |
| 规模预期 | 目标篇幅、章节规模、节奏倾向 |

**约束：**

- `character_profile` 与 `world_setting` 只是 `ProjectSetting` 的**结构化视图**，不是新的主数据
- 修改世界观或角色设定时，仍按 `ProjectSetting` 变更处理和传播

### 3.2 Outline

`Outline` 是章节拆分前必须确认的故事骨架，至少应明确：

- 故事开端、发展、高潮、结局
- 关键转折点和阶段目标
- 主角成长线与主线冲突推进
- 结局承诺和收束方向

**约束：**

- `chapter_split` 不得绕过已确认的 `Outline`
- 若用户修改 `Outline`，应重新评估 `OpeningPlan` 和后续 `ChapterTask`

### 3.3 OpeningPlan

`OpeningPlan` 用于约束前 1-3 章，不直接替代正文。

推荐结构：

```yaml
opening_plan:
  opening_hook: "开篇钩子，读者为什么继续看"
  protagonist_entry: "主角以什么状态登场"
  world_reveal_strategy: "世界观先露出什么，不先露出什么"
  initial_conflict: "第一轮冲突/问题"
  reader_promise: "前几章向读者承诺的核心期待"
  first_arc_goal: "前 1-3 章完成什么推进"
  forbidden_moves:
    - "前 3 章不要一次性讲完全部世界规则"
    - "不要让主角过早无代价开挂"
```

**约束：**

- 从零开始的新项目，在生成第 1 章前，默认必须先确认 `OpeningPlan`
- 对“导入已有中后期项目”或“从中途章节继续”的场景，可显式记录跳过原因后绕过
- `OpeningPlan` 变更后，已生成的前几章应按内容编辑规则决定是否标记 stale 或重生
- `ProjectSetting` / `Outline` / `OpeningPlan` 变更后，现有 `ChapterTask` 应标记为 `stale`，重新执行 `chapter_split` 后才可继续用于章节生成

### 3.4 ChapterTask

`ChapterTask` 是执行层产物，不承担补齐上游战略缺口的职责。

它应来自：

```text
已确认的 ProjectSetting + Outline + OpeningPlan
```

其中：

- `Outline` 决定整本书怎么走
- `OpeningPlan` 决定前几章怎么开
- `ChapterTask` 决定这一章具体写什么

---

## 4. 标准工作流链路

### 4.1 默认链路

```text
建立 ProjectSetting
  -> 完整度检查
  -> 生成并确认 Outline
  -> 生成并确认 OpeningPlan
  -> 拆分 ChapterTask
  -> 逐章生成 Chapter
```

### 4.2 节点依赖

标准工作流中，推荐节点顺序如下：

```yaml
nodes:
  - id: "outline"
    depends_on: []

  - id: "opening_plan"
    depends_on: ["outline"]

  - id: "chapter_split"
    depends_on: ["outline", "opening_plan"]

  - id: "chapter_gen"
    depends_on: ["chapter_split"]
```

### 4.3 审核/确认关口

最优选择不是让 AI 一次吐完所有内容，而是设置两个明确关口：

- `Outline` 关口：确认故事方向是否成立
- `OpeningPlan` 关口：确认第一波读者体验是否成立

只有这两个关口成立，后面的 `ChapterTask` 和章节生成才会稳定。

---

## 5. 上下文注入策略

### 5.1 三层上下文

| 层级 | 资产 | 作用 |
|------|------|------|
| 长期约束 | `project_setting` / `character_profile` / `world_setting` / `outline` / `story_bible` | 保证世界、人物、主线不漂移 |
| 阶段约束 | `opening_plan` / 当前阶段目标 / 近期伏笔 | 保证当前阶段写法和节奏不偏 |
| 当前执行 | `chapter_task` / `previous_chapters` / `chapter_summary` | 保证这一章真正落到位 |

### 5.2 注入规则

- `ProjectSetting` 是长期约束根对象，优先级高于体验型上下文
- `character_profile`、`world_setting` 从 `ProjectSetting` 投影，不单独维护第二份数据
- `OpeningPlan` 默认在第 1-3 章作为高优先级阶段约束注入
- 第 4 章以后，`OpeningPlan` 默认降级为按需引用，不继续长期占用高优先级预算
- `ChapterTask` 是当前章节最高优先级执行指令，不应被 `OpeningPlan` 覆盖

### 5.3 为什么这样分层

如果把所有资产都当成同一层 Prompt 素材，会出现两个问题：

- token 被长期占满，后续章节越来越重
- 模型分不清“整本书不能偏什么”和“这一章必须完成什么”

因此必须区分长期约束、阶段约束和当前执行。

---

## 6. 数据与存储建议

### 6.1 MVP 最优选择

MVP 不额外新增“世界观表”“角色表”“开篇表”三套独立主模型，采用以下策略：

- `ProjectSetting`：继续作为项目主设定对象，内部结构补齐世界观和角色模块
- `Outline`：作为独立内容产物保存
- `OpeningPlan`：作为独立内容产物保存
- `Chapter`：继续走 `Content + ContentVersion`

### 6.2 存储建议

为避免数据库设计被不必要地复杂化，推荐：

- `Outline` 和 `OpeningPlan` 走现有 `Content/ContentVersion` 版本体系
- `Content.content_type` 增加 `outline`、`opening_plan` 等语义类型
- `OpeningPlan` 的修改也必须创建新版本，不得原地覆盖

---

## 7. 验收口径

- 世界观设定和角色设定明确归属 `ProjectSetting`，不存在第二套真值源
- 标准创作链路明确为 `ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter`
- `OpeningPlan` 被定义为结构化前置资产，而非直接正文
- `chapter_split` 默认依赖已确认的 `Outline` 和 `OpeningPlan`
- 章节上下文采用“长期约束 / 阶段约束 / 当前执行”三层注入

---

*最后更新: 2026-03-19*
