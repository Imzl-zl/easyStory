# 数据备份与审计

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🟡 MVP 建议简化实现 |
| 关联文档 | [跨模块契约](./17-cross-module-contracts.md)、[用户认证](./10-user-and-credentials.md) |

---

## 1. 概述

用户创作内容是核心资产，必须有备份机制。包括：自动备份、软删除、回收站、执行日志与审计。

---

## 2. 自动备份策略

```yaml
backup:
  enabled: true
  strategy: "incremental"
  schedule: "0 2 * * *"       # 每天凌晨 2 点
  retention:
    daily: 7
    weekly: 4
    monthly: 12
  storage:
    type: "local"             # local / s3 / oss
    path: "/backups"
```

---

## 3. 软删除机制

所有删除操作都是软删除（标记 deleted），不是物理删除：

```python
class Project(Base):
    status: Mapped[ProjectStatus]
    deleted_at: Mapped[datetime | None]

# 查询时自动过滤
query = select(Project).where(Project.deleted_at.is_(None))
```

---

## 4. 回收站功能

```
用户删除项目
  ↓ 标记 deleted_at = now()
  ↓ 移入回收站（保留 30 天）
  ↓ 30 天后自动物理删除
```

物理删除由 `ProjectDeletionService` 统一执行（详见 [跨模块契约](./17-cross-module-contracts.md)）。

---

## 5. 执行日志模型

```python
class ExecutionLog(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "execution_logs"
    workflow_execution_id: Mapped[uuid.UUID]
    node_execution_id: Mapped[uuid.UUID | None]
    level: Mapped[str]           # INFO / WARNING / ERROR
    message: Mapped[str]
    details: Mapped[dict | None] # 错误堆栈等
```

---

## 6. 日志记录点

```python
log("INFO", "Workflow started", {"workflow_id": "xxx"})
log("INFO", "Node started", {"node_id": "outline"})
log("INFO", "LLM called", {"model": "claude-sonnet", "tokens": 1234})
log("WARNING", "Review failed", {"reviewer": "style_checker", "reason": "..."})
log("WARNING", "Retrying node", {"attempt": 2, "reason": "timeout"})
log("ERROR", "Node failed", {"error": "...", "stack": "..."})
```

---

## 7. 日志查询 API

```
GET /api/v1/workflows/{execution_id}/logs?level=ERROR&limit=50
```

---

## 8. Prompt/响应回放（可开关）

```python
class PromptReplay(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "prompt_replays"
    node_execution_id: Mapped[uuid.UUID]
    replay_type: Mapped[str]         # generate / review / fix
    model_name: Mapped[str]
    prompt_text: Mapped[str]
    response_text: Mapped[str]
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
```

配置：
```yaml
prompt_replay:
  enabled: true
  scope: "all"                   # all / errors_only / none
  retention:
    days: 30
    max_storage_mb: 500
```

---

*最后更新: 2026-03-16*
