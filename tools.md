# easyStory Tools

## Concepts

- 本文件记录跨会话稳定协作知识，不替代 `docs/`、`config/` 或当前代码。
- 当前标准创作主链路：`ProjectSetting(结构化摘要) -> Outline -> OpeningPlan -> ChapterTask -> Chapter`。
- 后端实现边界固定为：`Entry -> Service -> Engine -> Infrastructure`。

## Source Lookup

- 总入口：`docs/README.md`
- 架构真值：`docs/specs/architecture.md`
- 数据边界：`docs/specs/database-design.md`
- 配置边界：`docs/specs/config-format.md`
- 当前主链路补充计划：`docs/plans/2026-03-19-pre-writing-assets.md`
- assistant 内部目录迁移路线图：`docs/plans/2026-04-07-assistant-service-package-roadmap.md`
- assistant runtime 文档重构历史记录：`docs/plans/2026-04-07-assistant-runtime-doc-refactor.md`
- assistant runtime 收尾路线历史记录：`docs/plans/2026-04-07-assistant-runtime-remaining-roadmap.md`

## Collaboration

- 文件归属：规则看 `AGENTS.md`；稳定知识写 `tools.md`；当前状态看 `memory.md`；重要历史根因查 `memory/archive/`；正式设计查 `docs/`
- 协作恢复默认先按当前已加载的 `AGENTS.md` 执行，再读项目根 `tools.md` / `memory.md`；设计细节只在需要时查 `docs/`
- 只把跨会话仍有效的信息写进本文件；不要写当天进度、Validation 通过数、一次性 TODO 或临时审查播报
- 同一条知识只保留一个主归属；已在 `docs/` 或 `AGENTS.md` 说清的内容，不再在这里展开第二份
- 深入追根因时，优先查当月归档最近相关条目，不默认整月通读

## Tools

- 后端标准验证命令：`cd apps/api && ruff check app tests && pytest -q`
- provider interop 本地探测：`cd apps/api && ./.venv/bin/python scripts/provider_interop_check.py list`
- provider interop dry-run：`cd apps/api && ./.venv/bin/python scripts/provider_interop_check.py probe <profile_id> --dry-run --show-request`
- provider interop conformance probe：`cd apps/api && ./.venv/bin/python scripts/provider_interop_check.py probe <profile_id> --probe-kind tool_call_probe`；支持 `text_probe / tool_definition_probe / tool_call_probe / tool_continuation_probe`
- 前端 support 单测命令：`pnpm --dir apps/web test:unit`
- 定向内容模块验证：`cd apps/api && pytest -q tests/unit/test_story_asset_service.py tests/unit/test_chapter_content_service.py tests/unit/test_chapter_content_api.py`
- Alembic 基线验证：`cd apps/api && ./.venv/bin/alembic -c alembic.ini upgrade head`
- 本地 SQLite 开发库损坏时的恢复命令：`cd apps/api && mv .runtime/easystory.db .runtime/easystory.db.bak-$(date +%Y%m%d-%H%M%S) && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
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
- `workflow runtime hooks` 主入口：`apps/api/app/modules/workflow/service/workflow_runtime_service.py`
- `assistant` 对话入口：`apps/api/app/modules/assistant/entry/http/router.py`
- `assistant` 运行时主入口：`apps/api/app/modules/assistant/service/assistant_service.py`
- `config_registry` agent 写回服务入口：`apps/api/app/modules/config_registry/service/agent_write_service.py`
- `config_registry` hook 写回服务入口：`apps/api/app/modules/config_registry/service/hook_write_service.py`
- `config_registry` skill 写回服务入口：`apps/api/app/modules/config_registry/service/skill_write_service.py`
- `config_registry` workflow 写回服务入口：`apps/api/app/modules/config_registry/service/workflow_write_service.py`
- provider interop 本地 profile：`apps/api/.runtime/provider-interop.local.json`
- provider interop 本地 key 文件：`apps/api/.env.provider-interop.local`
- provider interop 示例：`apps/api/provider-interop.example.json`
- provider interop 支撑模块（真实实现）：`apps/api/app/shared/runtime/llm/interop/provider_interop_support.py`；后续若扩 `tool_call_probe / tool_continuation_probe`，优先继续落在这条 shared runtime 链，不回写 assistant 业务层
- provider interop 探测脚本：`apps/api/scripts/provider_interop_check.py`
- 模型协议兼容层主入口（真实实现）：`apps/api/app/shared/runtime/llm/llm_protocol_requests.py`、`apps/api/app/shared/runtime/llm/llm_protocol_responses.py`、`apps/api/app/shared/runtime/llm/llm_stream_transport.py`、`apps/api/app/shared/runtime/llm/llm_stream_events.py`、`apps/api/app/shared/runtime/llm/llm_terminal_assembly.py`、`apps/api/app/shared/runtime/llm/llm_interop_profiles.py`；tool name 外发 alias codec 入口是 `apps/api/app/shared/runtime/llm/interop/tool_name_codec.py`，tool schema 编译入口是 `apps/api/app/shared/runtime/llm/interop/tool_schema_compiler.py`，tool call 解析入口是 `apps/api/app/shared/runtime/llm/interop/tool_call_codec.py`，continuation 投影与编码入口是 `apps/api/app/shared/runtime/llm/interop/tool_continuation_codec.py`，stream 协议归一化入口是 `apps/api/app/shared/runtime/llm/interop/stream_event_normalizer.py`，内部 dotted name 继续作为 canonical 真值
- `apps/api/app/shared/runtime/llm/interop/provider_interop_stream_support.py` 当前是共享 facade：transport / event normalizer / terminal assembly 已拆到独立模块，不要再把新逻辑堆回 facade
- MCP client 真实实现：`apps/api/app/shared/runtime/mcp/mcp_client.py`
- 插件 runtime 真实实现：`apps/api/app/shared/runtime/plugins/plugin_registry.py`、`apps/api/app/shared/runtime/plugins/plugin_providers.py`
- 当前 `apps/api/app/shared/runtime/` 根目录只保留 `__init__.py`、`errors.py`、`tool_provider.py`、`token_counter.py`、`storage_paths.py`、`template_renderer.py`
- 当前仓库内部（`apps/api/app`、`tests/unit`、`scripts`）已全部直接指向真实子域路径；新增/修改代码不得再回到旧根路径
- provider interop 显式公网 `http` 放行开关：`EASYSTORY_ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS`
- `config_registry` 管理 API 除 JWT 外，还要求 `EASYSTORY_CONFIG_ADMIN_USERNAMES` 命中当前用户名；默认空列表即全部拒绝
- 控制面轻权限当前统一口径：`EASYSTORY_CONFIG_ADMIN_USERNAMES` 命中才允许写控制面资源；现阶段包括 `config_registry` 全部接口和模板创建/更新/删除，模板读取仍只要求登录
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
- LLM 供应商兼容层当前最佳实践入口：`api_dialect` 只决定协议格式与解析；鉴权方式由 `auth_strategy` / `api_key_header_name` 显式 override，不再硬绑在 dialect 上。
- Credential Center 当前正式支持的高级连接字段：`interop_profile`、`auth_strategy`、`api_key_header_name`、`extra_headers`、`user_agent_override`、`client_name`、`client_version`、`runtime_kind`；这些字段同时作用于保存、验证和运行时请求，其中 `interop_profile` 用于显式表达协议兼容 override，不单独下沉到 assistant 业务层。
- Credential Center 当前已显式区分 `验证连接`、`验证流式工具`、`验证非流工具`；后端统一入口仍是 `POST /api/v1/credentials/{id}/verify?probe_kind=...&transport_mode=...`，不要再额外造一套产品级 probe API。
- `model_credentials` 当前的工具能力真值已按传输模式拆开：`stream_tool_verified_probe_kind + stream_tool_last_verified_at` 只代表流式工具链，`buffered_tool_verified_probe_kind + buffered_tool_last_verified_at` 只代表非流工具链；`last_verified_at` 只代表基础连接验证时间，不再承载工具能力语义。
- 工具能力 promote / failure invalidation 现在都按模式独立进行：流式 probe 只影响 `stream_tool_*`，非流 probe 只影响 `buffered_tool_*`；较低等级 probe 不能覆盖同模式下已证明的更高能力，失败也只清同模式里同级或更高的工具能力真值。
- provider conformance probe 当前正式契约：`tool_definition_probe` 只接受精确 success token；`tool_continuation_probe` 的最终回答必须携带只存在于 tool result 中的动态 echoed 值，follow-up prompt 不能直接泄漏期望答案。
- shared runtime 现在把“启用 tools 后上游返回空 assistant 响应（无文本、无 tool_calls）”统一视为明确协议错误，而不是普通中断；`LLMToolProvider` 主链和 credential verifier 的 stream probe 都会抛同一条 `空工具响应` 错误语义。
- 2026-04-08 本地实测：`ice(openai_chat_completions/gpt-5.4)` 与 `bwen(openai_responses/gpt-5.4)` 当前真实 tool probe 都失败，失败形态都是“启用工具时返回空响应”；其中 `ice` 的旧 `tool_continuation_probe` 真值已清掉，`bwen` 仍只保留 `text_probe`。不要把旧的成功验证结果继续当成当前工具能力真值。
- Gemini tool continuation / conformance probe 当前稳定口径：runtime replay 仍以“当前 prompt 在前、tool_call/tool_result replay 在后”为时序；Gemini 2.5 probe 必须显式 `thinkingBudget: 0`，且任何 probe request 调整都必须保留 `PreparedLLMHttpRequest.tool_name_aliases`，否则流式 tool call 会停留在 external alias，无法还原回 canonical dotted name。
- assistant 当前正式门控口径：只要本轮存在 visible `project.*` 工具，就按 `payload.stream` 选择门控目标；`stream=true` 要求 `stream_tool_verified_probe_kind >= tool_continuation_probe`，`stream=false` 要求 `buffered_tool_verified_probe_kind >= tool_continuation_probe`；能力不足直接显式报错，不静默隐藏工具，也不自动切换传输模式。
- 当前共享 tool schema 编译口径：外部协议默认先走 `portable_subset`，把 required-only `anyOf` 收口为描述性约束；Gemini 再叠加 `gemini_compatible`，继续移除不支持的 schema key。不要再把 schema sanitize 内联回具体 request builder。
- 当前共享 continuation 编码口径：runtime replay 文本投影、OpenAI Chat / Claude / Gemini continuation projection，以及 OpenAI Responses `function_call_output` 构造，统一走 `tool_continuation_codec.py`；不要再把 continuation helper 堆回 `llm_protocol_requests.py`。
- `model_credentials` 当前额外支持两类连接级 token 配置：`context_window_tokens` 只记录模型上下文窗口，不伪造成通用上游请求参数；`default_max_output_tokens` 会作为 runtime 的默认输出预算 fallback。
- `extra_headers` 只用于非敏感元数据头（如 Referer、租户标识）；鉴权类 header 和 `User-Agent` 不允许塞进这里，必须分别走 `auth_strategy / api_key_header_name` 和 `user_agent_override / client_name / client_version / runtime_kind`。
- 客户端预设只是帮你把一条常见 `User-Agent` 模板写入 `user_agent_override`；运行时若存在 `user_agent_override` 会优先发送它，不会再拼接下面的应用名/版本/运行环境。
- provider interop 本地 probe 若使用 `--model` 覆写，最终请求体中的探测模型也必须同步覆写，不能只改展示值。
- Anthropic Messages 请求当前默认把 `system_prompt` 编码为 text block 数组，而不是裸字符串；官方两种都允许，但兼容代理对数组更稳。
- Gemini probe 对简单连通性验证应显式压低思考配置；否则某些 `gemini-flash-latest` 代理会落到带默认 thinking 的 Gemini 3 变体，直接把 probe token 吃在内部思考上，表面看是“返回半句”，实际是上游 `finishReason=MAX_TOKENS`。
- assistant / provider interop 当前正式流式口径：`AssistantTurnRequestDTO.stream` 默认 `true`；前端若明确走 JSON 路径，必须显式发送 `stream=false`，不能依赖后端默认值。
- `ProjectSetting` 当前仍是运行时上下文投影输入之一：字段缺口只产生 `warning`，不会阻塞继续生成；但摘要一旦保存为新值，已确认的大纲 / 开篇设计 / 章节任务 / 正文仍需按 impact 标记为 stale，不能静默混用旧产物。
- `Studio` 当前已补齐项目文稿文件读写：`GET/PUT /api/v1/projects/{project_id}/documents?path=...`，文件默认落在 `apps/api/.runtime/project-documents/projects/<project_id>/documents/`；文件层现在支持 `.md + .json`，并采用“一次性默认模板 + 用户可编辑工作台”模式：默认会在新建项目时生成 `项目说明`、设定细分文稿、`数据层/*.json`、章节规划、时间轴、附录、校验、导出等空模板文件/目录，但这些模板项后续允许用户重命名、删除和扩展；正式 `大纲 / 开篇设计 / 正文章节` 继续走 `contents + content_versions` 真值链，不写入项目文件目录。`正文` 现在允许创建卷目录和章节路径占位文件；章节正文仍只通过 content 保存链更新。文稿模板只在项目创建时显式写入；读文稿/读树接口不再做隐式补模板或迁移。
- `Studio` 前端当前也已按文件类型分流：`.md` 继续走 Markdown 编辑/预览；`.json` 走 JSON 编辑/预览，其中 `数据层/人物.json`、`势力.json`、`人物关系.json`、`势力关系.json`、`隶属关系.json` 会组合成只读关系图预览，`结构定义.json`、`事件.json` 和其它 JSON 保持格式化预览，不支持手工拖线改图。数据层图预览当前只认固定 collection key 对象：`characters / factions / character_relations / faction_relations / memberships`，不再兼容裸数组或旧关系混合格式。
- incubator / studio 聊天当前不再做“流式失败自动退回非流”的静默降级；需要让真实上游错误直接暴露，便于定位中转兼容问题。
- credential verifier 当前已支持 `transport_mode=stream|buffered` 两条真实链路；设置页的工具验证必须明确携带模式，Gemini verification/probe 仍会注入最小思考配置，避免默认 thinking 吃掉验证输出预算。
- 任何会改变连接/tool contract 的凭证字段（如 `api_key / base_url / default_model / api_dialect / interop_profile / auth_strategy / api_key_header_name / extra_headers / user_agent_override / client identity`）更新后，都要同步清空 `last_verified_at + stream_tool_* + buffered_tool_*`，避免旧验证结果误穿透。
- credential verifier 当前仍发送普通短聊天提示以压低成本，但成功条件已经放宽为“拿到可用文本回复”；不再要求模型精确复读固定句子，也不在提示词里显式暴露“验证/测试”语义；只对空响应和明显的上游模型错误文本判失败。
- 受保护 API 统一走 `app.modules.user.entry.http.dependencies.get_current_user`（async 版），不保留 `get_current_user_async` 第二命名入口。
- 当业务 service 文件超出 300 行时，优先保持公开 `Service + factory` 不变，只把"查询/权限 helper""状态变更 helper""DTO 映射与归一化 helper"下沉到 `*_support.py`；不要用改公开命名来掩盖内部结构问题。
- `workflow events` SSE 端点需要 `Authorization: Bearer`；前端不要用原生 `EventSource`，统一走 `fetch + ReadableStream`，并区分正常 EOF 静默重连与错误重连提示。
- `apps/web` 当前 support 纯逻辑单测走 Node 原生 `--test` + 自定义 `scripts/ts-path-alias-loader.mjs`，这样可直接执行带 `@/` 路径别名的 TypeScript 文件而不引入额外测试框架。
- 对 query-param 驱动且带本地表单态的页面（如 Lobby Settings / Project Settings / Config Registry），统一复用 `useUnsavedChangesGuard + GuardedLink + UnsavedChangesDialog`；不要只拦本地 tab 按钮，跨页 Link 和浏览器返回也要一起拦。
- 对编辑态表单里存在“后端不会回显明文”的字段（如 credential `apiKey`）时，保存成功后不要只等 query 刷新推新 `initialState`；应立即用保存返回值重建本地 baseline 或 remount 表单，否则 dirty 会因明文字段残留长期为真。
- 对 `workflow` 维度的本地 UI 状态（如当前输入框值、已选 node execution、SSE 本地信号），优先用 `{ workflowId, value }` 绑定态再在 render 时按当前 `workflowId` 取值；不要依赖 effect 在切换后“补清空”，否则 A -> B -> A 容易复活旧状态。
- 导出口径当前已收口：`ChapterTask.status` 为 `completed | stale` 且正文状态为 `approved | stale` 时允许导出；`pending / generating / interrupted / failed` 阻断，`skipped` 直接省略，前端导出对话框必须先跑章节任务预检再发请求。
- 对"公开 async 入口 + 内部纯规则聚合"的服务（如 review/billing），最佳拆分边界：真实 I/O（并发调度、timeout、DB flush）保留 async；纯规则 helper（归一化、状态聚合、配置校验）保持 sync。
- `workflow hooks` 现已真实接入 runtime：通过 `PluginRegistry.execute` 分发 `script/webhook/agent/mcp`，默认事件覆盖 `before_node_start / before_generate / after_generate / before_review / after_review / on_review_fail / before_fix / after_fix / after_node_end / on_error`；新增 provider 继续沿这条 registry 抽象扩展，不要把类型判断塞回 runtime 主链。
- `workflow` 节点级 `hooks.before/after` 现在有 staged 校验：assistant-only 事件（如 `before_assistant_response`）不能挂到 workflow node，且 hook event 必须落在匹配的 stage（如 `after_generate -> after`）。
- `McpPluginProvider` 当前最佳实践语义：`server.enabled=false` 直接视为配置错误；上游返回 `is_error=true` 直接抛显式异常，不做“成功返回但结果里带错误”的静默降级。
- `assistant runtime` 当前已落地：`/api/v1/assistant/turn` 支持非 workflow 对话，默认可直接走“规则 + 当前会话消息历史”的纯聊天；显式传 `skill_id` 时走“规则 + Skill + 当前会话历史 + 当前消息”，其中 runtime 会自动补齐 Skill 未显式声明的 `conversation_history / user_input`；传 `agent_id` 时由 Agent 绑定 Skill；`hook` 负责生命周期，`mcp` 通过 PluginRegistry 执行；ordinary chat 的 `tool_catalog_version` 现已独立收口为“本轮最终可见 descriptor 快照版本”，不再借用 `document_context.catalog_version`；`continuation_anchor_snapshot` 现已归一化冻结 validated direct-parent digest，不再在省略 `messages_digest` 时只剩 `previous_run_id`；项目范围工具提示现已同步冻结为显式 `tool_guidance_snapshot`，prepare 会先解析 internal discovery decision，再按本轮 visible tools 收口后投影成 guidance snapshot，进入 `AssistantTurnContext / AssistantTurnRunSnapshot / AssistantTurnRun`，且当前 snapshot 会显式冻结 `discovery_source`，prompt projection / prompt render 与 `NormalizedInputItem(item_type=tool_guidance)` 共享同一份 frozen guidance 真值；`document_context` 当前已分成 `document_context_snapshot / document_context_bindings_snapshot / document_context_recovery_snapshot / document_context_injection_snapshot` 四层运行时真值，其中 latest recovery view 仍会进入 `NormalizedInputItem(item_type=document_context_recovery)`，而 prompt projection / prompt render / hook payload / run snapshot 共用同一份 `document_context_injection_snapshot`；initial prompt compaction snapshot 现已具备 `phase=initial_prompt` 与 `level=soft|hard`，其中 `soft` 表示摘要之外仍保留最近原始消息，`hard` 表示历史已完全折叠到摘要里；并额外冻结 `compressed_messages_digest + projected_messages_digest + summary_anchor_keywords + protected_document_paths + protected_document_refs + protected_document_reasons + protected_document_binding_versions + document_context_collapsed + document_context_projection_mode + projected_document_context_snapshot + document_context_recovery_snapshot`，其中 `projected_document_context_snapshot` 已与 `document_context_injection_snapshot` 对齐；`fail` 当前不写入 snapshot，而是与 continuation compaction 共用 `budget_exhausted` terminal error；`NormalizedInputItem(item_type=compacted_context)` 当前 `content` 保留摘要文本，`payload` 直接复用完整 `compaction_snapshot`；`before_assistant_response / after_assistant_response` hook payload 当前也会同步暴露 latest `request.document_context_bindings_snapshot / request.document_context_recovery_snapshot / request.document_context_injection_snapshot / request.compaction_snapshot / request.tool_guidance_snapshot / request.tool_catalog_version / request.exposed_tool_names_snapshot`；latest continuation request view 现已进入显式 `continuation_request_snapshot`，并与 `provider_continuation_state / continuation_compaction_snapshot` 分离；latest tool-loop continuation budget compaction 现已进入显式 `continuation_compaction_snapshot`，并会额外冻结 `compressed_items_digest + projected_items_digest + compacted_tool_names + compacted_document_refs + compacted_document_versions + compacted_catalog_versions`，其中 `soft` 表示仅发生 item 内部 payload trimming，`hard` 表示 top-level item 删除或 `content_items` 槽删除，`fail` 则与 initial prompt compaction 一样显式返回共享 `budget_exhausted` 终止错误；assistant 内部目录标准化当前已形成 `apps/api/app/modules/assistant/service/turn/`、`apps/api/app/modules/assistant/service/tooling/`、`apps/api/app/modules/assistant/service/context/`、`apps/api/app/modules/assistant/service/hooks_runtime/`、`apps/api/app/modules/assistant/service/rules/`、`apps/api/app/modules/assistant/service/preferences/`、`apps/api/app/modules/assistant/service/skills/`、`apps/api/app/modules/assistant/service/agents/`、`apps/api/app/modules/assistant/service/mcp/`、`apps/api/app/modules/assistant/service/hooks/` 十个稳定子域；其中 prompt render 已回收至 `service/context/assistant_prompt_render_support.py`，剩余 `assistant_service.py / factory.py / dto.py` 等继续保留为根壳；agent 通用 tool-calling 仍未实现。
- `assistant turn` 的 `messages` 当前正式只允许 `user / assistant`；规则、Skill、Agent system prompt 都属于独立装配层，不进入消息历史。
- assistant 规则层当前正式口径：`/api/v1/assistant/rules/me` 管理用户长期规则，`/api/v1/assistant/rules/projects/{project_id}` 管理项目规则；设置页当前仍只读写各自作用域的主 `AGENTS.md` 正文，但 runtime `rule bundle` 已支持主文件 frontmatter `include` 的同作用域递归展开；运行时按 `系统提示 -> 用户规则 -> 项目规则` 顺序叠加，且 include 顺序按声明顺序稳定展开；循环 include、缺失文件、越出当前作用域根目录都会显式报错；规则真值文件分别写入 `apps/api/.runtime/assistant-config/users/<user_id>/AGENTS.md` 与 `apps/api/.runtime/assistant-config/projects/<project_id>/AGENTS.md`
- assistant AI 偏好当前正式口径：`/api/v1/assistant/preferences` 管理个人默认连接/模型，`/api/v1/assistant/preferences/projects/{project_id}` 管理项目级覆盖；真值文件分别写入 `apps/api/.runtime/assistant-config/users/<user_id>/preferences.yaml` 与 `apps/api/.runtime/assistant-config/projects/<project_id>/preferences.yaml`
- assistant Skills 当前正式口径：`/api/v1/assistant/skills` 管理用户 Skill，`/api/v1/assistant/skills/projects/{project_id}` 管理项目 Skill；真值文件分别写入 `users/<user_id>/skills/<skill_id>/SKILL.md` 与 `projects/<project_id>/skills/<skill_id>/SKILL.md`，运行时按 `项目 -> 用户 -> 系统` 解析同 ID Skill
- assistant 用户 Agents 当前正式口径：`/api/v1/assistant/agents` 管理用户自己的 Agent；真值文件写入 `apps/api/.runtime/assistant-config/users/<user_id>/agents/<agent_id>/AGENT.md`，运行时优先解析用户 Agent，找不到再回退系统 Agent；用户 Agent 允许绑定已停用的用户 Skill 作为内部实现
- assistant 用户 Hooks 当前正式口径：`/api/v1/assistant/hooks` 管理用户自己的 Hook；真值文件写入 `apps/api/.runtime/assistant-config/users/<user_id>/hooks/<hook_id>/HOOK.yaml`，运行时优先解析用户 Hook，找不到再回退系统 Hook；聊天页通过 `hook_ids` 显式启用，不做全局静默注入
- assistant MCP 当前正式口径：`/api/v1/assistant/mcp-servers` 管理用户 MCP，`/api/v1/assistant/mcp-servers/projects/{project_id}` 管理项目 MCP；真值文件分别写入 `users/<user_id>/mcp_servers/<server_id>/MCP.yaml` 与 `projects/<project_id>/mcp_servers/<server_id>/MCP.yaml`，运行时按 `项目 -> 用户 -> 系统` 解析同 ID MCP
- assistant hook agent 当前也会继承用户偏好与项目规则；不要再假设只有主回复会吃到 `preferences/rules`，否则前后两次 `llm.generate` 会出现口径漂移。
- assistant 用户 Hook 的最小正式能力当前只支持两类事件：`before_assistant_response` / `after_assistant_response`；动作类型支持 `agent | mcp`。其中 agent 动作在未单独配模型时，运行时直接继承当前聊天已解析好的模型；mcp 动作通过 `server_id + tool_name + arguments + input_mapping` 调用用户或系统 MCP。
- assistant 前端 Claude 化当前口径：主路径已继续收口为“长期规则 + 当前会话 + 文稿上下文 + 模型连接”；`Skills / Agents / Hooks / MCP` 进入更明确的次级区域，并保留“可视化编辑 / 按文件编辑”双模式。当前项目设置页已补齐项目 Skills / MCP，但这些能力不再代表普通聊天的默认主链。
- Studio 聊天当前正式口径：默认就是普通对话，不再自动绑定系统内置 Skill；会话头部已支持显式 `Skill` 模式切换，区分“本次使用一次 / 当前会话持续使用”，普通对话仍只走规则 + 文稿上下文 + 当前会话历史。
- Studio 文稿树当前正式口径：只保留少量固定语义槽位 `设定 / 大纲 / 正文`，其中 DB 真值文稿 `大纲/总大纲.md`、`大纲/开篇设计.md`、`正文/第xxx章.md` 继续只读；默认模板里的 `项目说明`、设定细分文稿、`数据层/*.json`、章节规划、时间轴、附录、校验、导出等项目文稿会在新建项目时直接以空文件写入文件层，之后允许用户增删改。`数据层` JSON 仅用于结构化资料，不替代 `ProjectSetting` 或正文主真值。`正文` 现在允许新增卷目录，并通过章节路径占位文件把 DB 章节挂到对应目录下；这些占位文件不作为第二套正文真值。节点改名/删除时，会同步重映射聊天已选上下文路径；若影响当前打开文稿，还会同步更新 `doc` 路由。
- 共享 `assistant-skill-select-options` 当前默认不再自动注入系统默认聊天 Skill；只有像 Agent 编辑器这种确实需要系统 Skill 兜底的场景，调用方才显式传 `includeSystemDefault: true`。
- assistant 配置产品方向当前正式口径：面向小说创作用户时，主路径应优先收口为 `规则文件 + 当前会话 + 文稿上下文 + 模型连接`；`Skill / Agent / MCP` 属于显式增强层，不是普通聊天硬前提。作用域默认只保留 `全局(用户)` 与 `项目` 两层，项目层覆盖全局层；`Agents / Hooks` 保留为高级能力或内部能力，不作为主心智。
- 前端多用户切换账号时，退出登录必须同步清空 `workspace` 持久化里的 `lastProjectId / lastWorkflowByProject`；`sidebarPreference` 仍保留为设备级偏好。
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
- 如果后端日志长期停在 `Waiting for application startup.`，且 `healthz` 不通，优先怀疑本地 SQLite 开发库进入“`alembic_version` 表存在但没有 revision，业务表已存在”的损坏状态；这不是 WSL 端口转发问题，开发期可先备份并重建 `.runtime/easystory.db`。
- 默认沙箱内，任何命中 `aiosqlite` 的 async SQLite 验证都可能挂起；需在非沙箱环境执行，不是业务回归。
- unified exec 进程数告警是工具层会话配额问题，不是仓库代码回归。
- `provider_interop_check.py` 会复用正式 endpoint policy：公网模型端点默认要求 `https`；若确需验证公网 `http` 代理，必须显式设置 `EASYSTORY_ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS=true`，脚本不会静默绕过。
- workflow runtime 记账不能把 `raw_output.model_name` 当唯一真值；兼容代理或测试替身省略该字段时，必须回退到已解析 candidate 模型名，否则 billing 会把空模型名当配置错误直接打断运行。
- 用户提供的测试 profile 当前已验证可用口径：
  - `gpt`：`openai_responses`
  - `anthropic`：`anthropic_messages` + `system` text block array
  - `gemini`：`gemini_generate_content`
