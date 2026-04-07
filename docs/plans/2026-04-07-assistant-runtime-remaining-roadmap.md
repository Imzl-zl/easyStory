# Assistant Runtime 剩余风险执行路线图

> 文档状态：历史实施记录
>
> 本文是 [2026-04-07-assistant-runtime-doc-refactor](./2026-04-07-assistant-runtime-doc-refactor.md) 的历史执行路线图，记录本轮 assistant runtime 剩余风险如何一步一步收口。
>
> 正式语义真值仍以 [20-assistant-runtime-chat-mode](../design/20-assistant-runtime-chat-mode.md)、[21-assistant-project-document-tools](../design/21-assistant-project-document-tools.md)、[22-assistant-tool-calling-runtime](../design/22-assistant-tool-calling-runtime.md) 与当前代码为准。

## 1. 目标

本文记录了在不再变动 assistant 目录结构的前提下，如何把当时剩余的 4 类 runtime 风险按最小切口逐步收口：

1. `document_context` 的 `collapse / audit / recovery` 真值
2. 分级 `compaction / collapse / recovery` 的统一合同
3. ordinary chat 的 tool hint 与后续 discovery 过渡边界
4. 用户层 / 项目层规则拆分与 `include`

## 2. 不再重做的部分

下面这些已收口，不再混入本路线图：

- assistant `service/` 十个稳定子域目录标准化
- `tool_catalog_version` 独立化
- `continuation_anchor_snapshot` 归一化
- latest `continuation_request_snapshot`
- latest `continuation_compaction_snapshot`
- `tool_guidance` 与 visible tools 的基础对齐

## 3. 执行原则

- 每一步只收口一个主风险，不并行开两条语义线
- 优先复用现有 snapshot / normalized input / hook payload，不新建并行真值
- 每一步都必须同时补：代码、测试、设计回写
- 任何“为了不报错先兜底”的 fallback 不进入实现
- 若某一步需要新字段，优先补到现有 snapshot，而不是新增第二套顶层记录

## 4. 分步计划

### Step 1. `document_context` collapse 真值

当前状态：

- DONE（2026-04-07：已补齐 `document_context_collapsed + document_context_projection_mode + projected_document_context_snapshot`，让 initial prompt compaction 能显式记录 prompt 最终保留的文稿上下文视图）

目标：

- 让 initial prompt compaction 不只记录“保护了什么”，还显式记录“文稿上下文是否发生 collapse、collapse 到什么程度、当前 prompt 实际保留了哪一层文稿视图”。

建议落点：

- `apps/api/app/modules/assistant/service/dto.py`
- `apps/api/app/modules/assistant/service/context/assistant_context_compaction_support.py`
- `apps/api/app/modules/assistant/service/turn/assistant_turn_runtime_support.py`
- `apps/api/app/modules/assistant/service/turn/assistant_turn_run_store_support.py`
- `apps/api/tests/unit/test_assistant_service.py`
- `apps/api/tests/unit/test_assistant_context_compaction_support.py`

完成标准：

- `compaction_snapshot`
  - 能区分“未 collapse / 部分 collapse / 明确失败”
  - 能说明 prompt 实际保留的文稿上下文层级
- `NormalizedInputItem(item_type=compacted_context).payload`
  - 继续与完整 `compaction_snapshot` 单真值对齐
- 非法 snapshot 读回仍会显式失败

验证：

- `cd apps/api && ./.venv/bin/ruff check app/modules/assistant/service tests/unit/test_assistant_service.py tests/unit/test_assistant_context_compaction_support.py`
- `cd apps/api && ./.venv/bin/pytest -q tests/unit/test_assistant_service.py tests/unit/test_assistant_context_compaction_support.py`

### Step 2. recovery injection 显式化

当前状态：

- DONE（2026-04-07：已补齐 `document_context_injection_snapshot`，prepare 阶段只生成一次 latest recovery injection view，并让 prompt projection / prompt render / run snapshot / hook payload 共用同一份显式真值）

目标：

- 把“压缩后靠哪份 latest recovery view 恢复文稿上下文”从隐式 prompt 行为继续收成显式 runtime 合同。

建议落点：

- `apps/api/app/modules/assistant/service/context/assistant_context_compaction_support.py`
- `apps/api/app/modules/assistant/service/context/assistant_prompt_render_support.py`
- `apps/api/app/modules/assistant/service/turn/assistant_turn_prepare_support.py`
- `apps/api/app/modules/assistant/service/turn/assistant_turn_runtime_support.py`
- `apps/api/tests/unit/test_assistant_service.py`

完成标准：

- prepare 阶段只生成一次 latest recovery injection view
- prompt projection / prompt render / run snapshot / hook payload 看到的是同一份 recovery 真值
- 不再依赖“从 `document_context_snapshot + bindings_snapshot` 现推”的隐式恢复逻辑

验证：

- `cd apps/api && ./.venv/bin/ruff check app/modules/assistant/service tests/unit/test_assistant_service.py`
- `cd apps/api && ./.venv/bin/pytest -q tests/unit/test_assistant_service.py -k "document_context_recovery or compaction"`

### Step 3. 分级 compaction 合同统一

当前状态：

- DONE（2026-04-07：initial prompt compaction 与 continuation compaction 当前都已显式冻结前后投影视图 digest，并把 `soft / hard / fail` 统一收口为共享 helper/终止错误；当前 latest snapshot 语义已成为稳定 v1 合同，多次 compaction 历史链不再作为本轮阻塞项）

目标：

- 把 initial prompt compaction 和 tool-loop continuation compaction 进一步统一到同一套审计口径里。

建议落点：

- `apps/api/app/modules/assistant/service/dto.py`
- `apps/api/app/modules/assistant/service/context/assistant_context_compaction_support.py`
- `apps/api/app/modules/assistant/service/tooling/assistant_tool_loop_budget_support.py`
- `apps/api/tests/unit/test_assistant_service.py`
- `apps/api/tests/unit/test_assistant_tool_runtime.py`

完成标准：

- `soft / hard / fail` 的语义边界一致
- initial prompt 与 continuation 的 compaction 审计字段命名尽量对齐
- 预算超限的终止条件继续显式报错，不引入静默降级

验证：

- `cd apps/api && ./.venv/bin/ruff check app/modules/assistant/service tests/unit/test_assistant_service.py tests/unit/test_assistant_tool_runtime.py`
- `cd apps/api && ./.venv/bin/pytest -q tests/unit/test_assistant_service.py tests/unit/test_assistant_tool_runtime.py`

### Step 4. ordinary chat tool hint 向内部 discovery contract 过渡

当前状态：

- DONE（2026-04-07：prepare 阶段已从“候选 guidance snapshot -> visible tools 过滤”推进到“resolved discovery decision -> guidance snapshot 投影”；`tool_guidance_snapshot` 不再直接从关键词命中结果冻结，且当前 snapshot 已显式带上 `discovery_source`）

目标：

- 在不新增独立 `search_tools` 工具的前提下，把 ordinary chat 的 tool hint 从“启发式 prompt 文本”继续收成“resolved discovery decision 的 prompt 投影”。

建议落点：

- `apps/api/app/modules/assistant/service/context/assistant_prompt_support.py`
- `apps/api/app/modules/assistant/service/turn/assistant_turn_prepare_support.py`
- `apps/api/app/modules/assistant/service/tooling/assistant_tool_catalog_support.py`
- `apps/api/app/modules/assistant/service/tooling/assistant_tool_exposure_policy.py`
- `apps/api/tests/unit/test_assistant_service.py`
- `apps/api/tests/unit/test_assistant_tool_runtime.py`

完成标准：

- `tool_guidance_snapshot` 不再和“候选关键词命中”直接绑定，且可直接审计 `discovery_source`
- guidance 的来源与可见工具集合之间保持一条单真值链
- `20 / 22` 文档中可以明确把它描述为“internal discovery projection”，而不是纯 prompt heuristic

验证：

- `cd apps/api && ./.venv/bin/ruff check app/modules/assistant/service tests/unit/test_assistant_service.py tests/unit/test_assistant_tool_runtime.py`
- `cd apps/api && ./.venv/bin/pytest -q tests/unit/test_assistant_service.py tests/unit/test_assistant_tool_runtime.py`

### Step 5. 规则拆分 / `include`

当前状态：

- DONE（2026-04-07：当前规则仍以主 `AGENTS.md` 作为设置页真值，但 runtime `rule bundle` 已支持 frontmatter `include` 的同作用域递归展开；include 顺序稳定，循环 include / 缺失文件 / 越出作用域根目录都会显式报错，且主文件更新时会保留已有 include frontmatter）

目标：

- 在“用户层 / 项目层”现有作用域模型不变的前提下，支持规则拆分与显式 `include`。

建议落点：

- `apps/api/app/modules/assistant/service/assistant_config_file_store.py`
- `apps/api/app/modules/assistant/service/rules/assistant_rule_service.py`
- `apps/api/app/modules/assistant/service/rules/assistant_rule_support.py`
- `apps/api/tests/unit/test_assistant_service.py`
- `apps/api/tests/unit/test_assistant_rule_api.py`

完成标准：

- 只允许同作用域内显式 `include`
- include 顺序稳定、可审计
- 循环 include / 缺失文件 / 非法 scope 必须显式报错
- runtime `rule bundle` 继续只有一条最终装配真值

验证：

- `cd apps/api && ./.venv/bin/ruff check app/modules/assistant/service tests/unit/test_assistant_service.py tests/unit/test_assistant_rule_api.py`
- `cd apps/api && ./.venv/bin/pytest -q tests/unit/test_assistant_service.py tests/unit/test_assistant_rule_api.py`

### Step 6. 统一审查与主计划收口

当前状态：

- DONE（2026-04-07：`20 / 22 / config-format` 与协作文件已同步 absorb 当前实现；主计划当前已推进到 `9 DONE / 0 IN_PROGRESS / 0 TODO`，统一 assistant 回归已通过 `155 passed`）

目标：

- 在代码、设计、协作文件之间完成最后一次一致性审查，并把主计划状态推进到可退出。

建议落点：

- `docs/design/20-assistant-runtime-chat-mode.md`
- `docs/design/21-assistant-project-document-tools.md`
- `docs/design/22-assistant-tool-calling-runtime.md`
- `docs/plans/2026-04-07-assistant-runtime-doc-refactor.md`
- `tools.md`
- `memory.md`

完成标准：

- `20 / 21 / 22` 已吸收对应主归属主题
- 主计划中的 `IN_PROGRESS / TODO` 明显减少或清零
- 读者只看 `docs/design + 当前代码` 就能得到完整语义

验证：

- `cd apps/api && ./.venv/bin/ruff check app/modules/assistant/service tests/unit/test_assistant_service.py tests/unit/test_assistant_tool_runtime.py tests/unit/test_assistant_context_compaction_support.py tests/unit/test_assistant_rule_api.py tests/unit/test_assistant_api.py`
- `cd apps/api && ./.venv/bin/pytest -q tests/unit/test_assistant_service.py tests/unit/test_assistant_tool_runtime.py tests/unit/test_assistant_context_compaction_support.py tests/unit/test_assistant_rule_api.py tests/unit/test_assistant_api.py`

## 5. 建议执行顺序

本轮已按下面顺序执行并完成：

1. Step 1 `document_context` collapse 真值
2. Step 2 recovery injection 显式化
3. Step 3 分级 compaction 合同统一
4. Step 4 ordinary chat tool hint 向内部 discovery contract 过渡
5. Step 5 规则拆分 / `include`
6. Step 6 统一审查与主计划收口

## 6. 暂不纳入本轮的事项

- 新的 assistant 目录迁移
- 对外暴露独立 `search_tools` 工具
- agent 通用 tool-calling
- 流式工具预执行
- 新的 assistant memory 真值层

## 7. 退出条件

本路线图已满足以下条件，并已标记为历史实施记录：

1. Step 1-6 全部完成
2. 主计划 [2026-04-07-assistant-runtime-doc-refactor](./2026-04-07-assistant-runtime-doc-refactor.md) 不再存在核心 `TODO`
3. `20 / 21 / 22` 已能独立解释 assistant runtime 的当前正式语义
