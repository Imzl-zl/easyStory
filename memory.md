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

## [2026-03-21 | Auth CORS 预检修复完成]
- **Events**：修复了 Web 注册接口的浏览器预检失败问题，解决 `OPTIONS /api/v1/auth/register` 返回 `405 Method Not Allowed`。
- **Changes**：新增 `app/entry/http/cors.py`，将 CORS 装配收敛到入口层；`create_app()` 现在会注册 `CORSMiddleware`，默认允许 `localhost/127.0.0.1` 任意端口的本地 Web 开发源通过预检。
- **Changes**：额外跨域白名单支持通过 `EASYSTORY_CORS_ALLOWED_ORIGINS`（逗号分隔）和 `EASYSTORY_CORS_ALLOWED_ORIGIN_REGEX` 扩展，不再把 origin 策略硬编码死在 `main.py`。
- **Changes**：新增 `tests/unit/test_auth_api.py`，覆盖本地 Web origin 对 `/api/v1/auth/register` 的 CORS 预检，以及 CORS 修复后注册接口仍正常签发 token 的回归场景。
- **Insights**：这次报错根因不在认证服务，而是在 API 入口层缺少跨域中间件；浏览器跨域 JSON `POST` 会先发 `OPTIONS`，如果入口层不处理，业务路由即使正确也会先被 405 拦掉。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_auth_api.py tests/unit/test_preparation_api.py::test_auth_register_and_login_issue_tokens` 通过，`3 passed`。

## [2026-03-21 | 后端 settings 与 .env 基线补齐完成]
- **Events**：完成后端运行时配置基线收口，补齐统一 settings 层、`.env` 自动加载、`.env.example`、测试基座和文档说明。
- **Changes**：新增 `app/shared/settings.py`，用 `pydantic-settings` 统一管理 `EASYSTORY_DATABASE_URL`、`EASYSTORY_JWT_SECRET`、`EASYSTORY_JWT_EXPIRE_HOURS`、`EASYSTORY_CREDENTIAL_MASTER_KEY`、`EASYSTORY_CORS_ALLOWED_ORIGINS`、`EASYSTORY_CORS_ALLOWED_ORIGIN_REGEX`，并提供 `get_settings()/clear_settings_cache()/validate_startup_settings()`。
- **Changes**：`create_app()` 现在改为通过 lifespan 在服务启动时校验 `EASYSTORY_JWT_SECRET`；JWT、数据库、CORS、Credential master key 的读取点都已改为走 settings 真值源，不再各自散落 `os.getenv()`。
- **Changes**：新增 `apps/api/.env.example`，明确区分必需项、条件必需项和可选项；`docs/README.md` 已补后端环境配置说明，`.gitignore` 已忽略本地 `.env` 并保留示例文件。
- **Changes**：`tests/conftest.py` 新增自动清理 settings cache 的 fixture，避免 `monkeypatch.setenv()` 与 `lru_cache` 互相污染；新增 `tests/unit/test_settings.py` 覆盖 `.env` 文件读取、JWT 必需项校验和 CORS 逗号分隔解析。
- **Changes**：`apps/api/pyproject.toml` 已把 `python-dotenv` 声明为直接依赖，并通过 `uv lock --offline` 同步锁文件，避免继续依赖 `litellm` 的传递安装。
- **Insights**：统一 settings 后，配置错误会在“启动应用”或“触发对应能力”时明确暴露，不再变成分散在不同链路中的偶发问题；同时保持了测试里 `create_app(session_factory=...) + monkeypatch.setenv()` 的现有使用方式。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_settings.py tests/unit/test_auth_api.py tests/unit/test_preparation_api.py::test_create_app_bootstraps_database_session_factory tests/unit/test_preparation_api.py::test_auth_register_and_login_issue_tokens tests/unit/test_credential_service.py tests/unit/test_credential_api.py tests/unit/test_workflow_engine.py::test_app_registers_health_route` 通过，`19 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv lock --offline` 通过。

## [2026-03-21 | settings 正式规格同步完成]
- **Events**：完成 settings 基线任务收尾，将运行时 `.env` 约定同步回正式配置规格。
- **Changes**：`docs/specs/config-format.md` 已补充 `apps/api/.env` / `apps/api/.env.example`、统一 settings 入口、环境变量表和启动/懒校验规则，避免 README、代码与规格文档脱节。
- **Insights**：后端运行时环境配置与 `/config/*.yaml` 必须明确区分边界；前者属于部署注入，后者属于业务配置真值，不能再混写成一套“默认大家都懂”的隐式约定。

## [2026-03-21 | settings 审查回归问题修复完成]
- **Events**：完成 settings 基线在代码审查后暴露出的异常语义与依赖注入回归修复。
- **Changes**：`app/shared/settings.py` 现在会在 `jwt_expire_hours` 的原始值阶段显式解析整数，并把非整数配置也统一收敛为 `ConfigurationError`，不再泄漏 `pydantic ValidationError`。
- **Changes**：`TokenService` 改为仅在需要默认值时才读取 settings；显式传入 `secret` / `expire_hours` 时不再被全局坏环境变量反向污染，同时会拒绝空字符串 secret。
- **Changes**：新增 `test_token_service.py`，并扩展 `test_settings.py`，覆盖非整数过期时间、显式注入绕开坏环境变量以及空 secret 拒绝场景。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_settings.py tests/unit/test_token_service.py tests/unit/test_auth_api.py tests/unit/test_preparation_api.py::test_create_app_bootstraps_database_session_factory tests/unit/test_preparation_api.py::test_auth_register_and_login_issue_tokens tests/unit/test_credential_service.py tests/unit/test_credential_api.py tests/unit/test_workflow_engine.py::test_app_registers_health_route` 通过，`23 passed`。

## [2026-03-21 | template 最小闭环推进中]
- **Events**：启动 `template` 模块最小闭环收口，目标是补齐内置模板查询与 `Lobby` 模板选择联调。
- **Changes**：新增 `BuiltinTemplateSyncService`、`template` HTTP 路由、`test_template_service.py`、`test_template_api.py`；当前内置模板配置加入 `template_key=template.xuanhuan`，并把 builtin sync 从查询服务中剥离，避免读接口写库。
- **Changes**：`Lobby` 已接入 `/api/v1/templates`，支持默认模板选择、模板摘要预览、创建项目时提交 `template_id`，并在项目卡片回显模板名；新增前端 `templates.ts` 和模板契约类型。
- **Changes**：为兼容当前测试环境，对一批 API 测试引入 `client_helper.py` 作为 in-process 客户端抽象，减少各文件分散处理启动/关闭逻辑。
- **Insights**：旧的按模板名称匹配 builtin 数据会埋下重名漂移风险；当前已改成优先按 `template_key` 对齐 builtin 模板，再兼容旧数据按名称升级。
- **Insights**：本地 Python 3.13 环境下，API 级 in-process transport 对同步路由仍存在阻塞现象；直接服务调用、startup task 和 `template` service 单测可正常执行，但内嵌客户端命中真实同步路由时仍需继续定位 transport 层问题。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_template_service.py` 通过，`3 passed`。
- **Validation**：`pnpm --dir apps/web lint`、`pnpm --dir apps/web exec tsc --noEmit` 通过。

## [2026-03-21 | API sync path 根因确认与 async 迁移启动]
- **Events**：完成对 API 阻塞问题的根因定位，并正式启动后端 async-first 迁移任务。
- **Changes**：新增 `.codex-tasks/20260321-api-async-foundation/`，记录根因、迁移边界、阶段任务与恢复说明；新增 `docs/plans/2026-03-21-api-async-migration.md` 作为正式迁移计划。
- **Changes**：`app.main.create_app()` 已从 `@app.on_event("startup")` 收敛为 `FastAPI(..., lifespan=app_lifespan)`；新增 `tests/unit/test_app_lifespan.py` 验证 lifespan 启动阶段会完成 builtin template sync。
- **Changes**：`tests/unit/client_helper.py` 已改为与 app lifespan 对齐的生命周期管理，避免在后续 async 迁移期间继续叠加错误的 startup/shutdown 语义偏差。

## [2026-03-22 | review 阻塞项修复完成]
- **Events**：完成本轮 code review 暴露的两条真实阻塞问题与两条清理项修复，达到可提交状态。
- **Changes**：`app/shared/db/session.py` 中 `get_async_session_factory()` 已收敛回同步 accessor，避免 `workflow` 默认 dispatcher 直接调用时拿到 coroutine；新增 `tests/unit/test_workflow_runtime_dispatcher.py` 锁定该回归。
- **Changes**：`project_deletion_service.py` 现改为先 `await db.commit()` 再执行 `cleanup_project_export_directory()`；新增 `tests/unit/test_project_deletion_transaction.py`，覆盖 commit 失败时保留导出目录与项目记录的事务边界。
- **Changes**：删除无引用的 `apps/api/app/modules/project/service/project_sync_service.py`；将 `apps/web/tsconfig.tsbuildinfo` 恢复到 `HEAD`，不再把构建产物带入本次提交。
- **Insights**：async-first 收口不等于所有 helper 都要 async；像 `request.app.state` 这种纯内存 accessor 继续保持同步语义，反而更符合 FastAPI 依赖和直接调用两种使用面。
- **Insights**：任何会产生文件系统副作用的删除逻辑，都必须放在数据库事务成功提交之后，否则一旦 commit 失败就会制造“数据库回滚、文件已删”的不可恢复不一致。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_workflow_runtime_dispatcher.py tests/unit/test_project_deletion_service.py tests/unit/test_project_deletion_transaction.py tests/unit/test_workflow_api.py tests/unit/test_db_bootstrap.py` 通过，`16 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `303 passed`。

## [2026-03-22 | content 公共服务 async-only 收口完成]
- **Events**：继续按 async-first 迁移计划推进，完成 `content` 模块公开服务的单一 async 真值收口。
- **Changes**：`StoryAssetService` 与 `ChapterContentService` 现已直接承载 async 实现；`content` 包不再暴露 `AsyncStoryAssetService`、`AsyncChapterContentService`、`create_async_story_asset_service`、`create_async_chapter_content_service`。
- **Changes**：`chapter_service_support.py` 新增章节版本写入与回滚 payload 辅助函数；删除 `async_story_asset_service.py` 与 `async_chapter_content_service.py`，并同步更新 `content` router、`workflow` runtime/factory、`api_test_support.py` 与相关服务/runtime 测试。
- **Changes**：新增 `tests/unit/async_service_support.py`，让同步 `Session` 单测可显式驱动 async service；`test_story_asset_service.py`、`test_chapter_content_service.py`、`test_workflow_runtime.py`、`test_workflow_runtime_auto_fix.py` 已统一切到单一命名。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_story_asset_service.py tests/unit/test_chapter_content_service.py tests/unit/test_story_asset_api.py tests/unit/test_chapter_content_api.py tests/unit/test_workflow_runtime.py tests/unit/test_workflow_runtime_auto_fix.py` 通过，`32 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-22 | async 基线正式收口完成]
- **Events**：完成本轮 async-first 收口，将 builtin template startup、workflow app 公共出口与残余同步 factory 清理到正式完成态。
- **Changes**：新增 `AsyncBuiltinTemplateSyncService`；`app.main` 的 lifespan 现在通过 `async_session_factory` 执行 builtin template sync，`template` 模块公共导出已改为 async-first。
- **Changes**：新增 `workflow_app_service_base.py`，把 workflow app 的共享 execution 构建和日志写入能力从 sync 实现里抽离；`AsyncWorkflowAppService` 不再继承 sync `WorkflowAppService`。
- **Changes**：删除无引用的 sync workflow app/runtime support，以及 `create_workflow_app_service`、`create_chapter_task_service`、`create_builtin_template_sync_service` 这类遗留同步 factory 暴露；`workflow.service` 公共入口现只导出 async app/chapter-task service。
- **Changes**：`test_app_lifespan.py`、`test_template_service.py`、`test_workflow_app_service.py` 已迁到 async 基座；`tools.md` 已同步 workflow 控制面正式入口为 `async_workflow_app_service.py`。
- **Insights**：这轮遗留根因不是业务逻辑问题，而是“async 正式路径”和“legacy sync 兼容层”长期并存导致的双真值；如果不删除无引用同步出口，后续模块迁移会继续反复把桥接逻辑带回来。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。
- **Validation**：`rg -n "run_sync|asyncio\\.run|create_builtin_template_sync_service|create_workflow_app_service|create_chapter_task_service" apps/api/app` 无结果，说明本轮目标范围内的生产代码同步残留已清空。

## [2026-03-22 | app/auth 入口 async-only 收口完成]
- **Events**：继续沿 async-first 迁移收口应用入口与认证依赖，移除 `create_app` 双 session 基线和受保护路由的旧 async 命名残留。
- **Changes**：`create_app()` 已改成只挂载 `app.state.async_session_factory`；新增 `initialize_async_database()` 并在 lifespan startup 中异步建表，不再依赖同步 `create_session_factory()` 为 app 隐式建表。
- **Changes**：`shared/db` 运行时公共入口已移除 `get_db_session()` / `get_session_factory()`；`get_async_session_factory()` 也已改为 async dependency 包装。
- **Changes**：`AuthService` 现在只保留 async `authenticate()` 和 async 用户查询 helper；`user.entry.http.dependencies` 已收敛为单一 `get_current_user`，并删除 `get_current_user_async` 第二命名入口。
- **Changes**：所有受保护路由和 `get_*service` 依赖提供器都改成 async；`/healthz` 也已改为 async route。所有 API tests 已移除 `create_app(session_factory=...)` 与 `app.state.session_factory` 依赖。
- **Insights**：在当前依赖栈里，哪怕只是不做 IO 的 `def` dependency，也仍然属于应清理的同步执行面；否则 async-first 只是表面完成，真实执行模型仍然分叉。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_*api.py tests/unit/test_auth_service.py tests/unit/test_app_lifespan.py tests/unit/test_workflow_engine.py` 通过，`65 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量仍为 `300 passed`。
- **Validation**：`rg -n "get_current_user_async|get_db_session|app\\.state\\.session_factory" apps/api/app apps/api/tests --glob '*.py'` 无结果。

## [2026-03-21 | workflow runtime 原生 async 收口完成]
- **Events**：完成 `workflow runtime` 执行链的原生 async 收口，去掉正式 Async API/runtime 路径中的 `run_sync` 与 `asyncio.run` 桥接。
- **Changes**：新增 `AsyncBillingService`，并为 `AsyncCredentialService` 补齐 `resolve_active_credential()`；`WorkflowRuntimeService` 及其 `execute/review/fix/prompt/task/export/persistence/chapter-candidate` mixin 已全部切到 `AsyncSession`。
- **Changes**：`workflow` router dispatcher 已改为 `AsyncSessionFactory + asyncio.create_task`；`AsyncWorkflowAppService` 通过 `async_workflow_app_runtime_support.py` 直接调度 async runtime，不再走 `db.run_sync(...)`。
- **Changes**：为降低维护成本，新拆 `workflow_runtime_fix_mixin.py`、`async_workflow_app_runtime_support.py`；`context.service/__init__.py` 与 `workflow.service/__init__.py` 改为 lazy export，消除导入期循环依赖。
- **Insights**：`AsyncSession` 下不能继续依赖 ORM 关系集合的隐式 `append` 装载；像 `Artifact`、`ReviewAction` 这类运行时副产物，改成显式 `db.add(...)` 才能避免 `MissingGreenlet`。
- **Insights**：当前 app 中剩余唯一 `asyncio.run` 位于 `workflow_app_runtime_support.py` 的 legacy sync `WorkflowAppService` 兼容桥，不在正式 Async API/runtime 路径。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，结果 `300 passed`。

## [2026-03-21 | ProjectDeletionService 物理删除闭环完成]
- **Events**：完成 `project` 聚合统一删除服务收口，补齐 `physical_delete` 的同步/异步服务、API 与测试闭环。
- **Changes**：新增 `project_deletion_support.py`、`project_deletion_service.py`、`async_project_deletion_service.py`；`project` router 现在通过独立 deletion service 处理 `soft_delete / restore / physical_delete`，并新增 `DELETE /api/v1/projects/{project_id}/physical` 返回 `204`。
- **Changes**：`project_management_service` 与 `async_project_management_service` 已移除删除职责，只保留 create/list/get/update；factory 与 service 导出同步补齐 deletion service。
- **Changes**：物理删除采用显式顺序清理 `PromptReplay / ExecutionLog / ReviewAction / Artifact / TokenUsage / ChapterTask / StoryFact / Export / AuditLog / ContentVersion / Analysis / NodeExecution / WorkflowExecution / Content`，最后删除 `Project`，并同步清理 `.runtime/exports/<project_id>/` 导出目录。
- **Insights**：当前 `Project` ORM relationship 只覆盖 `contents / analyses / workflow_executions`，不能指望 `db.delete(project)` 自动清理 `context/export/billing/observability` 侧数据；这次改动把删除边界收敛为单一真值源，避免后期继续出现“看起来删了，实际上残留”的隐患。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_project_management_service.py tests/unit/test_project_deletion_service.py tests/unit/test_project_api.py` 通过，`10 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-21 | async 原生查询链路收口完成]
- **Events**：继续推进 async-first 迁移，清理 API 查询层剩余的 `run_sync` 过渡桥。
- **Changes**：新增 `AsyncBillingQueryService`、`AsyncReviewQueryService`、`AsyncWorkflowObservabilityService`；`billing/review/observability` 路由现在直接调用原生 async 查询服务，不再通过 `AsyncSession.run_sync()` 包装同步 service。
- **Changes**：为 `context-preview` 新增 `AsyncContextSourceLoader`、`AsyncContextBuilder`、`AsyncContextPreviewService`，彻底移除 `context` 路由中对同步 builder/source loader 的桥接。
- **Insights**：`context-preview` 不能只把 `run_sync` 从 router 挪到 service；如果 `ContextBuilder` 和 `ContextSourceLoader` 仍是同步实现，问题只是被藏起来，不算真正修复。
- **Insights**：截至本轮，`apps/api/app` 中唯一剩余的 `run_sync` 位于 `workflow/service/async_workflow_app_service.py`，属于 workflow runtime 内核桥接，不再是 API 查询层问题。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_context_api.py tests/unit/test_review_api.py tests/unit/test_billing_api.py tests/unit/test_workflow_observability_api.py tests/unit/test_context_preview_service.py` 通过，`16 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-21 | Story Bible 基础后端闭环完成]
- **Events**：继续稳步推进后端，补齐 `context` 模块的 Story Bible 基础能力，并把章节回滚接回事实视角同步。
- **Changes**：新增 `StoryBibleService / AsyncStoryBibleService`、`story_bible_factory.py`、`StoryFactCreateDTO / StoryFactDTO / StoryFactMutationResultDTO`，开放 `GET/POST /api/v1/projects/{project_id}/story-bible` 以及 `POST /story-bible/{fact_id}/confirm-conflict`、`POST /story-bible/{fact_id}/supersede`。
- **Changes**：`create_fact` 语义已明确：无同键激活事实时直接创建；同版本重复抽取自动 supersede；跨版本同键默认落 `potential_conflict`，并支持后续显式 `confirm-conflict` 或 `supersede`。
- **Changes**：`ChapterContentService` 与 `AsyncChapterContentService` 的 `rollback_version()` 已接入 Story Bible 同步；回滚到旧版本时会停用当前章节活跃 facts、重新激活目标版本 facts，并清掉旧 facts 的 `superseded_by`，让注入视角回到目标版本。
- **Insights**：这轮暴露出的真实根因不是业务规则，而是循环导入：`content -> context.service.__init__ -> context_preview -> workflow -> content`。修复方式是把 Story Bible factory 单独拆成 `story_bible_factory.py`，并让 `content` 侧做定向导入，避免包级 `__init__` 继续成为隐式依赖放大器。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_story_bible_service.py tests/unit/test_story_bible_api.py tests/unit/test_chapter_content_service.py` 通过，`16 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `295 passed`。
- **Insights**：FastAPI / Starlette 官方文档已确认同步 `def` 路由与同步 dependency 会走线程池，Starlette 明确底层通过 `anyio.to_thread.run_sync` 执行；当前仓库绝大多数 API 面都依赖这条路径。
- **Insights**：本地最小复现已确认在当前版本组合 `Python 3.13.12 + FastAPI 0.135.1 + Starlette 0.52.1 + AnyIO 4.12.1` 下，`anyio.to_thread.run_sync()` 挂死，而 `asyncio.to_thread()` 正常；因此问题不是单个模块或单个测试写法，而是同步 API 基线本身不可靠。
- **Insights**：`docs/plans/2026-03-17-backend-core-v2.md` 原本就以 async SQLAlchemy 和 async 测试基座为目标，当前故障本质上也是“正式计划未完全落地”被运行时放大的结果。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_app_lifespan.py tests/unit/test_settings.py tests/unit/test_template_service.py` 通过，`9 passed`。

## [2026-03-21 | async foundation 首批链路落地]
- **Events**：继续推进 async-first 迁移，完成 `shared/db` 基线和 `auth/template` 首批链路收口。
- **Changes**：`app/shared/db` 已新增 `create_async_database_engine()`、`create_async_session_factory()`、`resolve_async_database_url()`、`get_async_db_session()`；`create_app()` 已支持显式注入 `async_session_factory`。
- **Changes**：`auth` 的 `register/login` 已改为 `async route + AsyncSession`；`AuthService` 已新增 async 版 `register/login/authenticate_async`，并保留旧 `authenticate(Session)` 供尚未迁移的同步受保护路由继续使用。
- **Changes**：`template` 查询 API 已改为 `async route + AsyncSession + async query service`；模板 API 认证改走独立 `get_current_user_async()`，避免在未迁移模块上误触半成品依赖链。
- **Changes**：新增 `tests/unit/async_api_support.py`，用文件型 SQLite、`httpx.AsyncClient`、`ASGITransport`、显式 lifespan 管理跑 async API；新增 `test_db_bootstrap.py` 验证 async DB URL 解析。
- **Insights**：在全仓尚未完成 async 化前，最稳妥的迁移策略不是“一次性切全局 auth dependency”，而是对已迁移模块显式使用 async 认证依赖，避免把大量仍基于内存 sync SQLite 的旧测试链路一起拖爆。
- **Insights**：文件型 SQLite 是当前迁移阶段最实用的桥梁，它允许 sync startup/bootstrap 与 async route/query 共用同一数据库文件，比继续在 `sqlite://` 内存库上硬拼 sync/async 混合访问更可控。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests/unit/test_auth_service.py tests/unit/test_auth_api.py tests/unit/test_template_api.py tests/unit/test_template_service.py tests/unit/test_preparation_api.py tests/unit/async_api_support.py tests/unit/test_db_bootstrap.py` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_db_bootstrap.py tests/unit/test_auth_service.py tests/unit/test_app_lifespan.py tests/unit/test_settings.py tests/unit/test_template_service.py tests/unit/test_auth_api.py tests/unit/test_template_api.py tests/unit/test_preparation_api.py::test_auth_register_and_login_issue_tokens` 通过，`17 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_preparation_api.py::test_preparation_endpoints_drive_outline_to_opening_plan_flow tests/unit/test_project_api.py::test_project_api_manages_project_lifecycle tests/unit/test_workflow_api.py::test_start_workflow_creates_running_execution_with_snapshots` 通过，`3 passed`。

## [2026-03-21 | async foundation 第二批链路落地]
- **Events**：继续推进 async-first 迁移，完成 `project` 与 `analysis` 的 HTTP 链路收口。
- **Changes**：`project` 新增 `async_project_service.py` 与 `async_project_management_service.py`，项目管理、项目详情、项目设定更新和完整度检查已切到 `AsyncSession`；旧 sync `ProjectService/ProjectManagementService` 继续保留给尚未迁移的内部服务使用。
- **Changes**：`analysis` 新增 `AsyncAnalysisService`，`analysis` 路由已切到 async route + async service，并通过 `AsyncProjectService` 完成项目 owner 校验和 content 归属校验。
- **Changes**：`AuditLogService.record()` 已放宽到可接收 `AsyncSession`，让 project async 管理服务可以继续复用同一份审计落库逻辑，而不新造第二套审计真值。
- **Changes**：`test_project_api.py` 与 `test_analysis_api.py` 已切到 async API 客户端；`test_preparation_api.py` 中直接命中 project setting 路径的用例已补双工厂文件型 SQLite 基座，避免 async 路由落在缺失 `async_session_factory` 的旧测试环境上。
- **Insights**：`project` 是后续 `content/workflow/analysis` 的聚合根，先把它迁成 async，可以避免后面每个模块都各自再造一份 project owner 校验逻辑。
- **Insights**：对仍未迁移的 `content` 混合链路，当前最稳妥做法仍是“双工厂 + 文件型 SQLite + 临时 client helper”；等 `content/workflow` 全面 async 化后，再统一删掉同步测试 helper。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app/modules/project app/modules/observability/service/audit_log_service.py tests/unit/test_project_api.py tests/unit/test_preparation_api.py` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_project_api.py tests/unit/test_project_management_service.py tests/unit/test_preparation_api.py::test_create_app_bootstraps_database_session_factory tests/unit/test_preparation_api.py::test_preparation_endpoints_require_authentication tests/unit/test_preparation_api.py::test_preparation_endpoints_hide_other_users_project tests/unit/test_preparation_api.py::test_preparation_endpoints_drive_outline_to_opening_plan_flow` 通过，`9 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app/modules/analysis tests/unit/test_analysis_api.py` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_analysis_service.py tests/unit/test_analysis_api.py tests/unit/test_project_api.py::test_project_api_manages_project_lifecycle` 通过，`7 passed`。

## [2026-03-21 | async foundation 第三批 content 链路落地]
- **Events**：继续推进 async-first 迁移，完成 `content` 模块 HTTP 链路、服务层和相关 API 测试收口。
- **Changes**：新增 `AsyncStoryAssetService` 与 `AsyncChapterContentService`，`content` 路由已统一切到 `AsyncSession + get_current_user_async`；`story asset`、章节读写、版本回滚/最佳版本等入口都不再依赖同步线程池路径。
- **Changes**：`chapter_store.py` 与 `chapter_mutation_support.py` 已补 async 查询/状态辅助函数；`AsyncProjectService.require_project()` 新增 `load_contents` 参数，供 `content` 在 async 场景下显式预加载 `project.contents`。
- **Changes**：`tests/unit/test_story_asset_api.py`、`tests/unit/test_chapter_content_api.py`、`tests/unit/test_preparation_api.py` 中仍命中 content 路径的用例已全部切到 async API 客户端；同步 `content` 服务单测和 `tests/unit/test_workflow_api.py::test_start_workflow_creates_running_execution_with_snapshots` 也已回归通过。
- **Insights**：async SQLAlchemy 下不仅要避免 sync route/dependency，还要避免“新建 ORM 对象后第一次触发关系惰性加载”；这次 `Content.versions` 就暴露了 `MissingGreenlet`，根修是对新建 `Content` 显式初始化 `versions=[]`，而不是再包一层 fallback。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app/modules/content app/modules/project/service/async_project_service.py tests/unit/test_story_asset_api.py tests/unit/test_chapter_content_api.py tests/unit/test_preparation_api.py` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_story_asset_api.py tests/unit/test_chapter_content_api.py tests/unit/test_preparation_api.py` 通过，`9 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_story_asset_service.py tests/unit/test_chapter_content_service.py tests/unit/test_workflow_api.py::test_start_workflow_creates_running_execution_with_snapshots` 通过，`15 passed`。

## [2026-03-21 | async foundation 第四批 workflow 控制面落地]
- **Events**：继续推进 async-first 迁移，完成 `workflow` 控制面和 `chapter task` 管理 API 的 async 收口。
- **Changes**：新增 `AsyncWorkflowAppService` 与 `AsyncChapterTaskService`，`workflow` 路由已统一切到 `AsyncSession + get_current_user_async`；同时扩展 `AsyncProjectService.require_project(load_template=True)`，显式预加载模板关系，避免工作流启动时访问 `project.template` 触发隐式 IO。
- **Changes**：`workflow_task_runtime_support.py` 已补 `ensure_workflow_can_resume_async()` 等 async 校验函数；`tests/unit/test_workflow_api.py` 与 `tests/unit/test_chapter_task_api.py` 已全部切到 async API 客户端。
- **Changes**：为保持现有 workflow runtime 不大改而先收口 HTTP 面，测试里的内联 dispatcher 已调整为独立线程执行并 join；这样仍保持“请求返回前 runtime 已完成”的断言语义，同时避免在当前事件循环线程里直接命中 runtime 内部的 `asyncio.run()`。
- **Insights**：async 会话下 `expire_all()` 后再读 ORM 实例字段也可能触发 `MissingGreenlet`；这次 `AsyncWorkflowAppService.start/resume` 的 `workflow.id` 就暴露了这个问题，根修是提前缓存 `execution_id`，而不是继续依赖过期对象。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app/modules/workflow app/modules/project/service/async_project_service.py tests/unit/test_workflow_api.py tests/unit/test_chapter_task_api.py` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_workflow_api.py tests/unit/test_chapter_task_api.py` 通过，`13 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_workflow_app_service.py tests/unit/test_preparation_api.py` 通过，`7 passed`。

## [2026-03-21 | async foundation 收口完成]
- **Events**：完成 async-first foundation 收口，把剩余同步 HTTP 入口、旧 API 测试 helper 和跨测试文件耦合一并清理。
- **Changes**：`observability`、`review`、`billing`、`context` 路由已统一切到 `async def + get_current_user_async + get_async_db_session`，并通过 SQLAlchemy 官方 `AsyncSession.run_sync()` 复用现有纯查询 service，避免为只读查询平铺第二套 async 业务实现。
- **Changes**：新增 `AsyncExportService`、`AsyncCredentialService` 与 `AsyncHttpCredentialVerifier`；`export` 不再把文件写入包在 sync route 里，`credential verify` 也不再在 async 边界里继续走阻塞式 `urlopen`。
- **Changes**：新增 `tests/unit/api_test_support.py` 收敛 runtime app、认证 header 和 workflow seed helper；`tests/unit/test_context_api.py`、`test_billing_api.py`、`test_review_api.py`、`test_export_api.py`、`test_workflow_observability_api.py`、`test_credential_api.py` 已全部改到 async 基座，`tests/unit/client_helper.py` 已删除。
- **Insights**：对纯 DB 查询链路，`AsyncSession.run_sync()` 是比“复制一份 async query service”更稳妥的维护方案；但一旦 service 内含文件 IO 或外部 HTTP IO，就必须拆成真正 async 实现，否则会重新把阻塞带回事件循环。
- **Insights**：`test_workflow_api.py` 不应再承担“共享 helper 仓库”职责；共享构建逻辑抽到独立 support 文件后，测试恢复上下文更直接，也避免单个测试文件演进时把其他测试一起拖坏。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_project_api.py tests/unit/test_template_api.py tests/unit/test_analysis_api.py tests/unit/test_workflow_api.py tests/unit/test_context_api.py tests/unit/test_billing_api.py tests/unit/test_review_api.py tests/unit/test_export_api.py tests/unit/test_workflow_observability_api.py tests/unit/test_credential_api.py` 通过，`33 passed`。

## [2026-03-22 | 查询型 service 单一 async 真值收口完成]
- **Events**：继续推进 async-first 迁移，把 `analysis / billing / review / observability` 的服务层从“同步基类 + 异步子类”中间态收口为单一 async 真值。
- **Changes**：`analysis` 已删除同文件 sync/async 双实现，只保留 async `AnalysisService`；`analysis` router 与 factory 统一收敛到 `AnalysisService + create_analysis_service`。
- **Changes**：`billing`、`review`、`observability` 已删除 `AsyncBillingQueryService`、`AsyncReviewQueryService`、`AsyncWorkflowObservabilityService` 镜像类与对应 `create_async_*` 导出，router / `__init__` / factory 全部改为单一 async service 命名。
- **Changes**：新增 `billing_query_support.py`，承载 `billing` 的纯聚合、预算状态转换和 token usage DTO 映射，避免 `billing_query_service.py` 超过 300 行并保持查询流程职责单一。
- **Changes**：`test_analysis_service.py`、`test_billing_query_service.py`、`test_review_query_service.py`、`test_workflow_observability_service.py` 已切到文件型 SQLite + `async_session_factory`；同步 seed 只保留在测试数据预置阶段。
- **Insights**：对已明确只服务 async HTTP 面的模块，继续保留 `Async*Service` 镜像命名只会制造第二套公共真值；更清晰的做法是让模块公共入口直接回到单一 `Service + create_*_service`。
- **Insights**：文件大小限制不是形式问题。`billing_query_service.py` 在合并后立刻暴露出“查询流程和 DTO 聚合逻辑耦在一起”的结构问题，拆出私有 support 模块后职责边界更清楚，也更便于后续继续迁移其它模块。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_analysis_service.py tests/unit/test_analysis_api.py tests/unit/test_billing_query_service.py tests/unit/test_billing_api.py tests/unit/test_review_query_service.py tests/unit/test_review_api.py tests/unit/test_workflow_observability_service.py tests/unit/test_workflow_observability_api.py` 通过，`25 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-22 | workflow 控制面单一 async 真值收口完成]
- **Events**：继续推进 async-first 迁移，将 `workflow` 控制面从 `Async*` 迁移中间态收敛为单一 async 真值。
- **Changes**：新增 `workflow_app_service.py` 与 `workflow_app_runtime_support.py`；公开控制面 service 已统一为 `WorkflowAppService`，不再保留 `AsyncWorkflowAppService` 与 `create_async_workflow_app_service`。
- **Changes**：`chapter_task_service.py` 已收敛为单一 async `ChapterTaskService`；新增 `chapter_task_support.py` 承载 `advance_workflow_after_regenerate`、task 可编辑校验、DTO 转换等纯 helper，并删除 `async_chapter_task_service.py`。
- **Changes**：`workflow` router、`workflow.service.__init__`、`factory.py`、`tests/unit/api_test_support.py`、`test_workflow_app_service.py` 已全部切到单一命名。
- **Insights**：`workflow` 是主链路中心，控制面继续保留 `Async*` 命名会放大理解成本，因为它并没有同步公共真值可对照；这类“只剩 async 一套实现”的模块，公共命名应直接回到业务名本身。
- **Insights**：`ChapterTaskService` 这次再次证明，合并 async 真值时最容易失控的是“流程逻辑和纯 DTO/helper 混在一个文件”。先拆 support，再合并主服务，是更稳的结构化做法。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_workflow_app_service.py tests/unit/test_workflow_api.py tests/unit/test_chapter_task_api.py tests/unit/test_workflow_observability_api.py` 通过，`19 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-22 | project/export 单一 async 真值收口完成]
- **Events**：完成 `project` 与 `export` 的公开 async 中间态收口，并补齐启动职责边界与任务记录。
- **Changes**：`project` 公开入口已统一为 async `ProjectService / ProjectManagementService / ProjectDeletionService` 与 `create_*`；旧同步项目访问已降为内部 `SyncProjectService`，仅供同步 `credential/story_bible` 复用。
- **Changes**：`export` 公开入口已统一为 async `ExportService` 与 `create_export_service`；`workflow runtime`、router、`tests/unit/api_test_support.py` 和相关测试已全部切到单一命名。
- **Changes**：`create_app()` 现在只会在“内部自行创建 async session factory”时执行启动期建库；外部注入 `async_session_factory` 的测试/宿主路径只挂载 factory 并继续执行 settings/template startup，避免越权接管外部数据库生命周期。
- **Insights**：当前 Codex 默认沙箱与 `aiosqlite` 不兼容；命中 async SQLite 的 lifespan / async API / 全量 `pytest` 需要在非沙箱环境执行，否则会表现为挂起而不是显式报错。
- **Insights**：这次已对照验证 `aiosqlite 0.21.0` 与 `0.22.1` 在非沙箱环境都可正常 `connect(':memory:')`，因此根因不是依赖版本回归；已将临时依赖降级恢复，避免引入错误的版本约束。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_app_lifespan.py` 通过，`1 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_export_api.py tests/unit/test_export_service.py tests/unit/test_workflow_runtime.py tests/unit/test_workflow_runtime_auto_fix.py` 通过，`18 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-22 | context 单一 async 真值收口完成]
- **Events**：完成 `context` 模块公开 async 中间态收口，并同步下游 `content` 与相关测试。
- **Changes**：`context` 公开入口已统一为 async `ContextPreviewService / StoryBibleService` 与 `create_context_preview_service / create_story_bible_service`；`AsyncContextPreviewService`、`AsyncStoryBibleService` 与 `create_async_*` 公共导出已移除。
- **Changes**：`context` router、service 包导出、factory、`content` 下游工厂与章节内容服务已全部切到单一命名；`tests/unit/test_context_preview_service.py`、`test_context_api.py`、`test_story_bible_service.py`、`test_story_bible_api.py`、`test_chapter_content_service.py`、`test_chapter_content_api.py` 已完成适配。
- **Insights**：`story_bible` 这类已只剩 async 公共实现、同步仅作历史过渡的模块，继续保留 `Async*` 对外命名只会制造第二套真值和额外维护成本；更清晰的结构是让业务名直接代表唯一公开实现。
- **Insights**：本轮再次确认 async SQLite 回归验证必须用非沙箱执行；即便只是 `context`/`story_bible` 这类查询和事实写入接口，只要命中 `AsyncSession + aiosqlite`，沙箱挂起仍会给出假阴性结果。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_context_preview_service.py tests/unit/test_context_api.py tests/unit/test_story_bible_service.py tests/unit/test_story_bible_api.py tests/unit/test_chapter_content_service.py tests/unit/test_chapter_content_api.py` 通过，`25 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-22 | credential 单一 async 真值收口完成]
- **Events**：完成 `credential` 模块公开 async 中间态收口，并同步 `workflow runtime`、API 入口和相关测试。
- **Changes**：`credential` 公开入口已统一为 async `CredentialService` 与 `create_credential_service`；`AsyncCredentialService`、`create_async_credential_service` 与旧同步 credential service 文件已移除。
- **Changes**：`credential` router、service 包导出、factory、`workflow/service/factory.py`、`workflow_runtime_service.py`、`test_credential_api.py`、`test_credential_service.py` 已全部切到单一命名；服务单测也已改为通过 `async_db()` 适配器直接验证公开 async service。
- **Changes**：旧同步 `CredentialVerifier / HttpCredentialVerifier` 及相关导出已清理，`credential.infrastructure` 只保留 async verifier 真值，避免继续保留没有调用面的兼容层。
- **Insights**：当模块已经只剩 async 公共调用面时，继续保留同步 service/verifier 作为“也许以后会用到”的兼容层，只会制造第二套真值并放大维护成本；此时最优做法是直接删掉死代码，而不是给它改个内部名字继续留仓。
- **Insights**：`workflow runtime` 这类下游依赖不应该再直接 import 模块内部 `async_*.py` 文件；依赖应回到模块公共导出面，否则每次收口都会产生跨文件路径耦合。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_credential_service.py tests/unit/test_credential_api.py tests/unit/test_workflow_runtime.py tests/unit/test_workflow_api.py` 通过，`23 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-22 | billing 单一 async 真值收口完成]
- **Events**：完成 `billing` 模块写入/预算核算链路的公开 async 中间态收口，并同步 `workflow runtime` 与相关测试。
- **Changes**：`billing` 写入公开入口已统一为 async `BillingService` 与 `create_billing_service`；`AsyncBillingService`、`create_async_billing_service` 与旧中间态文件已移除。
- **Changes**：`workflow/service/factory.py`、`workflow_runtime_service.py`、`tests/unit/api_test_support.py`、`test_workflow_runtime.py`、`test_workflow_runtime_auto_fix.py`、`test_billing_service.py` 已全部切到单一命名；服务单测也已改为通过 `async_db()` 适配器直接验证公开 async service。
- **Insights**：`billing` 这类核心基础服务如果继续保留 `Async*` 第二命名，会直接把双真值耦进 `workflow runtime` 主链路；这类模块应优先收口，因为它们的扩散半径最大。
- **Insights**：测试辅助层和 runtime harness 必须跟着模块公共导出一起收口；否则即使业务代码已经统一，测试仍会通过对内部文件路径的硬依赖把旧结构继续固定下来。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_billing_service.py tests/unit/test_workflow_runtime.py tests/unit/test_workflow_runtime_auto_fix.py tests/unit/test_workflow_api.py` 通过，`25 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-22 | template 单一 async 真值收口完成]
- **Events**：完成 `template` 模块 builtin template sync 的公开 async 中间态收口，并同步 startup 路径与相关测试。
- **Changes**：`template` builtin sync 公开入口已统一为 async `BuiltinTemplateSyncService` 与 `create_builtin_template_sync_service`；`AsyncBuiltinTemplateSyncService`、`create_async_builtin_template_sync_service` 与旧镜像文件已移除。
- **Changes**：`app.main`、`template/service/__init__.py`、`template/__init__.py`、`template/service/factory.py`、`test_template_service.py` 已全部切到单一命名；同步版本的 builtin sync 基类也已合并，不再保留无公共调用面的第二实现。
- **Insights**：对只在 startup 和测试中使用的模块级服务，同样不能保留 `Async*` 第二命名“看起来更明确”；一旦模块公共真值只有 async 一套，业务名本身就应该直接代表这套实现。
- **Insights**：`main` startup 这类系统入口如果继续绑定旧工厂名，会把过期命名扩散到整个应用启动语义里；这类入口必须在收口时同步改掉。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_template_service.py tests/unit/test_template_api.py tests/unit/test_app_lifespan.py` 通过，`6 passed`。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `300 passed`。

## [2026-03-22 | context.engine 单一 async 真值收口完成]
- **Events**：完成 `context.engine` 的公开 async 中间态收口，并同步 `context preview`、`workflow runtime` 与 builder 测试结构。
- **Changes**：`context.engine` 公开入口已统一为 async `ContextBuilder` 与 `create_context_builder`；`AsyncContextBuilder`、`AsyncContextSourceLoader`、`create_async_context_builder` 与对应旧文件已移除。
- **Changes**：`context/service/factory.py`、`context_preview_service.py`、`workflow/service/factory.py`、`workflow_runtime_service.py`、`tests/unit/api_test_support.py`、`test_workflow_runtime.py`、`test_workflow_runtime_auto_fix.py` 已全部切到单一命名。
- **Changes**：旧的 `tests/unit/test_context_builder.py` 已拆为 `test_context_builder_loading.py`、`test_context_builder_story_bible.py`、`test_context_builder_policy.py`，并新增 `context_builder_test_support.py`，把超长测试文件压回职责清晰的小文件。
- **Insights**：`context.engine` 这类已经只剩 async 公共真值、但仍保留 `Async*` 第二命名的模块，会同时放大两类维护成本：一是下游 import 路径耦合，二是测试结构继续把过时命名固化下来；最佳收口方式是让业务名本身直接代表唯一实现。
- **Insights**：builder 层和 source loader 层收口时，最好一起做，否则会出现 `ContextBuilder` 已统一、但 `source_loader` 仍残留 `async_*` 第二文件的半收口状态；这会在后续 context 规则迭代里继续制造误导。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_context_builder_loading.py tests/unit/test_context_builder_story_bible.py tests/unit/test_context_builder_policy.py tests/unit/test_context_preview_service.py tests/unit/test_context_api.py tests/unit/test_workflow_runtime.py tests/unit/test_workflow_runtime_auto_fix.py tests/unit/test_workflow_engine.py` 通过，`38 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `301 passed`。

## [2026-03-22 | credential service 结构化拆分完成]
- **Events**：完成 `credential_service.py` 的结构化拆分，在不改变公开 API 的前提下消除超长业务文件。
- **Changes**：新增 `credential_query_support.py`、`credential_mutation_support.py`、`credential_service_support.py`；分别承载作用域/权限查询、状态切换与审计、DTO 映射与归一化 helper。
- **Changes**：`credential_service.py` 已从 491 行压到 295 行，公开入口仍然是 `CredentialService` 与 `create_credential_service`，`router` 和测试不需要改行为契约。
- **Insights**：对于已经完成 async 收口的业务模块，下一步最有价值的治理不是再改命名，而是把“公开编排”和“内部 helper”拆开；否则虽然 API 名义上统一了，文件结构仍会继续恶化。
- **Insights**：这轮也确认了一个稳定模式：查询/权限 helper、状态变更 helper、DTO 映射/归一化 helper 是最适合优先下沉的三类职责，因为它们能显著缩短主服务文件，同时不会制造新的公共真值。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_credential_service.py tests/unit/test_credential_api.py` 通过，`11 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `301 passed`。

## [2026-03-22 | export service 结构化拆分完成]
- **Events**：完成 `export_service.py` 的结构化拆分，在不改变公开 API 的前提下消除超长文件。
- **Changes**：新增 `export_file_support.py`，承载下载路径校验、导出文件写入、文件清理和文档渲染 helper。
- **Changes**：`export_service.py` 已从 304 行压到 247 行，主服务现在只保留 workflow 导出编排、章节加载校验和 owner 权限校验；`workflow runtime`、API 和测试行为契约保持不变。
- **Insights**：对于同时触及数据库和文件系统的 service，最佳拆分边界通常不是按“公开/私有方法”硬切，而是先把纯 I/O helper 拿出去；这样既能减少主服务体积，也能把事务边界和文件副作用边界分清。
- **Insights**：`resolve_download()` 这类方法如果把路径穿越校验和 owner 校验混在一起，后面最容易继续膨胀；把路径解析单独抽成 support helper 后，语义会稳定很多。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_export_service.py tests/unit/test_export_api.py` 通过，`5 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `301 passed`。

## [2026-03-22 | config_registry schema 结构化拆分完成]
- **Events**：完成 `config_schemas.py` 的结构化拆分，在不改变现有导入路径的前提下消除唯一超限的生产 schema 文件。
- **Changes**：新增 `base_schema.py`、`model_schema.py`、`field_schema.py`、`skill_agent_schema.py`、`hook_schema.py`、`workflow_schema.py`，分别承载基础 schema、模型配置、字段定义、skill/agent、hook、workflow/context/review 相关 schema。
- **Changes**：`config_schemas.py` 已从 306 行降到 54 行，当前只保留兼容聚合导出；`schemas/__init__.py` 也已补齐完整公共导出面。
- **Insights**：对 `config_registry` 这种被大量模块直接依赖的 contract 文件，最优治理方式不是立刻全仓改 import，而是先把内部职责拆开，再保留原聚合导出层做稳定过渡；这样可以同时满足结构清晰和回归风险可控。
- **Insights**：schema 文件的拆分边界应跟概念边界对齐，而不是机械按“每个类一个文件”；这次按 `base/model/field/skill_agent/hook/workflow` 分组后，依赖方向和语义都更稳定。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_config_loader.py tests/unit/test_config_validation.py tests/unit/test_review_executor.py tests/unit/test_fix_executor.py tests/unit/test_billing_service.py` 通过，`45 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `301 passed`。

## [2026-03-22 | async 语义清理完成]
- **Events**：完成 async-first 收口后的第二阶段语义治理，清理生产代码里仍制造双轨感知的 sync helper 与 `_async` 命名残留。
- **Changes**：`chapter_store.py`、`chapter_mutation_support.py`、`workflow_task_runtime_support.py` 已删除无生产调用面的 sync helper，统一回单一 async 实现；`chapter_content_service.py`、`story_asset_service.py`、`workflow_app_service.py`、`workflow_runtime_task_mixin.py` 已同步切到新命名。
- **Changes**：`workflow_app_runtime_support.py` 已将 `_dispatch_runtime_async`、`_run_persisted_workflow_async`、`_recover_runtime_failure_async` 收敛为 async-only 内部命名；`audit_log_service.py` 与 `project_deletion_support.py` 也已把 `Session | AsyncSession` 双兼容签名收紧为 `AsyncSession`。
- **Insights**：最优 async 治理不是“把全仓所有 async 字样都删掉”，也不是“看到能跑就保留双轨”；正确做法是区分边界。基础设施层的 async 类型命名是事实描述，应保留；业务内部若只剩 async 一套实现，继续保留 `_async` 或 sync/async 双轨只会制造伪双真值。
- **Insights**：判断是否该继续改的标准，不是名字里有没有 `async`，而是这个命名是否还在表达真实架构边界。`AsyncSessionFactory` 这种基础设施真值应保留，`find_next_actionable_task_async` 这种在 async-only 模块里无对应 sync 真值的 helper 则应收敛。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_story_asset_service.py tests/unit/test_chapter_content_service.py tests/unit/test_workflow_app_service.py tests/unit/test_workflow_runtime.py tests/unit/test_workflow_runtime_auto_fix.py tests/unit/test_credential_service.py tests/unit/test_project_api.py` 通过，`42 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_project_deletion_service.py` 通过，`4 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `301 passed`。

## [2026-03-22 | review/billing 异步边界收口完成]
- **Events**：完成 `ReviewExecutor` 与 `BillingService` 的结构化收口，并复核这轮 async 改造是否按“该异步的异步、该同步的同步”落地。
- **Changes**：新增 `review_executor_support.py`，承载执行失败构造、结果归一化、聚合排序与状态判定；`review_executor.py` 主文件只保留 reviewer 调度、并发控制、timeout 与 budget interruption 编排。
- **Changes**：修复了 `ReviewExecutor._execute_single()` 的计时根因问题，统一回 `perf_counter()`，避免 `loop.time()` 与 support 层 `elapsed_ms()` 混用导致的执行时长错误；同时补齐 `ReviewRunner` 类型所需的 `Any` 导入。
- **Changes**：新增 `billing_service_support.py`，承载 usage 落库、预算状态汇总、token 归一化与预算配置校验；`billing_service.py` 公开面保持单一 async `record_usage_and_check_budget()`。
- **Insights**：这轮再次确认 async 收口标准是“边界真值”，不是“名字清洗”。`ReviewExecutor`/`BillingService` 这类业务编排与 DB IO 入口必须保持 async；`normalize_usage_tokens()`、`validate_budget_config()`、review 聚合判定这类纯规则 helper 保持 sync 才是最佳边界。
- **Insights**：当前仓库里残留的 `AsyncSessionFactory`、`create_async_session_factory`、`get_async_db_session`、`AsyncCredentialVerifier` 属于基础设施事实命名，不是未完成的业务双轨；业务层公开 `Async*` 镜像类与 `create_async_*` 第二导出面在已审查范围内已基本收口。
- **Validation**：`cd apps/api && env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m ruff check app tests` 通过。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q tests/unit/test_review_executor.py tests/unit/test_billing_service.py tests/unit/test_workflow_runtime.py tests/unit/test_workflow_runtime_auto_fix.py` 通过，`26 passed`。
- **Validation**：`cd apps/api && timeout 60s env UV_CACHE_DIR=/tmp/uv-cache UV_PYTHON_INSTALL_DIR=/tmp/uv-python uv run --extra dev python -m pytest -q` 通过，当前全量结果为 `301 passed`。
