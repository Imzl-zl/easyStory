# easyStory 项目状态

> 本文件是当前状态快照 + 最近活跃窗口，允许覆盖更新。
> 完整历史归档见 `memory/archive/`，稳定规律见 `tools.md`。

## 当前基线

- 后端测试：最近全量 `cd apps/api && ruff check app tests && pytest -q` 通过
- 前端检查：`pnpm --dir apps/web exec tsc --noEmit` + `pnpm --dir apps/web lint` 通过
- 最后更新：2026-03-23

## 已完成能力

- 凭证安全闭环 + 方言化连接（openai/anthropic/gemini，api_dialect 显式路由）
- 项目 CRUD + 删除保护（ProjectDeletionService 物理删除闭环）
- 前置创作资产生成与确认（story asset generation，setting variable resolver 支持 direct/projection/full-context）
- 工作流控制面 + runtime + auto-review/fix（WorkflowAppService / WorkflowRuntimeService）
- 章节内容与版本管理（ChapterContentService，approve 只完成当前活跃 workflow 一致的 task）
- context preview + story bible（ContextPreviewService / StoryBibleService）
- billing runtime guard + 查询面板（BillingService，时间窗口与导出路径已解耦）
- review 查询 + 面板（ReviewQueryService，compound cursor SSE）
- analysis 最小闭环（AnalysisService）
- export 服务 + 面板（ExportService，基于 workflow execution 的 chapter task 导出）
- 全链路 async-only 收口（所有模块公开面 `Service + create_*_service`）
- Web 前端基座 + Engine/Studio 工作台（含 stale 章节引导层）
- endpoint 安全策略（llm_endpoint_policy，写入 + 运行时双出口校验）
- 旧库 schema reconcile（bootstrap 自动补 api_dialect/default_model 列）
- Alembic 初始迁移基线（`apps/api/alembic/` + baseline revision + 升级校验）
- DB 初始化链 Alembic 收口（owned startup / 文件型 SQLite helper 优先走 Alembic，旧库显式 bridge + stamp）
- template 内建模板同步 + 查询 API（BuiltinTemplateSyncService / TemplateQueryService）
- observability API 闭环（workflow logs / prompt replay / audit log）
- config_registry 只读查询 API（`GET /api/v1/config/{skills|agents|hooks|workflows}`）
- config_registry skill/agent 编辑写回 API（`GET/PUT /api/v1/config/{skills|agents}/{id}`，受 config admin 白名单保护，写回前先做 staged config 校验）

## 进行中 / 未完成

- config_registry hook/workflow 编辑能力
- 前端更多页面和交互完善

## 关键决策（仍有效）

- `provider` 是渠道键/凭证解析键，协议由 `api_dialect` 决定，模型缺省由 `default_model` 决定
- 投影视图（character_profile/world_setting）由 `project` 边界统一提供，不在 context/content 各自维护
- stale chapter task 必须先重建章节计划，不可直接编辑；前后端同步强制
- endpoint 安全策略必须同时落在写入入口和运行时出口
- 正式 schema 演进入口已切到 `apps/api/alembic/`；startup 和文件型 SQLite 测试库优先走 Alembic，pre-Alembic 旧库通过 `create_all + reconcile + stamp` 显式桥接接入
- 程序化 Alembic 需要命中现有 memory SQLite 或带密码 URL 时，优先复用现有 `connection/engine`，不要退回字符串化 URL
- service 文件超 300 行时，拆 `*_support.py`（查询/权限、状态变更、DTO 映射三类 helper）
- config_registry 首轮管理 API 只暴露 summary DTO，不把 skill prompt / agent system_prompt 直接放进列表查询响应
- config_registry detail/update API 对外优先暴露语义化字段名（如 `agent_type`、`skill_ids`），不要把 YAML alias 直接透传给前端
- config_registry skill 写回必须先在临时复制的 `config/` 根目录做完整 `ConfigLoader` 校验，确认通过后再替换真实 YAML
- config_registry 管理 API 必须走显式 `EASYSTORY_CONFIG_ADMIN_USERNAMES` 白名单；默认空列表拒绝全部访问

## 仍需注意的坑点

- aiosqlite 沙箱挂起不是业务回归（0.21.0 / 0.22.1 非沙箱都正常）
- unified exec 进程数告警是工具层会话配额问题，不是仓库代码回归
- workflow_snapshot 恢复需剥离运行时扩展字段，否则 WorkflowConfig extra key 校验失败
- PromptReplay.response_text 是文本列，结构化 LLM 响应需先 JSON 序列化再落库
- DB 事务 + 文件系统副作用：先 commit 再做不可回滚的文件删除
- async 语义审查不要误把基础设施命名（AsyncSessionFactory 等）当待清理对象
- shared/runtime 改为惰性导出，避免 settings -> runtime -> llm tool provider 循环导入

## 最近活跃窗口（2026-03-22 ~ 03-23）

- 完成模型连接方言化改造：LLMToolProvider 通过 llm_protocol 层直接支持 4 类 API 方言
- 完成方言化审查修复：base_url 安全边界、旧库 schema 升级、credential 更新语义收口
- 完成 review follow-up：setting variable resolver 统一、Engine keyed remount、Studio stale CTA 竞态修复
- 移除 LiteLLM 依赖，pyproject.toml / uv.lock 已同步
- 建立 Alembic 初始迁移基线，并验证 upgrade head 与当前 ORM metadata 对齐
- 完成 DB 初始化链 Alembic 收口：owned startup 与文件型 SQLite 测试库已优先走 Alembic，旧库保留 bridge + stamp 接入路径
- 完成 DB 初始化链审查 follow-up：修复 masked DB URL 与 memory SQLite 第二 engine 回归，定向回归提升到 13 通过
- 完成 config_registry 只读查询闭环：新增 query service、`/api/v1/config/*` 受保护端点与定向回归
- 完成 config_registry skill 编辑写回闭环：新增 skill detail/update API、staged config 校验与失败不落盘回归
- 完成 config_registry / Alembic 审查修复：补齐 config admin 授权、staged 校验 422、全局 ID 唯一性与 async sqlite 判定
- 完成 config_registry agent 编辑写回闭环：新增 agent detail/update API、语义化 DTO 映射与 staged 回归
