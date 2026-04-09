# 凭证兼容 Profile 贯通实施计划

| 字段 | 内容 |
|---|---|
| 文档类型 | 实施方案 |
| 文档状态 | 进行中 |
| 创建时间 | 2026-04-08 |
| 更新时间 | 2026-04-08 |
| 关联文档 | [模型工具调用兼容层设计](../design/23-provider-tool-interop-compatibility-layer.md)、[模型工具调用兼容层实施计划](./2026-04-08-provider-tool-interop-implementation-plan.md)、[provider conformance probes 实施计划](./2026-04-08-provider-tool-conformance-probes-plan.md) |

---

## 1. 目标

把 `interop_profile` 从“shared runtime 和 probe 已支持”的半成品状态，推进到“凭证可持久化、验证链可消费、assistant runtime 可真实携带、Credential Center 可配置”的完整闭环。

## 2. 当前缺口

截至 `2026-04-08`：

- `LLMConnection` 已支持 `interop_profile`
- `provider_interop_support.py` 与 probe CLI 已支持 `interop_profile`
- `ModelCredential`、Credential DTO、runtime payload 仍未携带 `interop_profile`
- `AsyncHttpCredentialVerifier` 仍未用凭证里的 `interop_profile` 构建 `LLMConnection`
- Credential Center 前端还没有 `interop_profile` 字段和选择入口

这会造成：

1. probe 和真实 assistant runtime 之间存在双真值
2. 凭证连接验证与实际运行使用的兼容能力不一致
3. 兼容层虽已落地，但用户无法在正式产品路径中稳定使用

## 3. 实施原则

- `interop_profile` 继续定义为协议边界配置，不下沉到 assistant 业务层
- 凭证层持久化的是“兼容 override”，不是第二套运行时真值
- 不做 silent fallback；profile 非法或与 `api_dialect` 不匹配时显式失败
- Credential verify、assistant runtime、provider interop probe 必须共享同一条 runtime contract

## 4. 分阶段计划

### Phase 1：凭证模型与运行时 payload 贯通

目标：

- `ModelCredential` 增加 `interop_profile`
- DTO / view / create / update / runtime payload 全部带上该字段
- `llm_tool_provider` 真正把该字段写入 `LLMConnection`

完成标准：

- assistant runtime 通过凭证真实拿到 `interop_profile`
- create/update/view/runtime payload 不再丢字段

### Phase 2：验证链与 schema 迁移对齐

目标：

- verifier 使用同一 `interop_profile`
- Alembic migration 与 SQLite legacy reconcile 补齐新列

完成标准：

- 凭证验证与真实运行时不再出现 profile 双真值
- 新老库都能稳定得到 `interop_profile` 列

### Phase 3：Credential Center 配置入口

目标：

- 前端 API contract、表单 draft、payload builder、兼容设置面板支持 `interop_profile`
- 按 `api_dialect` 约束可选 profile

完成标准：

- 用户可在正式连接配置入口显式设置 `interop_profile`
- 不支持 profile 的方言不会暴露错误配置入口

### Phase 4：回归与文档同步

目标：

- 后端单测、前端单测、Alembic / bootstrap 定向回归通过
- 更新设计/协作文档里的当前实施状态

完成标准：

- `interop_profile` 已形成“存储 -> 验证 -> 运行时 -> UI”完整闭环

## 5. 验证命令

```bash
cd apps/api && ./.venv/bin/pytest -q tests/unit/test_credential_service.py tests/unit/test_credential_service_updates.py tests/unit/test_credential_api.py tests/unit/test_credential_verifier.py tests/unit/test_assistant_service.py tests/unit/test_alembic_baseline.py tests/unit/test_db_bootstrap.py tests/unit/test_llm_tool_provider.py
pnpm --dir apps/web test:unit -- --runInBand src/features/settings/components/credential/credential-center-support.test.ts
```
