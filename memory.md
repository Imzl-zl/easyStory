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
