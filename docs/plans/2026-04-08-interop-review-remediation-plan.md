# 2026-04-08 Interop Review Remediation Plan

## 1. 背景

本轮代码审查发现了 3 个需要尽快修复的问题：

1. `tool_continuation_probe` follow-up prompt 直接暴露期望答案，存在明显假阳性
2. `verified_probe_kind` 当前只在应用层 promote，存在并发覆盖高等级能力真值的风险
3. `tool_definition_probe` 校验过宽，无法稳定证明工具定义兼容

## 2. 目标

- 修正 probe 契约，避免工具续接验证被提示词伪造通过
- 让 `verified_probe_kind` 写回保持真值一致，不会被较低等级并发验证覆盖
- 收紧 `tool_definition_probe` 校验，避免把任意非空文本误判为成功

## 3. 约束

- 不新增 silent fallback
- 不改变 assistant visible-tools 门控口径
- 继续复用 shared runtime conformance probe 主链

## 4. 实施步骤

### Phase 1：修正 probe 契约

- follow-up prompt 不再直接写入期望答案
- `tool_continuation_probe` 基于 tool result 中的真实值校验最终回答
- `tool_definition_probe` 改为严格 success token / 受控通过条件

### Phase 2：收紧 verified_probe_kind 写回

- 让验证成功后的 `verified_probe_kind` 写回具备并发安全 promote 语义
- 保持审计和返回 DTO 读取到最终真值

### Phase 3：验证与文档

- 补齐 probe support、credential service/verifier 的负例与并发语义测试
- 同步计划与协作真值

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q \
  tests/unit/test_provider_tool_conformance_support.py \
  tests/unit/test_credential_verifier.py \
  tests/unit/test_credential_service.py \
  tests/unit/test_assistant_service.py
```

## 6. 实施结果

- `tool_definition_probe` 已改为精确 success token 契约，不再把任意非空文本或额外 tool call 视为成功
- `tool_continuation_probe` 已改为基于 tool result 动态 echoed 值的严格校验，follow-up prompt 不再泄漏期望答案
- `verified_probe_kind` 写回已改为数据库当前值参与的原子 promote，避免并发低等级验证覆盖高等级 capability 真值
- 定向验证结果：`114 passed`
