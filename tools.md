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
- `create_app()` 当前对外部注入的 `async_session_factory` 只挂载到 `app.state` 并继续执行 settings/template startup；只有内部自行创建 session factory 时才负责启动期建库。测试若需要同步 seed，会在 app 外部单独创建 sync `session_factory`

## Patterns

- 先查正式设计真值，再补协作知识；不要反过来。
- 先沿主链路实施，不要并行散做全部模块。
- 涉及正文、前置资产、章节版本时，统一通过 `content` 模块公开服务，不把正文真值落到 `artifacts`。
- `workflow` 只做编排、状态机、恢复与执行记录；内容规则、审核规则、导出规则分别回对应模块。
- 新实现优先补服务和测试，再接路由；保持 API 只做装配，不直接写业务规则。
- 后端当前正式入口已收敛到 async-first；同步 service 若还存在，只允许作为内部复用或测试过渡，不再从模块公共入口导出。
- 查询/分析型 service 包若已完成 async 迁移，应直接收敛为单一 async `Service + create_*_service` 命名，不再保留 `Async*` 镜像类与 `create_async_*` 第二导出面。
- 当模块公共面已经 async-only 后，内部 helper 也应继续收敛语义：没有生产调用面的 sync helper 直接删除；若只剩 async 一套实现，就把 `*_async` 名称改回业务语义名，避免继续保留假双轨。
- `workflow` 控制面当前也已按同样规则收敛：公开入口是 `WorkflowAppService / ChapterTaskService` 与 `create_workflow_app_service / create_chapter_task_service`，不再暴露 `Async*` 命名。
- `content` 当前也已按同样规则收敛：公开入口是 `StoryAssetService / ChapterContentService` 与 `create_story_asset_service / create_chapter_content_service`，不再暴露 `Async*` 命名。
- `context` 当前也已按同样规则收敛：公开入口是 `ContextPreviewService / StoryBibleService` 与 `create_context_preview_service / create_story_bible_service`，不再暴露 `Async*` 命名。
- `context.engine` 当前也已按同样规则收敛：公开入口是 async `ContextBuilder` 与 `create_context_builder`；`workflow runtime`、`context preview` 与测试辅助不再直接 import `async_context_builder.py` / `async_source_loader.py`。
- `credential` 当前也已按同样规则收敛：公开入口是 `CredentialService` 与 `create_credential_service`；旧同步 credential service 与同步 HTTP verifier 已清理，不再保留无调用面的兼容层。
- `billing` 当前也已按同样规则收敛：写入/预算核算公开入口是 `BillingService` 与 `create_billing_service`；`workflow runtime` 与测试辅助应只依赖模块公共导出，不再直接 import `async_billing_service.py`。
- `template` 当前也已按同样规则收敛：builtin template sync 公开入口是 `BuiltinTemplateSyncService` 与 `create_builtin_template_sync_service`；`main` startup 不再依赖 `Async*` 第二命名入口。
- 受保护 API 当前统一走 `app.modules.user.entry.http.dependencies.get_current_user`；该依赖已经是 async 版，不再保留 `get_current_user_async` 第二命名入口。
- 当业务 service 文件超出 300 行时，优先保持公开 `Service + factory` 不变，只把“查询/权限 helper”“状态变更 helper”“DTO 映射与归一化 helper”下沉到 `*_support.py`；不要用改公开命名来掩盖内部结构问题。
- 对 `review` / `billing` 这类“公开 async 入口 + 内部纯规则聚合”的服务，最佳拆分边界是：并发调度、timeout、DB flush、预算查询这类真实 I/O 继续保留 async；结果归一化、执行失败构造、状态聚合、配置校验、token 归一化这类纯规则 helper 保持 sync。
- 读取 `request.app.state`、容器字段或内存注入对象的 accessor，如果本身不做 I/O，就保持同步 `def`；不要为了“全 async”把纯 accessor 改成 async coroutine，否则 direct call 和依赖注入都会变得更脆弱。
- async 语义审查时，不要误把基础设施事实命名当成待清理对象；`AsyncSessionFactory`、`create_async_session_factory`、`get_async_db_session`、`AsyncCredentialVerifier` 这类名称是在表达真实底层边界，应保留。
- 对 `export` 这类混合 DB 编排和文件 I/O 的服务，优先把“下载路径校验”“文件写入/清理”“文档渲染”抽到 `*_support.py`；主服务只保留 owner 校验、章节装配和事务边界。
- 对 `config_registry` 这类被大量模块直接导入的 schema/contract 文件，优先按职责拆子文件，并保留原聚合文件作为兼容导出层；不要为了压行数立刻做全仓 import 路径迁移。

## Pitfalls

- `memory.md` 只追加，不覆盖。
- `tools.md` / `memory.md` 发生冲突时，以正式设计、配置和当前代码为准。
- 外部安装的 project skills 只作为协作增强，不覆盖 `AGENTS.md`、`docs/`、`config/` 与当前代码真值。
- `.serena` 里的旧 memory 可能滞后于磁盘当前状态；实现判断以当前仓库文件为准。
- 工作区当前是脏的，包含用户已有未提交改动和本轮实现改动；不要回滚不属于当前任务的文件。
- 涉及 DB 事务和文件系统副作用的删除/导出逻辑时，先完成 `commit`，再做不可回滚的文件删除或落盘清理；否则一旦事务失败，就会制造“数据库已回滚、文件却已经删掉”的双真值。
- 当前项目不是“只有 docs 的空仓库”，`apps/api` 已有实装代码和通过的测试基线。
- 默认沙箱内，任何命中 `aiosqlite` 的 async SQLite 验证都可能挂起；`test_app_lifespan.py`、async API 测试和后端全量 `pytest` 需要在非沙箱环境执行，否则容易误判成业务回归。
- 这类挂起当前已确认不是 `aiosqlite` 版本回归：`0.21.0` 与 `0.22.1` 在非沙箱环境都能正常 `connect(':memory:')`；不要再为此引入不必要的依赖降级。
- unified exec 进程数告警是工具层会话配额问题，不是仓库代码回归；优先复用现有测试会话，不要把它误判成后端 bug。
