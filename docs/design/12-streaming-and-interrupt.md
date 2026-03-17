# 流式输出与中途打断

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 优先级 | 🟡 MVP 建议实现 |
| 关联文档 | [核心工作流](./01-core-workflow.md)、[内容编辑](./05-content-editor.md) |

---

## 1. 概述

用户不用等 30 秒才看到结果。实时看到文字出现，发现方向跑偏可以立刻喊停，省时间省 token。

---

## 2. 流式输出协议（SSE）

```
前端                        后端
  │─── SSE 连接 ────────────>│
  │<── event: status ────────│  { "nodeId": "chapter_7", "status": "running" }
  │<── event: chunk ─────────│  "林风站在"
  │<── event: chunk ─────────│  "悬崖边缘，"
  │<── event: chunk ─────────│  ...
  │─── POST /stop ──────────>│  用户点击"停止"
  │<── event: stopped ───────│  生成中断
  │<── event: partial ───────│  { "content": "已生成部分", "tokens": 1200 }
```

### 2.1 动作语义

`POST /stop` 的语义是**停止当前生成**，不是取消整个工作流：

| 动作 | 后端效果 | 后续用户选择 |
|------|---------|-------------|
| 停止当前生成 | 当前 `NodeExecution -> interrupted`；`WorkflowExecution -> paused`；`pause_reason="user_interrupted"` | 保存已有内容 / 从断点续写 / 重新生成整章 / 修改提示后重试 |
| 暂停工作流 | 若当前无流式输出，直接 `running -> paused` | 稍后恢复 |
| 取消工作流 | 尽力中断当前请求后 `-> cancelled` | 无恢复，只能重新发起新执行 |

---

## 3. 前端交互

```
生成中:
  ┌──────────────────────────────────────────────┐
  │  林风站在悬崖边缘...                          │
  │  █ (光标闪烁，文字持续出现)                   │
  ├──────────────────────────────────────────────┤
  │  🔄 生成中... 1,200 tokens    [ ⏹ 停止 ]    │
  └──────────────────────────────────────────────┘

停止后:
  ┌──────────────────────────────────────────────┐
  │  ⚠️ 生成已中断（1,200 / 4,000 tokens）       │
  │  [ 💾 保存已有内容 ]                          │
  │  [ 🔄 从断点续写 ]                           │
  │  [ 🔁 重新生成整章 ]                          │
  │  [ ✏️ 修改提示后重新生成 ]                    │
  └──────────────────────────────────────────────┘
```

---

## 4. 后端实现

```python
async def generate_streaming(node_execution_id, prompt):
    buffer = []
    interrupted = False

    async for chunk in litellm.acompletion_stream(prompt):
        if await check_cancelled(node_execution_id):
            interrupted = True
            break
        buffer.append(chunk.content)
        yield SSEEvent(event="chunk", data=chunk.content)

    partial_content = "".join(buffer)
    if interrupted:
        yield SSEEvent(
            event="stopped",
            data={"content": partial_content, "status": "interrupted"},
        )
        yield SSEEvent(
            event="partial",
            data={"content": partial_content, "tokens": count_tokens(partial_content)},
        )
    else:
        yield SSEEvent(event="completed", data={"content": partial_content})
```

---

## 5. 中断后的内容处理

- 中断后的内容**不自动保存为正式版本**
- 用户选择“保存已有内容”时，创建草稿版本并标记来源：`created_by: "ai_partial"`
- 断点续写时，将已生成内容作为上下文追加指令：
  "以下是已写的部分，请从断点处继续，自然衔接"
- “重新生成整章”会丢弃当前 partial，不复用中断内容
- “修改提示后重新生成”会创建新的 `NodeExecution`，避免与被中断的执行混淆

### 5.1 与工作流状态机的关系

- 流式中断是**节点级事件**，不是新的工作流终态
- 用户点击“停止”后，工作流进入 `paused`，等待明确决策
- 只有用户明确执行“取消工作流”时，工作流才进入 `cancelled`

---

*最后更新: 2026-03-17*
