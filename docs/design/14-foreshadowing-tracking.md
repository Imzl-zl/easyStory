# 伏笔/悬念追踪系统

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🟡 MVP 建议实现 |
| 关联文档 | [上下文注入](./02-context-injection.md)、[内容编辑](./05-content-editor.md) |

---

## 1. 概述

长篇小说最大的问题是"挖坑不填"。系统自动追踪伏笔的埋设和回收，生成新章节时提醒"还有哪些伏笔没解开"。

---

## 2. 伏笔生命周期

```
埋设 (planted)  →  发展 (developed)  →  揭示 (revealed)
                                        ↗
                     遗忘 (forgotten) ─┘  (系统自动检测并提醒)
```

---

## 3. 数据模型

```python
class Foreshadowing(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "foreshadowings"
    project_id: Mapped[uuid.UUID]
    title: Mapped[str]                    # "云岚宗的秘密"
    description: Mapped[str]
    status: Mapped[str]                   # planted / developed / revealed / forgotten / abandoned
    importance: Mapped[str]               # major / minor / hint
    planted_chapter: Mapped[int]
    planted_quote: Mapped[str | None]
    target_reveal_chapter: Mapped[int | None]
    actual_reveal_chapter: Mapped[int | None]
    source: Mapped[str]                   # ai_detected / user_created / outline

class ForeshadowingEvent(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "foreshadowing_events"
    foreshadowing_id: Mapped[uuid.UUID]
    chapter_number: Mapped[int]
    event_type: Mapped[str]               # mention / develop / reveal
    description: Mapped[str]
    quote: Mapped[str | None]
```

---

## 4. 检测与提醒

### 4.1 自动检测（每章确认后）

```
第 N 章确认 → AI 分析:
  - 新伏笔（"主角发现神秘古书"）
  - 已有伏笔发展（"再次提到云岚宗"）
  - 伏笔揭示（"揭开云岚宗真相"）
  → 更新状态
  → 检查遗忘: major 超 20 章无 event / minor 超 10 章
```

### 4.2 生成时注入提醒

```jinja2
{% if pending_foreshadowings %}
【伏笔提醒 - 请在合适时推进或揭示】
{% for f in pending_foreshadowings %}
- {{ f.title }} (第{{ f.planted_chapter }}章埋设)
{% endfor %}
{% endif %}

{% if overdue_foreshadowings %}
【⚠️ 以下伏笔可能被遗忘】
{% for f in overdue_foreshadowings %}
- {{ f.title }} (已{{ current_chapter - f.planted_chapter }}章未提及)
{% endfor %}
{% endif %}
```

### 4.3 注入预算规则

- 该提醒通过上下文类型 `foreshadowing_reminder` 注入
- 默认只注入最重要的 5 条提醒，优先级为：逾期 major > 进行中 major > 其他
- 总预算默认不超过 300 tokens，避免伏笔提醒反客为主

---

## 5. 伏笔面板 UI

```
Studio 侧栏 → 伏笔追踪:
  ⚠️ 可能遗忘 (2)
    · 云岚宗的秘密 (第2章, 已18章未提及)
    · 神秘古书 (第8章, 已12章未提及)
  🔄 进行中 (3)
    · 异火争夺 (第5章, 第15章最新提及)
  ✅ 已揭示 (1)
    · 主角天赋之谜 (第1章→第12章)
```

---

## 6. 与 Story Bible 集成

伏笔系统是 Story Bible 的子集：`fact_type: "foreshadowing"` 的 StoryFact 自动关联到 Foreshadowing 表。

---

*最后更新: 2026-03-17*
