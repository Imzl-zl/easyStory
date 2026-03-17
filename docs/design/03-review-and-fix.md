# 审核与精修流程

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🔴 MVP 必须 |
| 关联文档 | [核心工作流](./01-core-workflow.md)、[跨模块契约](./17-cross-module-contracts.md) |

---

## 1. 概述

审核与精修流程定义了内容质量保障机制，包括：并行/串行审核模式、ReviewResult 统一 Schema、聚合规则、精修策略和 Skill 来源。

---

## 2. 审核执行方式

### 2.1 并行审核

```yaml
- id: "chapter_1"
  auto_review: true
  review_mode: "parallel"
  max_concurrent_reviewers: 3
  reviewers:
    - "agent.style_checker"
    - "agent.banned_words_checker"
    - "agent.ai_flavor_checker"
    - "agent.plot_consistency_checker"
```

### 2.2 串行审核

```yaml
- id: "outline"
  auto_review: true
  review_mode: "serial"
  reviewers:
    - "agent.consistency_checker"  # 先执行
    - "agent.logic_checker"        # 后执行
```

### 2.3 技术实现

使用 Python `asyncio` + `Semaphore` 控制并发数，异步任务而非线程。

---

## 3. ReviewResult 统一 Schema

**所有 Reviewer Agent 的输出必须遵循此 Schema。**

```python
class ReviewIssue(BaseModel):
    category: Literal[
        "plot_inconsistency", "character_inconsistency", "style_deviation",
        "banned_words", "ai_flavor", "logic_error", "quality_low", "other"
    ]
    severity: Literal["critical", "major", "minor", "suggestion"]
    location: ReviewLocation | None
    description: str
    suggested_fix: str | None
    evidence: str | None

class ReviewLocation(BaseModel):
    paragraph_index: int | None
    start_offset: int | None
    end_offset: int | None
    quoted_text: str | None

class ReviewResult(BaseModel):
    reviewer_id: str
    reviewer_name: str
    status: Literal["passed", "failed", "warning"]
    score: float | None          # 0-100
    issues: list[ReviewIssue]
    summary: str
    execution_time_ms: int
    tokens_used: int

class AggregatedReviewResult(BaseModel):
    overall_status: Literal["passed", "failed"]
    results: list[ReviewResult]
    total_issues: int
    critical_count: int
    major_count: int
    minor_count: int
    pass_rule: Literal["all_pass", "majority_pass", "no_critical"]
```

**使用约束：**
- Reviewer 的 system prompt 中必须要求结构化输出
- 精修模块基于 `AggregatedReviewResult.critical_count` 和 `total_issues` 判断策略
- 编辑器的"跳转到问题"基于 `ReviewLocation`

> **决策**：Agent output_schema 不允许自由定义，审核 Agent 必须强制使用 ReviewResult Schema。

---

## 4. 聚合规则配置

### 4.1 配置位置

**在节点级配置，有工作流级默认值：**

```yaml
workflow:
  settings:
    default_pass_rule: "no_critical"

  nodes:
    - id: "chapter_1"
      reviewers: [...]
      review_config:
        pass_rule: "all_pass"          # 节点级覆盖
        re_review_scope: "all"         # 精修后重新审核范围
```

### 4.2 聚合规则

| 规则 | 说明 |
|------|------|
| `all_pass` | 所有 reviewer 都通过才算通过 |
| `majority_pass` | 过半通过即可 |
| `no_critical` | 无 critical 级别问题即通过（**默认**） |

---

## 5. 精修机制

### 5.1 精修输入

```yaml
fix_context:
  original_content: true       # 原始生成的内容
  review_feedback: true        # 审核反馈（问题列表）
  review_severity: true        # 问题严重级别
  original_prompt: true        # 原始 prompt
  fix_instructions: ""         # 用户额外精修指令（可选）
```

### 5.2 精修策略

```yaml
fix_strategy:
  mode: "targeted"             # targeted（局部）/ full_rewrite（整篇）
  selection_rule: "auto"
  auto_rules:
    targeted_threshold: 3      # 问题 ≤ 3 → 局部修改
    rewrite_threshold: 6       # 问题 > 6 → 整篇重写
    # 3-6 个之间 → 自动模式下局部精修，手动模式下询问用户
```

### 5.3 精修 Prompt 来源

```
优先级: 节点专用精修 Skill > 通用精修 Skill > 内置默认 Prompt

节点配置:
- id: "chapter_1"
  fix_skill: "skill.fix.xuanhuan"     # 专用

  # 没有 → workflow.default_fix_skill
  # 也没有 → 内置 "请根据审核反馈修改内容：{feedback}"
```

### 5.4 精修完整流程

```
审核失败
  ↓ 收集审核反馈
  ↓ 判断精修策略
  ├─ 问题 ≤ 3 → 局部精修
  ├─ 问题 > 6 → 整篇重写
  └─ 3-6 个 → 自动模式局部，手动模式询问用户
  ↓ 加载精修 Skill
  ↓ 组装精修 Prompt
  ↓ 调用 LLM 精修
  ↓ 重新审核
  → 通过则下一步 / 失败则重试或暂停
```

---

## 6. 精修后重新审核

### 6.1 审核范围

```yaml
review_config:
  re_review_scope: "all"       # 默认
  # all: 精修后所有 reviewer 重新运行（安全，推荐）
  # failed_only: 只重新运行失败的 reviewer（省 token，有风险）
```

### 6.2 精修引入新问题的处理

- 新问题算在同一轮 fix cycle 内
- `max_fix_attempts: 3` 计数总精修轮次，不区分 issue category
- 达到 `max_fix_attempts` 后，**停止继续精修**；最后一次输出仅作为 `final_candidate`，不得自动视为审核通过
- 示例：第 1 轮修 banned_words → 引入 ai_flavor → 第 2 轮修 ai_flavor → 第 3 轮还有问题 → 达上限，交由 `on_fix_fail` 决定后续动作

---

## 7. 审核结果处理流程

```
生成内容
  ↓ 自动审核（并行/串行）
  ├─ 全部通过 → 进入下一节点
  └─ 有问题 → 自动精修
       ↓ 重新审核
       ├─ 通过 → 下一节点
       └─ 失败且未达上限 → 继续下一轮精修
       └─ 达 max_fix_attempts → 保留 final_candidate → 执行 on_fix_fail
```

配置：
```yaml
- id: "chapter_1"
  auto_review: true
  auto_fix: true
  max_fix_attempts: 3
  on_fix_fail: "pause"     # pause / skip / fail
```

| `on_fix_fail` | 行为 |
|--------------|------|
| `pause` | 工作流进入 `paused`，保留 `final_candidate` 供用户查看、手改或重试 |
| `skip` | 当前章节标记 `skipped`，`final_candidate` 不进入正式主线版本 |
| `fail` | 当前节点和工作流标记失败，等待用户重新发起或修配置 |

---

*最后更新: 2026-03-17*
