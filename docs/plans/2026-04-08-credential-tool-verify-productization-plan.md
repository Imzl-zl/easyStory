# 2026-04-08 Credential Tool Verify Productization Plan

## 1. 背景

当前 shared runtime 已有 provider conformance probe：

- `text_probe`
- `tool_definition_probe`
- `tool_call_probe`
- `tool_continuation_probe`

但产品面 `Credential Center -> 验证` 仍只走基础文本验证，导致“验证成功”与“assistant 真实工具调用可用”之间继续存在语义断层。

## 2. 目标

- 把 probe 分类正式接入凭证验证主链
- 产品显式区分“验证连接”和“验证工具调用”
- 工具调用验证默认验证完整 tool loop

## 3. 约束

- 复用 `app/shared/runtime/llm/interop/provider_tool_conformance_support.py`
- 不新增 fallback 或 silent downgrade
- 不在 credential 模块复制一套 tool probe 协议

## 4. 实施步骤

### Phase 1：后端 probe_kind 贯通

- 扩展 `CredentialVerificationResult` 与 verifier 接口
- `verify_credential_record()`、`CredentialService.verify_credential()`、HTTP router 贯通 `probe_kind`
- `/verify` 保持单入口，但增加显式 `probe_kind`

### Phase 2：通用 verifier 复用 conformance probe

- `text_probe` 继续支持现有连接验证
- `tool_continuation_probe` 作为产品默认“验证工具调用”动作
- 工具验证失败时显式暴露 probe/continuation 失败原因

### Phase 3：Credential Center 产品语义收口

- 动作层改成 `验证连接 / 验证工具调用`
- 成功/失败提示按动作语义区分
- API contract 带回 `probe_kind`

### Phase 4：验证与文档同步

- 补齐后端/前端定向单测
- 更新 `docs/design`、`tools.md`、`memory.md`

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q \
  tests/unit/test_credential_verifier.py \
  tests/unit/test_credential_service.py \
  tests/unit/test_credential_api.py

pnpm --dir apps/web test:unit -- --runInBand \
  src/features/settings/components/credential-center-action-support.test.ts \
  src/features/settings/components/credential-center-feedback.test.ts \
  src/features/settings/components/credential-center-support.test.ts
```
