# 创作设定

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🔴 MVP 必须 |
| 关联文档 | [核心工作流](./01-core-workflow.md)、[上下文注入](./02-context-injection.md)、[前置创作资产](./19-pre-writing-assets.md) |

> **优先级说明**：本模块整体为 🔴，但"设定修改影响结果分级（自动替换/人工复核/stale）+ 范围批量处理"为 🟡 建议简化。

---

## 1. 概述

创作起点定义了用户如何建立创作方向，包括：自由对话式设定、结构化设定输出、设定→Skill 变量映射、快速开始模板、设定修改影响传播。

> 本文聚焦“如何建立和维护 `ProjectSetting`”。关于 `ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter` 的前置资产链路，见 [前置创作资产](./19-pre-writing-assets.md)。

---

## 2. 自由对话式设定

### 2.1 设计决策

**采用方案：自由文本对话。** 用户通过自然语言对话确定创作方向，而不是填写结构化表单。

**理由：** 更符合 AI 创作的自然交互方式，不限制创作自由度，可以通过多轮对话逐步细化。

### 2.2 交互流程

```
用户: "我想写一个修仙小说，主角是个废柴逆袭的..."
  ↓ AI 理解并提取关键信息
  ↓ AI 追问: "主角的起点是什么？有什么特殊机遇吗？"
  ↓ 用户补充细节
  ↓ 生成结构化设定文档
```

---

## 3. 结构化设定输出

对话结束后，AI 生成一份结构化的设定文档：

```json
{
  "genre": "玄幻修仙",
  "sub_genre": "废柴逆袭",
  "target_readers": "男频成长流读者",
  "tone": "热血燃向，偶有幽默",
  "core_conflict": "主角必须在宗门压制中夺回成长机会",
  "plot_direction": "从底层一步步崛起",
  "protagonist": {
    "name": "萧炎",
    "identity": "没落家族少年",
    "initial_situation": "天赋被夺，处于家族低谷",
    "background": "天赋被夺的没落家族少年",
    "personality": "坚韧不拔，性格倔强",
    "goal": "恢复天赋，为家族报仇"
  },
  "world_setting": {
    "name": "斗气大陆",
    "era_baseline": "宗门林立、强者为尊",
    "world_rules": "资源和血脉决定修炼上限，但存在逆天机缘",
    "power_system": "斗气修炼体系，分为斗者到斗帝",
    "key_locations": ["乌坦城", "迦南学院", "中州"]
  },
  "scale": {
    "target_words": 1000000,
    "target_chapters": 200,
    "pacing": "前期快节奏，中后期稳步升级"
  },
  "special_requirements": "每章结尾要有悬念"
}
```

> `world_setting`、`protagonist` 等结构都是 `ProjectSetting` 的组成部分；世界观设定和角色设定不再单独维护第二套真值源。
>
> `ProjectSetting` 当前按固定 schema 校验，禁止继续使用 `worldview`、`target_length`、`protagonist: "林渊"` 这类语义模糊或结构漂移的写法。

---

## 4. 设定→Skill 变量映射

```yaml
setting_to_skill_mapping:
  direct:
    genre: "genre"
    protagonist.name: "protagonist_name"
    protagonist.background: "protagonist"
    world_setting.name: "world_setting"
    scale.target_words: "target_words"
  composite:
    character_summary: "{{ protagonist.name }}，{{ protagonist.background }}，性格{{ protagonist.personality }}"
  full_context: true  # 完整设定作为 {{ project_setting }} 注入
```

---

## 5. 三种创建方式

```
创建项目时选择:
  ├─ 🗣️ 自由对话（推荐）→ 多轮对话 → 生成结构化设定
  ├─ 📝 手动填写 → 直接填写结构化设定表单
  └─ 📋 快速模板 → 选择模板 → 修改预填内容
```

三种方式最终都产出同一份结构化设定文档。

### 5.1 设定可随时修改

项目设定不是一次性的，用户可以随时：
- 打开设定页面修改字段
- 通过对话追加设定
- 修改后，后续节点自动使用最新设定

### 5.2 启动前完整度检查

**项目可以先创建，但第一次启动 `outline` / `opening_plan` / `chapter` 工作流前必须做设定完整度检查。**

| 字段 | 等级 | 规则 |
|------|------|------|
| 题材 / 类型 | 必填 | 缺失则阻止启动 |
| 主角核心信息 | 必填 | 至少有身份或初始处境 + 核心目标 |
| 核心冲突 | 必填 | 缺失则阻止启动 |
| 世界基线 | 必填 | 奇幻要有世界规则，现实题材要有时代/场景基线 |
| 基调 / 风格 | 建议 | 缺失时允许启动，但给警告 |
| 目标篇幅 / 章节规模 | 建议 | 缺失时允许启动，但无法做更准的预算和规划 |

检查结果分三档：
- `ready`：可以直接启动工作流
- `warning`：允许启动，但展示缺口和“一键让 AI 帮我补全”
- `blocked`：阻止启动，并给出最少追问列表

> 目标不是逼用户先填满所有表单，而是在真正开跑前，避免“设定都没立住就进入批量生成”。

---

## 6. 设定修改影响传播

```
用户修改设定（如主角名 "萧炎" → "萧明"）
  ↓ 系统检测到变更
  ↓ 扫描已有内容和 StoryFact，统计影响范围
  ↓ 弹出确认:
    "有 10 章内容和 12 条事实引用了旧名称"
    选项:
    - [ 仅更新设定 ] — 只改设定，已有内容不动
    - [ 全局替换 ] — 在所有内容和事实中替换
    - [ 逐章确认 ] — 每章单独决定
```

**处理规则：**
- 简单字段替换（名称、地点名）→ 支持全局文本替换
- 复杂字段变更（性格、能力、世界观规则）→ 只更新设定，标记下游为 stale
- 对已有正文执行“全局替换/批量替换”时，必须按内容编辑规则**逐章创建新的 `ContentVersion`**，不得原地覆盖历史版本

### 6.1 影响分级

影响分析结果必须分成三类展示，而不是只报总数：

| 类别 | 含义 | 默认动作 |
|------|------|---------|
| 可自动替换 | 纯文本引用、低风险替换 | 可批量替换 |
| 需人工复核 | 对话语气、上下文依赖、叙事逻辑相关 | 逐章确认 |
| 仅标记 stale | 不能直接替换，但会影响后续生成 | 标记 stale，交给用户决定 |

示例：
```text
可自动替换（5章）
- 第3章："萧炎" -> "萧明"（3处）

需人工复核（3章）
- 第7章：角色对话中包含昵称和语气变化

仅标记 stale（2章）
- 第15章：引用了旧性格描述
```

### 6.2 批量操作

除了“全局替换”和“逐章确认”，还应支持按范围批量处理：

- 只重新生成第 10-20 章
- 只处理被标记为 stale 的章节
- 只自动替换“可自动替换”类，其他保留人工复核

---

## 7. 快速开始模板

### 7.1 设计目标

降低新手门槛，提供预设的创作模板。MVP 提供 2-3 个基础模板。

### 7.2 模板内容

1. **玄幻小说模板** — 预配置 Workflow + Skills + Agents
2. **都市小说模板** — 预配置 Workflow + Skills + Agents

### 7.3 用户交互

选择模板后：加载预配置 → 引导用户填写基础信息 → 自动生成初始设定

### 7.4 模板配置示例

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
        skill: "skill.outline.xuanhuan"
      - id: "opening_plan"
        name: "生成开篇设计"
        skill: "skill.opening_plan.xuanhuan"
        depends_on: ["outline"]
      - id: "chapter_split"
        name: "拆分章节任务"
        skill: "skill.chapter_split"
        depends_on: ["outline", "opening_plan"]
      - id: "chapter_gen"
        name: "生成章节"
        skill: "skill.chapter.xuanhuan"
        depends_on: ["chapter_split"]
  guided_questions:
    - question: "主角是什么身份?"
      variable: "protagonist"
    - question: "故事发生在什么世界?"
      variable: "world_setting"
    - question: "主要冲突是什么?"
      variable: "conflict"
```

---

*最后更新: 2026-03-19*
