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
