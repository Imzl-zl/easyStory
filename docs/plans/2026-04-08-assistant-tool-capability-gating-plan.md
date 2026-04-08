# 2026-04-08 Assistant Tool Capability Gating Plan

> 状态：已完成（2026-04-08）

## 1. 背景

当前 shared runtime、credential verifier 与 Credential Center 已支持：

- `text_probe`
- `tool_definition_probe`
- `tool_call_probe`
- `tool_continuation_probe`

当时 probe 结果还没有沉淀为凭证级能力真值，assistant runtime 也没有基于该真值做显式工具门控。

这意味着：

- 产品已经能“验证工具”
- 但 assistant runtime 仍无法基于验证结果决定是否允许完整 tool loop

## 2. 目标

- 将当前最高已证明的 probe capability 持久化到 `ModelCredential`
- 连接参数变更时显式清空 capability 真值
- assistant runtime 在存在 visible tools 时显式要求 `tool_continuation_probe`
- Credential Center 展示当前能力状态

## 3. 设计选择

- 使用 `verified_probe_kind` 作为“当前最高已证明 capability”真值
- 不使用“最后一次验证 probe kind”作为门控依据，避免较低等级 probe 覆盖已证明的更高等级能力
- assistant 不静默隐藏工具；能力不足直接显式报错，引导用户执行“验证工具”

## 4. 实施步骤

### Phase 1：凭证能力真值

- `ModelCredential` 新增 `verified_probe_kind`
- DTO / API / runtime payload / migration / legacy bootstrap 同步
- 更新凭证时统一清空验证状态
- 成功验证时按 probe 等级做 promote，不做降级

### Phase 2：assistant runtime 门控

- `ResolvedAssistantLlmRuntime` 带出 `verified_probe_kind`
- prepare 阶段在 `visible_tool_descriptors` 非空时显式检查 capability
- 当前 assistant tool loop 统一要求 `tool_continuation_probe`

### Phase 3：前端展示与文档

- Credential Center 展示当前工具验证能力状态
- 同步设计文档、`tools.md`、`memory.md`

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q \
  tests/unit/test_provider_tool_conformance_support.py \
  tests/unit/test_credential_service.py \
  tests/unit/test_credential_service_updates.py \
  tests/unit/test_credential_api.py \
  tests/unit/test_credential_verifier.py \
  tests/unit/test_alembic_baseline.py \
  tests/unit/test_db_bootstrap.py \
  tests/unit/test_assistant_service.py

pnpm --dir apps/web test:unit -- --runInBand \
  src/features/settings/components/credential-center-display-support.test.ts \
  src/features/settings/components/credential-center-support.test.ts \
  src/features/settings/components/credential-center-feedback.test.ts

pnpm --dir apps/web lint
```

## 6. 实施结果

- `ModelCredential` 已新增并持久化 `verified_probe_kind`
- verifier 成功后会按 probe rank promote，连接关键字段变更时会显式 reset 验证状态
- assistant prepare 阶段已对 visible tools 显式要求 `tool_continuation_probe`
- Credential Center 已展示当前工具能力摘要
- 定向后端回归 `147 passed`，前端 support suite `62 passed`，`pnpm --dir apps/web lint` 通过
