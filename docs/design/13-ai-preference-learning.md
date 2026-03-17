# AI 偏好学习（记忆系统）

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🟡 MVP 建议实现 |
| 关联文档 | [内容编辑](./05-content-editor.md)、[上下文注入](./02-context-injection.md) |

---

## 1. 概述

用户每次编辑 AI 输出时，系统自动学习偏好。下次生成时避开问题，减少重复编辑。借鉴 OpenClaw 的记忆架构。

---

## 2. 两层记忆架构

```
短期记忆（Session Memory）
  ├── 本次编辑会话中的修改模式
  ├── 存储: 内存 + 临时文件
  └── 生命周期: 会话结束后归档

长期记忆（Writing Preference Memory）
  ├── 跨会话的稳定写作偏好
  ├── 存储: 项目级 Markdown 文件 + 数据库
  └── 生命周期: 持久化，用户可编辑
```

---

## 3. 偏好学习流程

```
用户编辑 AI 输出
  ↓ 系统计算 diff
  ↓ AI 分析编辑模式（短期记忆）:
    - 删除: "恐怖如斯" → 不喜欢网文口头禅
    - 替换: "如同千年寒冰" → "眼神冰冷" → 偏好简洁
    - 添加: 增加对话 → 偏好对话驱动
  ↓ 累积阈值（同类编辑 ≥ 3 次）
  ↓ 归纳为长期偏好
  ↓ 注入后续 Prompt
```

---

## 4. 记忆存储格式（Markdown）

```markdown
# 写作偏好记忆 - 赛博长安

## 文风偏好
- 简洁白话优先，避免堆砌成语（置信度: 高，来源: 12次编辑）
- 句子长度控制在30字以内（置信度: 中，来源: 5次编辑）

## 叙事偏好
- 偏好对话推进剧情（置信度: 高，来源: 8次编辑）

## 禁忌词/表达
- "恐怖如斯" → 删除（3次）
- "震惊！" → 删除（4次）

## 角色语音
- 主角林风: 说话简短有力
- 师傅: 文言腔调，喜欢用典故
```

---

## 5. 数据模型

```python
class WritingPreference(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "writing_preferences"
    project_id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]
    category: Mapped[str]        # "style" / "narrative" / "forbidden" / "character_voice"
    content: Mapped[str]
    confidence: Mapped[float]    # 0-1
    source_edits_count: Mapped[int]
    is_pinned: Mapped[bool] = False
    is_active: Mapped[bool] = True

class EditPattern(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "edit_patterns"
    project_id: Mapped[uuid.UUID]
    content_version_id: Mapped[uuid.UUID]
    pattern_type: Mapped[str]    # "deletion" / "replacement" / "addition"
    original_text: Mapped[str]
    edited_text: Mapped[str]
    ai_analysis: Mapped[str | None]
```

---

## 6. 偏好注入 Prompt

```jinja2
{% if writing_preferences %}
【写作偏好（基于历史编辑学习）】
{{ writing_preferences }}
请严格遵循以上偏好。
{% endif %}
```

注入位置：新的上下文注入类型 `type: "writing_preferences"`，自动注入所有 generate 节点。

### 6.1 注入治理

- 不直接把原始 `EditPattern` 注入 Prompt，只注入归纳后的 `WritingPreference`
- 默认只注入满足 `confidence >= 0.7` 且 `source_edits_count >= 3` 的偏好，或用户手动 pin 的偏好
- 注入时按 `is_pinned > confidence > source_edits_count` 排序，默认最多 5 条、300 tokens
- 若存在冲突偏好（如“多描写环境”与“减少环境描写”），不自动都注入，必须由用户确认保留哪条

---

## 7. 用户可查看/编辑偏好

```
项目设置 → 写作偏好 Tab:
  📝 文风:  ✅ 简洁白话 (高置信, 12次)
  🚫 禁忌:  ❌ "恐怖如斯" (3次删除)
  💬 角色:  · 林风: 简短有力
  操作: 删除不准确的 / 手动添加 / 调整置信度 / Pin 到顶部
```

---

*最后更新: 2026-03-17*
