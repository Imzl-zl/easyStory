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
- template 自定义模板管理 API（create/update/delete，自定义模板按 workflow_id 自动生成 template_nodes，built-in 只读保护）
- project incubator draft API（基于 template + guided answers 生成非持久化 `ProjectSetting` 初稿，显式返回 applied/unmapped answers）
- project incubator create-project API（基于 template + guided answers 一键创建项目，返回 project + applied/unmapped answers）
- incubator 前移完整度检查（draft/create 响应直接返回 `setting_completeness`）
- project incubator 自由对话 draft API（请求显式 provider、可选 model_name；自由文本提取为结构化 `ProjectSetting` 草稿，并返回完整度与追问建议）
- observability API 闭环（workflow logs / prompt replay / audit log）
- config_registry 只读查询 API（`GET /api/v1/config/{skills|agents|hooks|workflows}`）
- config_registry skill/agent/hook/workflow 编辑写回 API（`GET/PUT /api/v1/config/{skills|agents|hooks|workflows}/{id}`，受 config admin 白名单保护，写回前先做 staged config 校验）

## 进行中 / 未完成

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
- config_registry hook detail/update API 对外使用 `action.action_type`，不要把 `action.type` 直接透传给前端
- config_registry workflow detail/update API 对外使用 `node_type`、`skill_id`、`reviewer_ids`、`fix_skill_id`、`inject_type`，不要把 YAML alias 直接透传给前端
- config_registry detail/update DTO 必须严格拒绝未知字段，不能静默忽略 extra keys
- config_registry skill 写回必须先在临时复制的 `config/` 根目录做完整 `ConfigLoader` 校验，确认通过后再替换真实 YAML
- config_registry `build_*_config()` 产生的 schema `ValidationError` 必须转成 `422 business_rule_error`，不能泄漏为 500
- config_registry 管理 API 必须走显式 `EASYSTORY_CONFIG_ADMIN_USERNAMES` 白名单；默认空列表拒绝全部访问
- template 写入 API 只接收语义字段，`template_nodes` 必须由后端按 `workflow_id` 自动展开；built-in 模板保持只读，且模板名称全局唯一，避免与 built-in 同名后被同步逻辑误吸收
- project incubator draft 只生成 `ProjectSetting` 草稿，不直接创建项目；模板未声明变量、空白回答直接失败，已声明但未映射变量必须显式出现在 `unmapped_answers`
- template guided question 变量在模板边界统一规范化；`core_conflict` 为规范名，历史 `conflict` 兼容收口到同一真值
- quick template 一键建项目必须先经 incubator 映射得到 `ProjectSetting`，再复用普通项目创建逻辑；不单独复制项目落库与前置资产 scaffold
- incubator 的完整度结果必须复用 `project` 现有规则；当前内建模板只覆盖最少问题集，因此默认通常仍是 `blocked`
- 自由文本设定草稿继续归属 `project incubator`；请求必须显式给出 provider、可选给出 model_name，skill 不锁死 provider/model；LLM 只输出 `ProjectSetting` schema，追问列表由完整度结果派生，预创建阶段不走 system credential pool

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
- 完成 config_registry hook 编辑写回闭环：新增 hook detail/update API、`action_type` 语义映射与 staged 回归
- 完成 config_registry workflow 编辑写回闭环：新增 workflow detail/update API、语义化 DTO 映射与 staged 回归
- 完成 config_registry 输入校验修复：DTO 改为 strict extra-forbid，schema `ValidationError` 统一收口为 `422 business_rule_error`
- 完成 template 自定义模板管理闭环：新增 create/update/delete API，自定义模板按 workflow 自动生成节点快照，built-in 只读与重名冲突保护已补齐
- 完成 project incubator draft 闭环：新增基于 template 的 `ProjectSetting` 草稿 API，显式区分 applied/unmapped answers，定向回归 7 通过
- 完成 template/incubator 契约修复：guided question 变量改为规范化存储，`conflict` 与空白变量问题已收口，template+incubator 定向回归 19 通过
- 完成 quick template 一键建项目闭环：新增 incubator create-project API，复用普通项目创建逻辑，project/incubator 定向回归 19 通过
- 完成 incubator 完整度前移：draft/create 响应直接返回 `setting_completeness`，并补齐 `blocked/warning/ready` 语义回归
- 完成 project incubator 自由对话 draft 闭环：新增 conversation draft API、`skill.project_setting.conversation_extract` 与追问派生逻辑，定向回归 31 通过
- 完成 conversation draft 审查修复：请求改为显式 `provider` + 可选 `model_name`，`conversation_text` 增加上限，定向回归 32 通过
