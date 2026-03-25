# easyStory Tools

## Concepts

- 本文件记录跨会话稳定协作知识，不替代 `docs/`、`config/` 或当前代码。
- 当前标准创作主链路：`ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter`。
- 后端实现边界固定为：`Entry -> Service -> Engine -> Infrastructure`。

## Source Lookup

- 总入口：`docs/README.md`
- 架构真值：`docs/specs/architecture.md`
- 数据边界：`docs/specs/database-design.md`
- 配置边界：`docs/specs/config-format.md`
- 当前主链路补充计划：`docs/plans/2026-03-19-pre-writing-assets.md`

## Collaboration

- 文件归属：规则看 `AGENTS.md`；稳定知识写 `tools.md`；当前状态看 `memory.md`；重要历史根因查 `memory/archive/`；正式设计查 `docs/`
- 协作恢复默认先按当前已加载的 `AGENTS.md` 执行，再读项目根 `tools.md` / `memory.md`；设计细节只在需要时查 `docs/`
- 只把跨会话仍有效的信息写进本文件；不要写当天进度、Validation 通过数、一次性 TODO 或临时审查播报
- 同一条知识只保留一个主归属；已在 `docs/` 或 `AGENTS.md` 说清的内容，不再在这里展开第二份
- 深入追根因时，优先查当月归档最近相关条目，不默认整月通读

## Tools

- 后端标准验证命令：`cd apps/api && ruff check app tests && pytest -q`
- 定向内容模块验证：`cd apps/api && pytest -q tests/unit/test_story_asset_service.py tests/unit/test_chapter_content_service.py tests/unit/test_chapter_content_api.py`
- Alembic 基线验证：`cd apps/api && ./.venv/bin/alembic -c alembic.ini upgrade head`
- 项目共享 skills 目录：`.codex/skills/`
- 已安装项目共享 skills：
  - `react-best-practices`：用于 `apps/web` 的 React / Next.js 组件、状态、渲染与性能实践
  - `composition-patterns`：用于组件 API 设计、组合式结构和复杂 UI 拆分
  - `web-design-guidelines`：用于页面布局、信息层级和视觉设计任务
  - `code-review-expert`：用于代码审查任务，优先找 bug、回归风险和缺失验证
  - `supabase-postgres-best-practices`：用于 PostgreSQL 约束、索引、锁和查询模式审查；只借鉴 Postgres 实践，不引入 Supabase 产品绑定
- 根 API 路由装配：`apps/api/app/entry/http/router.py`
- `config_registry` 路由入口：`apps/api/app/modules/config_registry/entry/http/router.py`
- `content` 路由入口：`apps/api/app/modules/content/entry/http/router.py`
- `workflow` 路由入口：`apps/api/app/modules/workflow/entry/http/router.py`
- `content` 章节服务入口：`apps/api/app/modules/content/service/chapter_content_service.py`
- `workflow` 控制面服务入口：`apps/api/app/modules/workflow/service/workflow_app_service.py`
- `config_registry` agent 写回服务入口：`apps/api/app/modules/config_registry/service/agent_write_service.py`
- `config_registry` hook 写回服务入口：`apps/api/app/modules/config_registry/service/hook_write_service.py`
- `config_registry` skill 写回服务入口：`apps/api/app/modules/config_registry/service/skill_write_service.py`
- `config_registry` workflow 写回服务入口：`apps/api/app/modules/config_registry/service/workflow_write_service.py`
- `config_registry` 管理 API 除 JWT 外，还要求 `EASYSTORY_CONFIG_ADMIN_USERNAMES` 命中当前用户名；默认空列表即全部拒绝
- `create_app()` 当前对外部注入的 `async_session_factory` 只挂载到 `app.state` 并继续执行 settings/template startup；只有内部自行创建 session factory 时才负责启动期建库，并通过 `initialize_async_database()` 走 Alembic。测试若需要同步 seed，会在 app 外部单独创建 sync `session_factory`
- 文件型 SQLite 测试 helper `build_sqlite_session_factories()` 已改为先调用 `initialize_database(sync_url)`；正式 schema 真值与测试建库入口保持一致
- 程序化 Alembic 若需要命中 memory SQLite 或避免 URL 掩码/二次建库问题，应优先复用现有 `connection`（`Config.attributes["connection"]`），不要只传 `sqlalchemy.url`

## Patterns

- 先查正式设计真值，再补协作知识；不要反过来。
- 先沿主链路实施，不要并行散做全部模块。
- 涉及正文、前置资产、章节版本时，统一通过 `content` 模块公开服务，不把正文真值落到 `artifacts`。
- `workflow` 只做编排、状态机、恢复与执行记录；内容规则、审核规则、导出规则分别回对应模块。
- 新实现优先补服务和测试，再接路由；保持 API 只做装配，不直接写业务规则。
- 所有业务模块公开面已收敛为 async-only：统一 `Service + create_*_service` 命名，不保留 `Async*` 镜像类或 `create_async_*` 第二导出面。内部若只剩 async 一套实现，把 `*_async` 名称改回业务语义名。
- 受保护 API 统一走 `app.modules.user.entry.http.dependencies.get_current_user`（async 版），不保留 `get_current_user_async` 第二命名入口。
- 当业务 service 文件超出 300 行时，优先保持公开 `Service + factory` 不变，只把"查询/权限 helper""状态变更 helper""DTO 映射与归一化 helper"下沉到 `*_support.py`；不要用改公开命名来掩盖内部结构问题。
- `workflow events` SSE 端点需要 `Authorization: Bearer`；前端不要用原生 `EventSource`，统一走 `fetch + ReadableStream`，并区分正常 EOF 静默重连与错误重连提示。
- 导出口径当前已收口：`ChapterTask.status` 为 `completed | stale` 且正文状态为 `approved | stale` 时允许导出；`pending / generating / interrupted / failed` 阻断，`skipped` 直接省略，前端导出对话框必须先跑章节任务预检再发请求。
- 对"公开 async 入口 + 内部纯规则聚合"的服务（如 review/billing），最佳拆分边界：真实 I/O（并发调度、timeout、DB flush）保留 async；纯规则 helper（归一化、状态聚合、配置校验）保持 sync。
- 读取 `request.app.state`、容器字段或内存注入对象的 accessor，如果不做 I/O 就保持同步 `def`；不为"全 async"把纯 accessor 改成 coroutine。
- async 语义审查时，不要误把基础设施事实命名当成待清理对象；`AsyncSessionFactory`、`create_async_session_factory`、`get_async_db_session`、`AsyncCredentialVerifier` 是真实底层边界，应保留。
- 对混合 DB 编排和文件 I/O 的服务（如 export），优先把路径校验、文件写入/清理、文档渲染抽到 `*_support.py`；主服务只保留 owner 校验、装配和事务边界。
- 对被大量模块直接导入的 schema/contract 文件（如 config_registry），优先按职责拆子文件，保留原聚合文件作为兼容导出层；不为压行数立刻做全仓 import 路径迁移。
- `config_registry` 首轮管理 API 先做只读 summary DTO；`prompt` / `system_prompt` 等重字段不通过列表接口直出，写回 YAML 后置到独立闭环。
- `config_registry` agent detail/update 已补齐：API 对外字段保持 `agent_type` / `skill_ids` 语义，内部再映射回 YAML `type` / `skills`
- `config_registry` hook detail/update 已补齐：API 对外使用 `action.action_type`，内部再映射回 YAML `action.type`
- `config_registry` workflow detail/update 已补齐：API 对外使用 `node_type` / `skill_id` / `reviewer_ids` / `fix_skill_id` / `inject_type` 语义，内部再映射回 YAML `type` / `skill` / `reviewers` / `fix_skill` / `type`
- `config_registry` detail/update DTO 现统一基于 strict DTO：未知字段直接失败，不再静默忽略 extra keys
- `config_registry` skill 写回已补齐：先在临时复制的 `config/` 根目录完成整仓 `ConfigLoader` 校验，再原子替换真实 YAML；失败时不污染目标文件。
- staged skill 校验失败属于客户端输入问题，当前统一返回 `422 business_rule_error`，不再走 `ConfigurationError -> 500`
- `config_registry` 的 `build_*_config()` 现统一把 schema `ValidationError` 收口成 `422 business_rule_error`；例如 reviewer agent 非法 `output_schema`、generate node 缺 skill、hook action config 非法
- `template` 自定义模板写入只接收语义字段（`name/description/genre/workflow_id/guided_questions`）；`template_nodes` 必须由后端根据 `workflow_id` 自动展开，不能让前端提交第二份节点真值。built-in 模板保持只读，模板名称全局唯一，避免与 built-in 同名后被同步逻辑误吸收。
- `project incubator` draft 能力归属 `project` 模块：模板只提供题材和引导问题快照，`ProjectSetting` 草稿由 `project` 服务生成；已声明但未支持映射的变量返回 `unmapped_answers`，未声明变量或空白回答直接 `422 business_rule_error`
- `template.guided_questions.variable` 现在在模板边界做规范化存储；`core_conflict` 是规范字段名，历史 `conflict` 会显式归一化到 `core_conflict`
- `quick template` 一键建项目应继续归属 `project incubator` 编排层：先生成 `ProjectSetting` 草稿，再复用 `ProjectManagementService.create_project()` 持久化；不要复制项目创建与前置资产 scaffold 逻辑
- incubator 响应现在直接返回 `setting_completeness`，并复用 `project` 模块既有完整度规则；当前内建模板问题集仍不足以直接达到 `ready`
- `free-text setting` draft 也继续归属 `project incubator`：请求必须显式传 `provider`，可选传 `model_name`；自由文本先通过 `skill.project_setting.conversation_extract` 提取成 `ProjectSetting` 草稿，再复用 `evaluate_project_setting()` 生成 `setting_completeness` 与 `follow_up_questions`；skill 配置只保留生成参数，不锁死 provider/model，预创建阶段也不走 system credential pool

## Pitfalls

- `tools.md` / `memory.md` 发生冲突时，以正式设计、配置和当前代码为准。
- 外部安装的 project skills 只作为协作增强，不覆盖 `AGENTS.md`、`docs/`、`config/` 与当前代码真值。
- `.serena` 里的旧 memory 可能滞后于磁盘当前状态；实现判断以当前仓库文件为准。
- 涉及 DB 事务和文件系统副作用的删除/导出逻辑时，先完成 `commit`，再做不可回滚的文件删除或落盘清理；否则一旦事务失败，就会制造"数据库已回滚、文件却已经删掉"的双真值。
- 当前项目不是"只有 docs 的空仓库"，`apps/api` 已有实装代码和通过的测试基线。
- Alembic CLI 若不显式覆盖 `sqlalchemy.url`，默认会命中 `apps/api/.runtime/easystory.db`；做 baseline/autogenerate/临时验证时要用 `-x database_url=...` 或在 Config 里显式覆盖。
- 默认沙箱内，任何命中 `aiosqlite` 的 async SQLite 验证都可能挂起；需在非沙箱环境执行，不是业务回归。
- unified exec 进程数告警是工具层会话配额问题，不是仓库代码回归。
