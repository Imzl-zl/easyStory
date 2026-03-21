# easyStory Memory

> 仅追加，不覆盖历史。写入前先读当前内容。

## [2026-03-20]
- **Events**：建立项目级协作记忆规则，新增 `tools.md` / `memory.md` 作为代理协作辅助文件。
- **Changes**：更新 `AGENTS.md`，明确协作文件的读取、优先级、写入和冲突处理规则。
- **Insights**：协作记忆只做恢复与沉淀，不得覆盖正式设计真值。

## [2026-03-20 | 项目状态初始化]
- **Events**：当前仓库已从“文档期”进入后端实施期，`apps/api` 已存在可运行骨架和一批已落地模块。
- **Changes**：根 API 路由当前已挂载 `auth`、`credential`、`project`、`content`、`workflow`、`system`；`content` 已补到章节内容与版本管理闭环。
- **Insights**：当前已较完整闭环的后端链路是 `ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter`，适合继续按主链路推进，而不是散做所有剩余模块。
- **Insights**：已完成并验证通过的能力包括：凭证安全闭环、项目设定更新与完整度检查、前置创作资产保存/确认、工作流控制面、章节任务管理、章节内容与版本管理。
- **Insights**：当前明显未完成的方向包括：`analysis` 模块、`review/context/observability` 的完整 API 闭环，以及 `billing/export/template` 的业务层能力。
- **Insights**：最近一次全量后端验证结果为 `cd apps/api && ruff check app tests && pytest -q` 通过，累计 `200 passed`。
- **Next**：新会话进入仓库时，应先核对 `docs/README.md`、`AGENTS.md`、`tools.md`、本文件，再基于当前磁盘代码判断实现状态，不信任过期记忆。

## [2026-03-20 | 项目 skills 基线]
- **Events**：为当前仓库安装项目共享 skills，补齐代码审查、React/Next.js、组合式组件和 PostgreSQL 实践能力。
- **Changes**：新增 `.codex/skills/react-best-practices`、`.codex/skills/composition-patterns`、`.codex/skills/web-design-guidelines`、`.codex/skills/code-review-expert`、`.codex/skills/supabase-postgres-best-practices`。
- **Insights**：当前项目最适合保留的共享 skills 是代码审查、React/Next.js、组件组合模式和 PostgreSQL 最佳实践；浏览器自动化、React Native、移动端设计类 skills 暂不属于当前主线。

## [2026-03-20 | 工作流真实执行闭环完成]
- **Events**：完成后端最小真实执行闭环，打通 `chapter_split -> chapter_gen -> export`，并接入现有 `start_workflow / resume_workflow`。
- **Changes**：新增 `WorkflowRuntimeService`、`LLMToolProvider`、`ExportService`；工作流运行时可持久化 `NodeExecution`、`Artifact`、`PromptReplay`、`ReviewAction`，章节生成后可落 `ContentVersion` 并在章节确认时回写 `ChapterTask`。
- **Changes**：将 `WorkflowRuntimeService` 继续拆为 prompt/review/task/persistence 多个 mixin/helper，主服务文件已压到 300 行以内，避免继续堆积成单文件大杂烩。
- **Changes**：新增 `apps/api/tests/unit/test_workflow_runtime.py`，并更新 `apps/api/tests/unit/test_workflow_api.py` 以覆盖手动模式暂停恢复、章节确认推进和最终导出。
- **Insights**：`workflow_snapshot` 恢复时必须剥离运行时扩展字段，否则 `WorkflowConfig` 会因 `resolved_hooks` 这类 extra key 校验失败。
- **Insights**：`PromptReplay.response_text` 是文本列，结构化 LLM 响应需要先显式 JSON 序列化再落库。
- **Insights**：测试中的导出根目录应放在仓库可写路径下，避免 Windows 沙箱对系统临时目录的写权限问题。
- **Validation**：`cd apps/api && ruff check app tests && pytest -q` 通过，当前全量结果为 `203 passed`。

## [2026-03-20 | 工作流审查问题修复完成]
- **Events**：完成工作流闭环代码审查后的 P1/P2 修复，覆盖事务恢复、章节确认、导出一致性和 provider 路由语义。
- **Changes**：`WorkflowAppService` 改为先持久化 `running` 状态，再单独执行 runtime；runtime 期间发生异常时先 `rollback()`，再重载 workflow 落 `paused + runtime_error snapshot`，避免 `flush` 失败后在失效事务上继续提交。
- **Changes**：`ChapterContentService.approve_chapter()` 现在只会完成当前活跃工作流里、处于等待确认态且 `content_id` 与当前章节一致的 `ChapterTask`，避免审批旧内容或异常绑定时跳过未来章节。
- **Changes**：`ExportService` 现在严格基于当前 `workflow_execution` 的 `ChapterTask` 导出，阻止 `generating/pending/interrupted/failed`，跳过 `skipped`；`exports.file_path` 改存相对路径，并在 DB flush 失败时清理已写文件。
- **Changes**：`LLMToolProvider` 已把 `provider` 透传为 LiteLLM `custom_llm_provider`，消除“凭证选择和真实调用不一致”的双真值。
- **Changes**：新增 `apps/api/tests/unit/test_export_service.py`、`apps/api/tests/unit/test_llm_tool_provider.py`、`apps/api/tests/unit/test_workflow_app_service.py`，并扩展章节确认与导出集成断言。
- **Validation**：`cd apps/api && ruff check app tests`、`cd apps/api && pytest -q` 通过，当前全量结果为 `211 passed`。

## [2026-03-20 | review auto-fix runtime 闭环完成]
- **Events**：完成 `chapter_gen` 的 `auto_review -> auto_fix -> re-review` 真实执行闭环，并补齐失败策略。
- **Changes**：`WorkflowRuntimeReviewMixin` 已接入 `FixExecutor`，支持节点级 `auto_fix / max_fix_attempts / on_fix_fail / fix_skill` 与 workflow 级 `default_fix_skill` 回退。
- **Changes**：新增 `workflow_runtime_execute_mixin.py`，将章节生成后的候选正文落库、任务状态流转、`pause / skip / fail` 收尾逻辑从主服务拆出，保持 runtime 主服务文件精简。
- **Changes**：`ChapterContentService` 新增 `save_auto_fix_draft()`；自动精修通过或保留最终候选时，会写入 `ContentVersion(created_by=auto_fix, change_source=ai_fix)`。
- **Changes**：修正了旧逻辑混乱：审核失败但保留候选正文时，`ChapterTask` 现在进入 `generating` 等待确认态，而不是 `failed` 死状态；`PromptReplay` 也支持记录 `replay_type="fix"`。
- **Changes**：新增 `apps/api/tests/unit/test_workflow_runtime_auto_fix.py`，覆盖 auto-fix 成功、`on_fix_fail=skip` 以及无 auto-fix 时 review_failed 候选正文仍可确认的回归场景。
- **Validation**：`cd apps/api && ruff check app tests && pytest -q` 通过，当前全量结果为 `214 passed`。

## [2026-03-20 | workflow observability API 闭环完成]
- **Events**：完成工作流可观测性后端 API 闭环，让 runtime 已持久化的执行数据可直接查询。
- **Changes**：新增 `observability` 路由与 `WorkflowObservabilityService`，可查询 `workflow executions`、`execution logs`、`node prompt replays`。
- **Changes**：节点执行详情现在会返回 `input_summary`、`context_report`、`artifacts`、`review_actions`，将调试所需数据和完整 prompt 回放分开。
- **Changes**：`WorkflowRuntimePersistenceMixin` 已接入 `ExecutionLog`，记录节点 `started/completed/skipped/failed`；`WorkflowAppService` 与 runtime 收尾逻辑会记录 `started/resumed/paused/cancelled/completed/failed/runtime_error` 等 workflow 级日志。
- **Changes**：新增 `apps/api/tests/unit/test_workflow_observability_service.py`、`apps/api/tests/unit/test_workflow_observability_api.py`，覆盖查询结果结构和 owner 隔离。
- **Validation**：`cd apps/api && ruff check app tests && pytest -q` 通过，当前全量结果为 `218 passed`。

## [2026-03-20 | workflow 状态一致性修复完成]
- **Events**：完成对 runtime 审查中 3 条 P1 状态一致性问题的真实修复，覆盖 auto-fix pause、resume 前置校验、failed 候选确认后的 retry 闭环。
- **Changes**：新增 `workflow_task_runtime_support.py`，统一工作流恢复前的章节任务选择与可继续判断；`WorkflowAppService.resume_workflow()` 现会在状态迁移前阻止“章节待确认/failed 但候选未确认”的恢复请求，保留原始快照。
- **Changes**：`WorkflowRuntimeExecuteMixin` 的 auto-fix pause 语义已统一为 `pause_reason=review_failed`，不再写入非法 `fix_failed`，与设计文档和状态机保持一致。
- **Changes**：`chapter_mutation_support.py` 现在会优先完成活跃工作流的等待确认任务，并在必要时补全 matching failed 任务，保证 `on_fix_fail=fail` 后用户确认最终候选再 retry 时不会重复生成同章。
- **Changes**：新增/扩展 `apps/api/tests/unit/test_workflow_runtime_auto_fix.py`、`apps/api/tests/unit/test_workflow_api.py`、`apps/api/tests/unit/test_chapter_content_service.py`，覆盖上述 3 条回归链路。
- **Validation**：`cd apps/api && ruff check app tests && pytest -q` 通过，当前全量结果为 `222 passed`。

## [2026-03-20 | billing runtime guard 闭环完成]
- **Events**：完成 `billing` 主链路闭环，打通 `workflow runtime -> llm call -> token usage -> budget guard -> workflow pause/fail/skip`。
- **Changes**：新增 `apps/api/app/modules/billing/service/`，实现 `BillingService`、factory 与 DTO；现在每次 LLM 调用都会记录 `TokenUsage`、计算 `estimated_cost`，并汇总 `node / workflow / project_day / user_day` 四级预算状态。
- **Changes**：`WorkflowRuntimeService._call_llm()` 已接入 billing；预算达到 warning threshold 时写执行日志，预算超限时抛出携带原始输出的 `BudgetExceededError`，不做 silent fallback。
- **Changes**：`ReviewExecutor` 现会透传 `BudgetExceededError`；`chapter_split`、`chapter_gen`、`review`、`fix` 已全部接入预算控制，预算超限后会按 `budget.on_exceed` 收敛，并尽量保留已产生的候选内容而不继续追加后续 LLM 调用。
- **Changes**：为保持文件职责清晰，runtime 新拆出 `workflow_runtime_budget_support.py`、`workflow_runtime_chapter_candidate_mixin.py`、`workflow_runtime_export_mixin.py`；测试 fake credential 也改为真实 ORM 凭证，避免 `TokenUsage.credential_id` 漂空。
- **Validation**：`cd apps/api && ruff check app tests`、`cd apps/api && pytest -q` 通过，当前全量结果为 `229 passed`。

## [2026-03-20 | billing/review 语义一致性修复完成]
- **Events**：完成对 billing/runtime/review 审查中 3 条一致性问题的真实修复，覆盖预算告警边界、review 预算中断持久化、`chapter_split` 的 unsupported skip 语义。
- **Changes**：`BillingService` 的 warning threshold 计算改为向上取整，保证 `warning_threshold` 的展示值和实际告警生效边界一致。
- **Changes**：`ReviewExecutor` 现在会在 `BudgetExceededError` 中附带已完成 reviewer 的 partial aggregate；`WorkflowRuntimeReviewMixin` 会先补写这些 `ReviewAction`，再让 runtime 继续按 budget 策略 pause/skip/fail，避免 `TokenUsage` 已落库但 `ReviewAction` 丢失。
- **Changes**：`chapter_split` 遇到 `budget.on_exceed=skip` 时改为显式抛出 `ConfigurationError`，并在写入 `ChapterTask` 之前中断，避免继续使用静默改写语义。
- **Changes**：新增/扩展 `test_billing_service.py`、`test_review_executor.py`、`test_workflow_runtime.py`、`test_workflow_runtime_auto_fix.py`，覆盖上述 3 条回归链路。
- **Validation**：`cd apps/api && ruff check app tests && pytest -q` 通过，当前全量结果为 `233 passed`。

## [2026-03-20 | 仓库换行符真值补齐]
- **Events**：为仓库补充 `.gitattributes`，降低 Windows 与 WSL 之间的整仓换行符漂移风险。
- **Changes**：新增仓库根 `.gitattributes`，默认文本文件统一为 `LF`；`*.bat`、`*.cmd`、`*.ps1` 固定为 `CRLF`；常见二进制文件标记为 `binary`。
- **Insights**：当前仓库此前没有 `.gitattributes`，且 Windows Git 配置为 `core.autocrlf=true`，这是跨环境出现“大量伪变更”的高风险组合。

## [2026-03-21 | 后端审查问题修复完成]
- **Events**：完成一轮后端审查问题修复，覆盖 git 跟踪污染、workflow 请求阻塞、SSE 可观测性和 export 对外 API 缺口。
- **Changes**：已把历史上误跟踪进仓库的 `apps/api/**/__pycache__/*.pyc` 全部从 git 移除；`.gitignore` 原本已正确配置，后续再次生成的 pyc 将只作为本地忽略文件存在。
- **Changes**：`workflow` 路由新增 runtime dispatcher，`start_workflow / resume_workflow` 现在默认通过后台线程触发 runtime；`WorkflowAppService` 额外拆出 `workflow_app_runtime_support.py`，把 runtime 持久化/恢复逻辑移出主服务文件。
- **Changes**：`observability` 新增 `/api/v1/workflows/{workflow_id}/events` SSE 端点；服务层新增按时间增量读取执行日志与终态判断能力。
- **Changes**：`export` 新增对外 API：按 workflow 创建导出、按 project 列表查询、按 export_id 下载文件；并新增 `test_export_api.py`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `237 passed`。

## [2026-03-21 | SSE 复合游标修复完成]
- **Events**：完成第二轮后端稳步推进，修复 workflow events SSE 的增量游标漏日志问题。
- **Changes**：`WorkflowObservabilityService.list_execution_logs_since()` 改为按 `(created_at, id)` 复合游标与稳定排序查询，避免多条 `ExecutionLog` 共享同一时间戳时被 `created_at > last_created_at` 跳过。
- **Changes**：`observability` SSE 路由已同步保存 `last_created_at + last_log_id` 两段游标，并新增服务层/API 层回归测试覆盖相同时间戳场景。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_workflow_observability_service.py tests/unit/test_workflow_observability_api.py` 通过，`7 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `239 passed`。

## [2026-03-21 | billing workflow 查询 API 闭环完成]
- **Events**：继续稳步推进后端，实现 `billing` 的 workflow 维度查询 API 闭环。
- **Changes**：新增 `BillingQueryService`，支持 workflow owner 校验、billing summary 聚合、token usage 列表查询，并保持现有 `BillingService` 只负责写入与预算守卫。
- **Changes**：新增 `billing/entry/http/router.py`，开放 `GET /api/v1/workflows/{workflow_id}/billing/summary` 与 `GET /api/v1/workflows/{workflow_id}/billing/token-usages`；根 API 路由已挂载 billing router。
- **Changes**：新增 `test_billing_query_service.py` 与 `test_billing_api.py`，覆盖 summary 聚合、usage_type 过滤和 owner 隔离。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_billing_query_service.py tests/unit/test_billing_api.py` 通过，`4 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `243 passed`。

## [2026-03-21 | context preview API 闭环完成]
- **Events**：继续稳步推进后端，实现 `context` 模块的 workflow 节点上下文预览 API。
- **Changes**：新增 `ContextPreviewService`、`context/service/dto.py`、`context/entry/http/router.py`，开放 `POST /api/v1/workflows/{workflow_id}/context-preview`，可基于 workflow/skill 快照预览指定 generate 节点的真实上下文变量和 `context_report`。
- **Changes**：将 `VARIABLE_TO_INJECT_TYPE` 从 `workflow` 内部 support 文件归位到 `context/engine/contracts.py`，让 runtime prompt 构建与 preview service 共用同一份映射真值，减少后续维护分叉。
- **Changes**：`ContextBuilderError` 体系已接入 `BusinessRuleError` 口径，preview 缺少章节号或上下文缺失时可直接返回业务错误而不是裸 500。
- **Changes**：新增 `test_context_preview_service.py` 与 `test_context_api.py`，覆盖真实变量预览、chapter 依赖校验和 owner 隔离。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_context_preview_service.py tests/unit/test_context_api.py` 通过，`6 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `249 passed`。

## [2026-03-21 | review query API 闭环完成]
- **Events**：继续稳步推进后端，实现 `review` 模块的最小读取 API 闭环。
- **Changes**：新增 `ReviewQueryService`、`review/service/dto.py`、`review/entry/http/router.py`，开放 `GET /api/v1/workflows/{workflow_id}/reviews/summary` 与 `GET /api/v1/workflows/{workflow_id}/reviews/actions`。
- **Changes**：review 汇总接口返回 workflow 级审核状态计数、问题严重级别计数和 `review_type` 分组统计；action 列表接口返回节点上下文信息，并支持按 `node_execution_id / review_type / status` 过滤。
- **Changes**：`review` 查询层显式兼容历史 `ReviewAction.issues` 已存在的两种 JSON 形态：`[]` 与 `{\"items\": [...]}`；非法负载继续直接暴露错误，不做 silent fallback。
- **Insights**：`review_actions` 的主查询职责现在回到 `review` 模块；`observability` 继续只负责执行过程排障和 node execution 详情展示，避免模块边界继续混乱。
- **Changes**：新增 `test_review_query_service.py` 与 `test_review_api.py`，覆盖汇总统计、action 过滤和 owner 隔离。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_review_query_service.py tests/unit/test_review_api.py` 通过，`4 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `253 passed`。

## [2026-03-21 | review query API 审查修复完成]
- **Events**：根据审查结论，修复 `review` 查询 API 的统计口径、子资源归属校验和异常负载显式暴露问题。
- **Changes**：`reviewed_node_count` 已改为按逻辑 `node_id` 去重，不再把同一节点的多次 `sequence` 执行重复计为多个 reviewed node。
- **Changes**：`GET /api/v1/workflows/{workflow_id}/reviews/actions` 在传入 `node_execution_id` 时，现会先校验该记录是否属于目标 workflow 且 owner 正确；错误参数会返回 `404 not_found`，不再静默返回空列表。
- **Changes**：`ReviewQueryService._parse_issues()` 现会把异常 `issues` 负载抛成带 `review action id` 的 `ConfigurationError`，避免裸 `ValueError` 变成无上下文 500。
- **Changes**：扩展 `test_review_query_service.py` 与 `test_review_api.py`，新增多 `sequence` 统计、跨 workflow `node_execution_id` 校验和异常 issues 负载回归用例。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_review_query_service.py tests/unit/test_review_api.py` 通过，`8 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `257 passed`。

## [2026-03-21 | analysis API 最小闭环完成]
- **Events**：补齐 `analysis` 模块最小后端闭环，支持 project 维度分析结果创建、列表查询和详情查询。
- **Changes**：新增 `analysis/models/analysis.py`、`analysis/service/`、`analysis/entry/http/router.py`，并将 `Analysis` 注册到 `model_registry`、将 `analysis` 路由挂到根 API。
- **Changes**：`project.models.Project` 新增 `analyses` relationship；`analysis` 当前沿用仓库既有模块模式，采用 `models/service/entry` 分层，DTO 放在 `service/dto.py`，未补空壳 `engine/infrastructure`。
- **Changes**：新增 `test_analysis_service.py` 与 `test_analysis_api.py`，覆盖 owner 隔离、foreign content 校验、创建/列表/详情闭环；同时将 service 单测构造方式收敛为 `create_analysis_service()`，移除动态 `__import__` 写法。
- **Insights**：当前仓库多数业务模块都把应用层 DTO 放在模块内 `service/dto.py`，`analysis` 继续遵循这一约定，比单独再造一套 `schemas` 目录更一致，维护成本更低。
- **Insights**：`__pycache__/*.pyc` 目前已由根 `.gitignore` 忽略；测试运行后会在本地重新生成缓存文件，但不会再进入 git 变更。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_analysis_service.py tests/unit/test_analysis_api.py` 通过，`6 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `263 passed`。

## [2026-03-21 | project 管理 API 闭环完成]
- **Events**：继续稳步推进后端，补齐 `project` 聚合的最小管理闭环，支持创建、列表、详情、基础更新、软删除和恢复。
- **Changes**：新增 `ProjectManagementService`、扩展 `project/service/dto.py` 与 `project/service/factory.py`，并在 `project` 路由上开放 `POST/GET/PUT/DELETE /api/v1/projects` 与 `POST /api/v1/projects/{project_id}/restore`。
- **Changes**：`ProjectService.require_project()` 现在默认过滤 `deleted_at is not null`，仅恢复场景通过 `include_deleted=True` 显式访问回收站项目；这会同步让复用该校验的 `content / analysis / workflow` 等模块默认隐藏已删除项目。
- **Changes**：`observability.audit_log_service` 新增 `AUDIT_ENTITY_PROJECT`；项目删除和恢复都会写入 `audit_logs`，事件类型分别为 `project_delete` 和 `project_restore`。
- **Insights**：项目基础元数据更新与 `project_setting` 仍保持分离边界更稳妥；`PUT /projects/{id}` 只处理 `name / template_id / allow_system_credential_pool`，长期设定继续走专用 `setting` 路径，避免未来维护时把聚合元数据和创作真值混在一起。
- **Insights**：软删除一旦进入系统，`require_project()` 的默认过滤就必须尽早收紧，否则回收站项目仍会被后续内容、分析、工作流接口继续访问，形成“删除只是 UI 假象”的边界漏洞。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_project_management_service.py tests/unit/test_project_api.py` 通过，`5 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `268 passed`。

## [2026-03-21 | UI 文档 MVP 对齐完成]
- **Events**：完成 `docs/ui/ui-design.md` 与 `docs/ui/ui-interaction-supplement.md` 的收口重写，改为当前前后端联调阶段可执行的 UI 真值文档。
- **Changes**：`ui-design.md` 已固定 `Auth + Lobby / Studio / Engine / Lab` 的工作台 IA，明确子视图层级，并把 `Lab` 收口为分析结果工作台、`Engine` 收口为执行控制台。
- **Changes**：`ui-interaction-supplement.md` 已新增后端能力矩阵、状态映射、响应式、无障碍、边界态规则，并明确 `Auth` 无忘记密码、`Export` 仅 `txt/markdown`、`Recycle Bin` 仅恢复、`Workflow` 模式只读展示。
- **Insights**：本轮无需为迁就 UI 草案而扩散后端改造；更稳妥的方案是把未来态能力显式标注为 `MVP UI 占位` 或 `Future`，避免 UI 文档继续制造伪完成态。
- **Insights**：`chapter_task.status=\"generating\"` 在前端不能直接等同于“生成中”；需要结合 `content_id` 区分“运行中”和“待确认”，否则会把当前后端真实语义渲染错。

## [2026-03-21 | UI 文档审查修复完成]
- **Events**：根据代码审查结论，修复了 UI 文档里关于 `credential` 范围和 `Review & Diff` 挂载边界的剩余偏差。
- **Changes**：`ui-design.md` 现在把 `Credential Center` 明确为 `MVP 已支持`，并限定 `Studio` 仅保留跳转到当前 workflow 审核面板的联动语义。
- **Changes**：`ui-interaction-supplement.md` 已补充 `Credential` 能力矩阵，明确 `Review & Diff` 归属 `Engine` 的 workflow 子视图，不再写成 `Studio` 可直接承载审核数据面板。
- **Changes**：`docs/README.md` 已把两份 UI 文档的索引描述更新为当前的 MVP 对齐定位。
- **Insights**：`credential` 已有真实后端 CRUD/verify/enable/disable 能力，不能继续被文档误降级为占位；否则前端会把关键可用模块排除出 MVP。

## [2026-03-21 | UI 文档 Web 体验增强完成]
- **Events**：将 Gemini 建议中适合当前 Web MVP 的部分补充进 UI 文档，重点增强视觉与交互实现规则，而不扩展产品边界。
- **Changes**：`ui-design.md` 已明确“大屏 Web 工作台”语义，补充静态宣纸噪点、湿墨/入纸状态反馈、折扇式侧板和 `Ink Pool` 动态响应规则。
- **Changes**：`ui-interaction-supplement.md` 已补充对应实施约束，明确 `Version Panel` 只允许轻量折扇式开合、`running/completed` 用水墨反馈替代呼吸灯、`Ink Pool` 只跟 token/账单更新联动。
- **Insights**：`stale` 目前只能保持单一视觉语言，不能被文档升级成轻重分级；当前后端和状态真值并没有这一层语义。
- **Insights**：字体锐化不是当前 Web 写作体验的主抓手，真正优先级更高的是首行缩进、阅读行宽、行间距和正文稳定性。

## [2026-03-21 | Web 前端基座与首批工作台页面完成]
- **Events**：基于已收口的 UI 文档，正式创建 `apps/web` 并落地首批 Web 工作台实现。
- **Changes**：新增根 `package.json`、`pnpm-workspace.yaml`、`pnpm-lock.yaml`，创建 `apps/web` 的 `Next.js 16 + React 19 + TypeScript + Tailwind 4` 工程骨架，并补齐 `Auth / Lobby / Studio / Engine / Lab` 路由。
- **Changes**：前端已接入真实 API 客户端、React Query 远程状态、Zustand 本地会话与工作台偏好存储；`Lobby` 已支持项目列表/创建/回收站恢复与 `Credential Center`，`Studio` 已支持项目设定、`outline/opening_plan`、章节编辑与版本面板，`Engine` 已支持工作流控制、任务/日志/审核/账单/上下文/回放/导出面板，`Lab` 已支持分析列表/详情/创建。
- **Changes**：为满足 `Studio` 回显需求，后端补充了 `GET /api/v1/projects/{project_id}/outline` 与 `GET /api/v1/projects/{project_id}/opening-plan`，并新增 `test_story_asset_api.py` 覆盖读取闭环。
- **Insights**：当前后端的 SSE 认证仍是 `Authorization Bearer` 方案，浏览器原生 `EventSource` 不能直接带这个头，因此本轮 `Engine` 明确采用轮询刷新，而不是做隐式前端降级。
- **Insights**：工作台页面依赖本地会话和查询参数，不适合静态预渲染；前端路由已显式标记为动态页，并将 Zustand 持久化存储改为 SSR 安全实现。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_story_asset_service.py tests/unit/test_story_asset_api.py` 通过，`7 passed`。
- **Validation**：`pnpm install` 已完成并生成锁文件。
- **Validation**：`pnpm --dir apps/web lint`、`pnpm --dir apps/web exec tsc --noEmit`、`pnpm --dir apps/web exec next build --webpack` 通过。
- **Validation**：默认 `next build` 在当前沙箱中会因 Turbopack/PostCSS 子进程端口绑定限制失败；这已确认是环境级现象，不是当前前端代码编译错误。

## [2026-03-21 | Web 前端 review 问题修复完成]
- **Events**：完成 Web MVP 首轮代码审查后的 3 个前端修复，覆盖工作台导航上下文、导出认证下载和 Engine 状态动作映射。
- **Changes**：`workspace-store` 新增 `lastProjectId`，`WorkspaceShell` 现在按当前 pathname 解析 `projectId` 并回写最近项目；`Studio / Engine / Lab` 不再硬编码 `demo`，无项目上下文时改为禁用导航项，避免坏链路。
- **Changes**：`export.ts` 新增受控下载 helper，`EngineExportPanel` 改为 Bearer `fetch -> blob -> a.click()` 下载链路，并在面板内显式显示下载成功或失败反馈，不再使用会丢认证头的 `window.open()`。
- **Changes**：`EnginePage` 已把工作流控制按钮改为基于 `workflow.status` 的显式派生；新增 `engine-workflow-controls.ts` 收敛状态动作与轮询判定，并拆出 `engine-block.tsx` 保持文件职责清晰。
- **Insights**：`failed` 不能简单当成“新建一次”的终态；当前后端状态机允许 `failed -> running`，因此前端动作映射保留为 `恢复 + 取消`，而 `completed / cancelled / 无 workflow` 才回到“启动工作流”主入口。
- **Insights**：认证下载属于 API 客户端职责，不能继续走浏览器默认新开页链路；否则一旦接口只认 `Authorization: Bearer`，UI 就会稳定 401。
- **Validation**：`pnpm --dir apps/web lint` 通过。
- **Validation**：`pnpm --dir apps/web exec tsc --noEmit` 通过。
- **Validation**：`pnpm --dir apps/web exec next build --webpack` 通过。
