# easyStory Tools

## Concepts

- 本文件记录项目协作知识，不替代 `docs/specs`、`docs/design`、`docs/plans`、`config` 或当前代码。
- 正式真值优先级：`docs/specs/architecture.md` > `docs/specs/database-design.md` > `docs/specs/config-format.md` > `docs/design/*.md` > `docs/plans/*.md` > 本文件。
- 当前标准创作主链路：`ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter`。
- 后端实现边界固定为：`Entry -> Service -> Engine -> Infrastructure`。

## Read First

- 总入口：`docs/README.md`
- 架构真值：`docs/specs/architecture.md`
- 数据边界：`docs/specs/database-design.md`
- 配置边界：`docs/specs/config-format.md`
- 当前主链路补充计划：`docs/plans/2026-03-19-pre-writing-assets.md`

## Tools

- 后端标准验证命令：`cd apps/api && ruff check app tests && pytest -q`
- 定向内容模块验证：`cd apps/api && pytest -q tests/unit/test_story_asset_service.py tests/unit/test_chapter_content_service.py tests/unit/test_chapter_content_api.py`
- 项目共享 skills 目录：`.codex/skills/`
- 已安装项目共享 skills：
  - `react-best-practices`：用于 `apps/web` 的 React / Next.js 组件、状态、渲染与性能实践
  - `composition-patterns`：用于组件 API 设计、组合式结构和复杂 UI 拆分
  - `web-design-guidelines`：用于页面布局、信息层级和视觉设计任务
  - `code-review-expert`：用于代码审查任务，优先找 bug、回归风险和缺失验证
  - `supabase-postgres-best-practices`：用于 PostgreSQL 约束、索引、锁和查询模式审查；只借鉴 Postgres 实践，不引入 Supabase 产品绑定
- 根 API 路由装配：`apps/api/app/entry/http/router.py`
- `content` 路由入口：`apps/api/app/modules/content/entry/http/router.py`
- `workflow` 路由入口：`apps/api/app/modules/workflow/entry/http/router.py`
- `content` 章节服务入口：`apps/api/app/modules/content/service/chapter_content_service.py`
- `workflow` 控制面服务入口：`apps/api/app/modules/workflow/service/workflow_app_service.py`

## Patterns

- 先查正式设计真值，再补协作知识；不要反过来。
- 先沿主链路实施，不要并行散做全部模块。
- 涉及正文、前置资产、章节版本时，统一通过 `content` 模块公开服务，不把正文真值落到 `artifacts`。
- `workflow` 只做编排、状态机、恢复与执行记录；内容规则、审核规则、导出规则分别回对应模块。
- 新实现优先补服务和测试，再接路由；保持 API 只做装配，不直接写业务规则。

## Pitfalls

- `memory.md` 只追加，不覆盖。
- `tools.md` / `memory.md` 发生冲突时，以正式设计、配置和当前代码为准。
- 外部安装的 project skills 只作为协作增强，不覆盖 `AGENTS.md`、`docs/`、`config/` 与当前代码真值。
- `.serena` 里的旧 memory 可能滞后于磁盘当前状态；实现判断以当前仓库文件为准。
- 工作区当前是脏的，包含用户已有未提交改动和本轮实现改动；不要回滚不属于当前任务的文件。
- 当前项目不是“只有 docs 的空仓库”，`apps/api` 已有实装代码和通过的测试基线。
