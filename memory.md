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
