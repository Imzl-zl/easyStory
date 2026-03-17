# 上下文注入机制

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🔴 MVP 必须 |
| 关联文档 | [核心工作流](./01-core-workflow.md)、[成本控制](./08-cost-and-safety.md) |

---

## 1. 概述

上下文注入机制在生成章节时自动注入相关上下文（大纲、前几章、人物设定等），确保内容连贯性。包含：三层优先级架构、Story Bible 事实库、上下文→Skill 变量映射、裁剪算法、可观测性报告。

---

## 2. 三层优先级架构

**优先级：节点级 > 模式匹配 > 全局规则**

### 层级 1：全局规则（Workflow 级）

```yaml
workflow:
  context_injection:
    enabled: true
    default_inject:
      - type: "outline"
      - type: "chapter_list"
```

### 层级 2：模式匹配规则

```yaml
context_injection:
  rules:
    - node_pattern: "chapter_*"
      inject:
        - type: "previous_chapters"
          count: 2
        - type: "character_profile"
          required: true
```

### 层级 3：节点级覆盖

```yaml
- id: "chapter_10"
  context_injection:
    - type: "previous_chapters"
      count: 5  # 覆盖全局的 2 章
    - type: "world_setting"
      required: true
```

### 支持的注入类型

| 类型 | 映射到 Skill 变量 | 说明 |
|-----|-------------------|------|
| `project_setting` | `{{ project_setting }}` | 项目设定（结构化设定文档，可全文或摘要注入） |
| `outline` | `{{ outline }}` | 大纲 |
| `chapter_list` | `{{ chapter_list }}` | 章节目录 |
| `chapter_task` | `{{ chapter_task }}` | 当前章节任务（来自 ChapterTask：title/brief/关键角色等） |
| `previous_chapters` | `{{ previous_content }}` | 前 N 章，用 `\n\n---\n\n` 分隔 |
| `character_profile` | `{{ character_profile }}` | 人物设定 |
| `world_setting` | `{{ world_setting }}` | 世界观设定 |
| `story_bible` | `{{ story_bible }}` | 事实库，按 fact_type 分组 |
| `chapter_summary` | `{{ chapter_summaries }}` | 各章摘要 |
| `style_reference` | `{{ style_reference }}` | 小说分析结果（选字段注入，用于文风参考） |
| `writing_preferences` | `{{ writing_preferences }}` | 用户编辑学习出的高置信偏好摘要 |
| `foreshadowing_reminder` | `{{ pending_foreshadowings }}` / `{{ overdue_foreshadowings }}` | 伏笔推进和遗忘提醒 |
| `custom` | `{{ custom_<key> }}` | 用户自定义 |

---

## 3. 上下文→Skill 变量映射

上下文注入系统的输出是 **一组变量**，填充进 Skill 的 Jinja2 模板：

```
ContextBuilder.build_context()
  ↓
返回 dict: {
  "outline": "大纲全文...",
  "previous_content": "第48章...\n\n第49章...",
  "character_profile": "萧炎：16岁，斗者三段...",
  "story_bible": "【人物状态】...\n【未解伏笔】...",
  ...
}
  ↓
SkillTemplateRenderer.render(template, variables)
  ↓
最终 Prompt 文本
```

> `variables` 会在渲染前由统一的 VariableResolver 合并默认值/循环变量/映射结果，并在 `StrictUndefined` 下做缺失校验，详见 [跨模块契约](./17-cross-module-contracts.md)。

**关键规则：**
- Skill 模板中**未引用的注入类型不会进入最终 Prompt**（不浪费 token），但会在上下文报告中标记为 `unused` 便于排查
- `required: true` 含义为"适用时必须注入"：不适用（如第 1 章无前文）→ 跳过并在报告中标记 `not_applicable`；适用但缺失 → 编译/运行时报错
- 模板引用了变量但注入系统无数据：required=true → 编译时报错；required=false → 使用默认值

---

## 4. Story Bible 事实库

### 4.1 核心理念

每章生成/确认后，自动抽取结构化事实存入事实库。后续章节注入时，优先使用事实库 + 摘要，而不是堆叠原文。

```
第 3 章确认 → AI 抽取事实（人物/地点/时间线/伏笔） → 存入事实库
第 4 章生成时 → 注入事实库人物状态 + 时间线 + 第 3 章摘要
```

### 4.2 事实类型

| 类型 | 说明 | 示例 |
|-----|------|------|
| `character_state` | 人物当前状态 | "萧炎：16 岁，斗者三段" |
| `location` | 出现过的地点 | "迦南学院：大陆顶级学府" |
| `timeline` | 时间线事件 | "第 3 章：入学，推进 2 个月" |
| `setting_change` | 世界观变更 | "异火排行榜首次被提及" |
| `foreshadowing` | 伏笔记录 | "云岚宗与萧家恩怨暗线" |
| `relationship` | 人物关系变化 | "萧炎与薰儿重逢" |

### 4.3 数据模型

```python
class StoryFact(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "story_facts"
    project_id: Mapped[uuid.UUID]
    chapter_number: Mapped[int]
    source_content_version_id: Mapped[uuid.UUID]  # 绑定到具体版本
    fact_type: Mapped[str]
    subject: Mapped[str]
    content: Mapped[str]
    is_active: Mapped[bool] = True
    superseded_by: Mapped[uuid.UUID | None]
```

### 4.4 注入优化效果

| 方案 | 50 章 token 消耗 | 一致性 |
|------|-----------------|--------|
| 前 N 章原文 | ~50,000 tokens（N=2 时只有 2 章信息） | 差 |
| 事实库 + 摘要 + 前 1 章原文 | ~5,000 tokens（覆盖所有 50 章） | 好 |

---

## 5. 上下文裁剪算法

### 5.1 Section 优先级配置

```python
SECTION_CONFIG = {
    "project_setting":         {"priority": 1, "min_tokens": 0,   "truncation": "none"},
    "chapter_task":            {"priority": 1, "min_tokens": 0,   "truncation": "none"},
    "story_bible":             {"priority": 2, "min_tokens": 500, "truncation": "drop_oldest_facts"},
    "writing_preferences":     {"priority": 3, "min_tokens": 80,  "truncation": "keep_high_confidence_only"},
    "foreshadowing_reminder":  {"priority": 4, "min_tokens": 80,  "truncation": "keep_major_only"},
    "chapter_summaries":       {"priority": 5, "min_tokens": 200, "truncation": "drop_oldest_chapters"},
    "previous_chapters":       {"priority": 6, "min_tokens": 500, "truncation": "tail_truncation"},
    "style_reference":         {"priority": 7, "min_tokens": 0,   "truncation": "selected_fields_only"},
    "outline":                 {"priority": 8, "min_tokens": 200, "truncation": "tail_truncation"},
}
```

### 5.2 裁剪流程

1. 计算所有 section 总 token
2. 不超预算 → 原样返回
3. 超预算 → 从最低优先级（数字最大）开始裁剪：
   - 先尝试 section 内部裁剪
   - 裁剪后低于 min_tokens → 整个 section 丢弃
   - 重新计算，仍超则裁下一个
4. priority=1 的 section（project_setting）**永不裁剪**

### 5.3 裁剪策略可配置

```yaml
context_injection:
  truncation:
    strategy: "priority_based"   # priority_based / proportional / newest_first
    priorities:
      project_setting: 1         # 最高
      chapter_task: 1
      story_bible: 2
      writing_preferences: 3
      foreshadowing_reminder: 4
      previous_chapters: 5
      chapter_summary: 6
      style_reference: 7         # 最低，先裁
```

### 5.4 体验型上下文预算规则

- `writing_preferences` 只注入 `is_active=true` 且 `confidence >= 0.7` 的偏好，或用户手动 pin 的偏好
- `writing_preferences` 默认最多 5 条、总计不超过 300 tokens
- `foreshadowing_reminder` 按“逾期 major → 进行中 major → 其他”排序，最多 5 条、总计不超过 300 tokens
- `style_reference` 只允许注入用户显式选择的字段，默认不超过 500 tokens
- 当预算紧张时，体验型上下文必须先被裁剪，不能挤占 `project_setting`、`chapter_task`、`story_bible` 的空间

---

## 6. 上下文构建可观测性

### 6.1 构建报告

每次节点执行时生成上下文构建报告：

```json
{
  "node_id": "chapter_10",
  "context_report": {
    "total_tokens": 8500,
    "budget_limit": 10000,
    "sections": [
      {"type": "story_bible", "token_count": 1800, "items_count": 25, "items_truncated": 3},
      {"type": "chapter_summary", "token_count": 900, "chapters": [6, 7, 8, 9]},
      {"type": "previous_chapters", "token_count": 4500, "original_tokens": 6200},
      {"type": "project_setting", "token_count": 1300}
    ]
  }
}
```

### 6.2 UI 展示

```
节点执行详情 → 🔍 上下文详情（可展开）
  ├─ 事实库: 25 条, 1800 tokens
  ├─ 章节摘要: 4 章, 900 tokens
  ├─ 前章原文: 第9章, 4500 tokens (裁剪自 6200)
  ├─ 项目设定: 1300 tokens
  └─ 总计: 8500 / 10000 tokens
```

---

## 7. 第 1 章特殊处理

第 1 章生成时，无数据的注入类型跳过并在上下文报告中标记原因：

| 注入类型 | 状态 |
|---------|------|
| outline | 完整注入 ✅ |
| chapter_task | 从 ChapterTask 表读取 ✅ |
| world_setting | 完整注入 ✅ |
| previous_chapters | 无数据，跳过（not_applicable） |
| story_bible | 无数据，跳过（not_applicable） |

Skill 模板用 Jinja2 条件处理：

```jinja2
{% if previous_content %}
【前文回顾】
{{ previous_content }}
{% endif %}

{% if not previous_content and not story_bible %}
【创作提示】
这是故事的第一章，请着重建立世界观、引入主角、设定基调。
{% endif %}
```

---

*最后更新: 2026-03-17*
