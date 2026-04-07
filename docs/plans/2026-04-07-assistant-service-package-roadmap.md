# Assistant Service 目录迁移路线图

> 文档状态：已完成
>
> 本文只定义 assistant 模块内部 `service/` 的后续目录迁移顺序、暂停条件和验证口径，不替代正式运行时设计真值。
>
> assistant runtime 的正式设计真值仍以 [20-assistant-runtime-chat-mode](../design/20-assistant-runtime-chat-mode.md)、[22-assistant-tool-calling-runtime](../design/22-assistant-tool-calling-runtime.md)、[21-assistant-project-document-tools](../design/21-assistant-project-document-tools.md) 与当前代码为准。

## 1. 目标

这份 roadmap 只解决一个问题：在 assistant 内部已经形成 `turn / tooling / context` 三个稳定子域之后，剩余文件该按什么顺序继续迁移，才能保证：

- 每次只改一个小切片
- 每次都能独立验证和中断恢复
- 不把跨域壳层提前迁碎
- 不因为“想整理目录”而重新制造双真值、循环导入或语义漂移

## 2. 当前已完成的目录标准化

已完成：

- `service/turn/`
  - turn 生命周期、run store、run snapshot、LLM bridge
- `service/tooling/`
  - descriptor / catalog / policy / executor / tool loop / tool step
- `service/context/`
  - prompt projection、document context 归一化、历史 compaction、输入预算 support
- `service/hooks_runtime/`
  - hook payload / runtime execution / plugin registry provider
- `service/rules/`
  - rule DTO / runtime bundle service / system prompt support
- `service/preferences/`
  - preferences DTO / merge support / runtime preferences service
- `service/skills/`
  - skill DTO / file store / runtime skill service / markdown support
- `service/agents/`
  - agent DTO / file store / runtime agent service / markdown support
- `service/mcp/`
  - MCP DTO / file store / runtime MCP service / YAML support
- `service/hooks/`
  - Hook 配置 DTO / file store / runtime hook service / YAML support

当前 assistant `service/` 根目录已经不再承担这些子域的具体实现，只保留跨域组合壳层与剩余资源管理文件。

## 3. 迁移总原则

后续所有目录迁移必须遵守以下规则：

1. 一次只迁一个子域，不并行迁多个包。
2. 只做纯结构迁移，不把行为改造混进同一轮。
3. 新子包的 `__init__.py` 默认保持轻量；除非确有必要，不做聚合导出，避免重新引入循环导入。
4. 任何一轮迁移都必须能仅依赖：
   - 当前代码
   - 本文
   - 对应 `.codex-tasks/<task>/SPEC.md + TODO.csv + PROGRESS.md`
   完成上下文恢复。
5. 下一轮迁移开始前，上一轮必须满足：
   - 目标文件已全部迁入新子包
   - 根目录无残留旧路径真值
   - 定向 `ruff` / `pytest` 通过
   - `tools.md` / `memory.md` / 相关计划文档已同步

## 4. 现在必须保留在根目录的文件

以下文件当前不建议迁移，应继续留在 `apps/api/app/modules/assistant/service/` 根目录：

- [assistant_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_service.py)
  - assistant 主应用服务与运行时总装配壳层
- [factory.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/factory.py)
  - 跨子域实例装配入口
- [factory_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/factory_support.py)
  - 默认 store / runtime 组装支撑
- [assistant_execution_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_execution_support.py)
  - execution 组合层；当前保留 execution spec 与 hook agent 辅助，prompt render 已回收至 `service/context/assistant_prompt_render_support.py`
- [assistant_run_budget.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_run_budget.py)
  - 运行时预算壳层，同时服务 ordinary chat 与 tooling
- [assistant_llm_runtime_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_llm_runtime_support.py)
  - LLM runtime 组合层，横跨 turn / tooling
- [assistant_runtime_terminal.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_runtime_terminal.py)
  - 统一终止错误合同
- [assistant_runtime_claim_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_runtime_claim_support.py)
  - stale-run / runtime claim 统一支撑
- [assistant_snapshot_store_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_snapshot_store_support.py)
  - snapshot 通用基础设施
- [assistant_config_file_store.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_config_file_store.py)
  - 配置根目录文件系统边界
- [dto.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/dto.py)
  - 运行时主 DTO 合同；当前仍是跨子域共享真值
- [__init__.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/__init__.py)
  - 包级对外导出面

这些文件要等剩余子域基本收口后，再评估是否继续拆分；现在提前迁，只会增加耦合和恢复成本。

## 5. 推荐迁移顺序

### 5.1 第 1 步：`hooks_runtime/`（已完成）

已迁入：

- [assistant_hook_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/hooks_runtime/assistant_hook_support.py)
- [assistant_hook_runtime_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/hooks_runtime/assistant_hook_runtime_support.py)
- [assistant_hook_providers.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/hooks_runtime/assistant_hook_providers.py)

本步已验证：

- hook runtime 三文件已统一收口到 `service/hooks_runtime/`
- `assistant_service / assistant_execution_support / turn/* / 定向测试` 已全部改用新路径
- assistant 定向 `ruff` / `pytest` 已通过

本步明确未迁：

- `assistant_hook_service.py`
- `assistant_hook_dto.py`
- `assistant_hook_file_store.py`
- `assistant_user_hook_support.py`

### 5.2 第 2 步：`rules/`（已完成）

已迁入：

- [assistant_rule_dto.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/rules/assistant_rule_dto.py)
- [assistant_rule_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/rules/assistant_rule_service.py)
- [assistant_rule_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/rules/assistant_rule_support.py)

本步已验证：

- rules 三文件已统一收口到 `service/rules/`
- `assistant_config_file_store / assistant_service / factory / turn/* / hooks_runtime/* / service/__init__.py / 定向测试` 已全部改用新路径
- assistant 定向 `ruff` / `pytest` 已通过

本步明确未迁：

- `assistant_config_file_store.py`
- `assistant_service.py`
- `factory.py`

### 5.3 第 3 步：`preferences/`（已完成）

已迁入：

- [preferences_dto.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/preferences/preferences_dto.py)
- [preferences_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/preferences/preferences_service.py)
- [preferences_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/preferences/preferences_support.py)

本步已验证：

- preferences 三文件已统一收口到 `service/preferences/`
- `assistant_config_file_store / assistant_execution_support / assistant_service / factory / agent|skill|user_* support / turn/* / hooks_runtime/* / service/__init__.py / 定向测试` 已全部改用新路径
- assistant 定向 `ruff` / `pytest` 已通过

本步明确未迁：

- `assistant_config_file_store.py`
- `assistant_service.py`
- `factory.py`

### 5.4 第 4 步：`skills/`（已完成）

已迁入：

- [assistant_skill_dto.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/skills/assistant_skill_dto.py)
- [assistant_skill_file_store.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/skills/assistant_skill_file_store.py)
- [assistant_skill_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/skills/assistant_skill_service.py)
- [assistant_skill_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/skills/assistant_skill_support.py)

本步已验证：

- skills 四文件已统一收口到 `service/skills/`
- `assistant_service / assistant_agent_service / factory / factory_support / turn/* / hooks_runtime/* / service/__init__.py / 技能相关定向测试` 已全部改用新路径
- assistant 定向 `ruff` / `pytest` 已通过

本步明确未迁：

- `assistant_agent_*`
- `assistant_hook_*`
- `assistant_service.py`

### 5.5 第 5 步：`agents/`（已完成）

已迁入：

- [assistant_agent_dto.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/agents/assistant_agent_dto.py)
- [assistant_agent_file_store.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/agents/assistant_agent_file_store.py)
- [assistant_agent_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/agents/assistant_agent_service.py)
- [assistant_agent_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/agents/assistant_agent_support.py)

本步已验证：

- agents 四文件已统一收口到 `service/agents/`
- `assistant_service / assistant_hook_service / factory / factory_support / turn/* / hooks_runtime/* / service/__init__.py / agents 相关定向测试` 已全部改用新路径
- assistant 定向 `ruff` / `pytest` 已通过

本步明确未迁：

- `assistant_hook_*`
- `assistant_mcp_*`
- `assistant_service.py`

### 5.6 第 6 步：`mcp/`（已完成）

已迁入：

- [assistant_mcp_dto.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/mcp/assistant_mcp_dto.py)
- [assistant_mcp_file_store.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/mcp/assistant_mcp_file_store.py)
- [assistant_mcp_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/mcp/assistant_mcp_service.py)
- [assistant_user_mcp_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/mcp/assistant_user_mcp_support.py)

本步已验证：

- MCP 四文件已统一收口到 `service/mcp/`
- `assistant_service / assistant_hook_service / factory / factory_support / service/__init__.py / MCP 相关定向测试` 已全部改用新路径
- assistant 定向 `ruff` / `pytest` 已通过

本步明确未迁：

- `assistant_hook_*`
- `assistant_service.py`
- `factory.py` 根壳职责

### 5.7 第 7 步：`hooks/` 配置 CRUD（已完成）

已迁入：

- [assistant_hook_dto.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/hooks/assistant_hook_dto.py)
- [assistant_hook_file_store.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/hooks/assistant_hook_file_store.py)
- [assistant_hook_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/hooks/assistant_hook_service.py)
- [assistant_user_hook_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/hooks/assistant_user_hook_support.py)

本步已验证：

- Hook 配置 CRUD 四文件已统一收口到 `service/hooks/`
- `assistant_service / factory / factory_support / turn/* / service/__init__.py / hooks 相关定向测试` 已全部改用新路径
- assistant 定向 `ruff` / `pytest` 已通过

本步明确未迁：

- `service/hooks_runtime/*`
- `assistant_service.py`
- `factory.py` 根壳职责

### 5.8 第 8 步：根壳再评估（已完成）

评估结论：

- `assistant_service.py`
- `factory.py`
- `factory_support.py`
- `assistant_run_budget.py`
- `assistant_llm_runtime_support.py`
- `assistant_runtime_terminal.py`
- `assistant_runtime_claim_support.py`
- `assistant_snapshot_store_support.py`
- `assistant_config_file_store.py`
- `dto.py`

当前均继续保留在根目录，视为稳定组合壳或共享合同，不再继续做目录迁移。

本步唯一执行的最小必要改造：

- 新增 [assistant_prompt_render_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/context/assistant_prompt_render_support.py)
- 把 prompt 渲染从 [assistant_execution_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_execution_support.py) 抽回 `service/context/`
- 保持 `assistant_execution_support.py` 只承载 execution spec 解析与 hook agent 辅助

本步已验证：

- root shell 路线已从“继续迁目录”收口为“到此停止继续拆分”
- assistant 定向 `ruff` / `pytest` 已通过

## 6. 每一轮迁移的固定模板

为了避免上下文膨胀和遗忘，后续每轮都按同一模板执行：

1. 建立单独 `.codex-tasks/<task>/SPEC.md + TODO.csv + PROGRESS.md`
2. 只锁定一个子域，不跨两个包
3. 列清楚“迁哪些文件 / 明确不迁哪些文件”
4. 先做纯路径迁移，再修相对导入
5. 新子包 `__init__.py` 默认只保留轻量声明
6. 跑定向验证
7. 回写 `docs/plans`、`tools.md`、`memory.md`
8. 当前子域彻底 `DONE` 后，才开始下一轮

## 7. 固定验证口径

assistant 内部目录迁移每轮至少跑以下定向检查：

```bash
cd apps/api && ./.venv/bin/ruff check \
  app/modules/assistant/service \
  tests/unit/test_assistant_service.py \
  tests/unit/test_assistant_service_continuation.py \
  tests/unit/test_assistant_tool_runtime.py \
  tests/unit/test_assistant_context_compaction_support.py \
  tests/unit/test_assistant_api.py
```

若当前子域有额外专属测试，再补充对应定向 `pytest` 文件；但不在同一轮临时扩大到无关测试面。

## 8. 暂停与恢复规则

后续任何一轮如果中断，恢复时只需要看三处：

1. 当前子域对应的 `.codex-tasks/<task>/TODO.csv`
2. 本文的迁移顺序与根壳保留规则
3. 当前代码目录结构

恢复时禁止：

- 同时跳到下一个子域
- 因为“顺手”开始行为改造
- 把根壳文件一起带着迁走

## 9. 与现有 runtime 文档计划的关系

本文只解决 assistant `service/` 内部目录标准化的实施顺序。

与 runtime 语义相关的迁移主题，例如：

- compaction / recovery / tool hint
- rule include / 拆分
- tool governance 正式合同回写

继续由 [2026-04-07-assistant-runtime-doc-refactor.md](./2026-04-07-assistant-runtime-doc-refactor.md) 负责。
