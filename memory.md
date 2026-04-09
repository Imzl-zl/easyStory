# easyStory 项目状态
> 本文件是当前状态快照 + 最近活跃窗口，允许覆盖更新；完整历史归档见 `memory/archive/`，稳定规律见 `tools.md`。

## 当前基线

- 后端测试：最近一次已知全量 `cd apps/api && ruff check app tests && pytest -q` 通过（记录日期：2026-03-23）
- 前端检查：最近一次已知 `pnpm --dir apps/web lint` + `pnpm --dir apps/web test:unit` 通过（记录日期：2026-04-04）
- 最后更新：2026-04-09
## 已完成能力

- 凭证与模型连接闭环：安全存储、endpoint policy、`api_dialect` 路由、`interop_profile` / auth strategy override、公网 http 显式测试开关、本地 provider interop probe、旧库 schema reconcile，以及连接级 `context_window_tokens / default_max_output_tokens`
- provider interop conformance probe 第二阶段已落地：shared runtime 现已支持 `text_probe / tool_definition_probe / tool_call_probe / tool_continuation_probe`，`provider_interop_check.py` 已新增 `--probe-kind`；当前 dry-run 正常，但真实 `gpt` profile 的 tool probes 仍显式暴露上游 `HTTP 502 / output=[]`，说明 profile 本身的 tool contract 还不稳定
- provider interop 深化闭环：本地 probe 已支持 `prompt/system_prompt/extra_headers/stream`，并与真实运行链共用同一请求 builder；Gemini 不再做 probe-only `thinkingConfig` 特判，避免验证链和运行链静态漂移
- verification / tool conformance probe 预算当前已显式抬高：连接验证 `max_output_tokens` 从 32 提到 256，tool conformance probe 从 128 提到 256，tool probe 超时从 5 秒提到 30 秒；修复目标是减少 reasoning 模型把默认思考预算或首 token 延迟误判成“渠道不兼容”
- assistant / provider interop 流式口径已收口：assistant turn 后端默认 `stream=true`，前端非流 JSON 调用显式传 `stream=false`；credential verifier 与 provider interop probe 默认走流式；incubator / studio 聊天已移除“流式失败自动退回非流”；模型工具调用现已在 shared runtime 引入 canonical dotted name -> external safe alias 边界，以及共享 `tool_schema_compiler / tool_call_codec / tool_continuation_codec / stream_event_normalizer`，避免 OpenAI-compatible tool name / schema / tool call parse / continuation / stream parse 漂移再次打断 assistant tool loop
- Credential Center 高级兼容设置与能力真值闭环：凭证现正式支持 `interop_profile / auth_strategy / api_key_header_name / extra_headers`，工具能力真值已按传输模式拆成 `stream_tool_* / buffered_tool_*`，且保存、验证、assistant runtime 与前端配置入口已对齐；其中 `extra_headers` 已收口为仅允许非敏感元数据头，`interop_profile` 已按 `api_dialect` 做显式约束
- Credential Center 显式验证语义与 assistant 门控已收口：产品面现已区分 `验证连接(text_probe)`、`验证流式工具(tool_continuation_probe + stream)`、`验证非流工具(tool_continuation_probe + buffered)`；共享 verifier 已复用 conformance probe 主链，assistant 在 visible `project.*` 工具存在时会按本轮 `stream` 模式显式要求对应的工具能力真值，避免再出现“流式验证通过但非流 tool loop 实际不可用”的单一 verify 假象
- 2026-04-08 review remediation 已完成：`tool_definition_probe` 现仅接受精确 success token；`tool_continuation_probe` follow-up 改为校验只存在于 tool result 中的动态 echoed 值，不再把期望答案写进 prompt；同模式下的工具能力写回已改为数据库当前值参与的原子 promote，避免并发低等级验证覆盖高等级 capability 真值
- 2026-04-09 继续收口了工具能力真值与传输模式语义：若显式工具验证失败，只会清掉对应模式里同级或更高的工具能力真值；shared runtime 与 verifier 现已明确区分流式 / 非流工具链，并把“工具验证通过”改成带模式的能力结论。任何成功/失败验证现在都会清空 legacy `verified_probe_kind`，避免启动 reconcile 再从旧字段回灌流式能力；`openai_responses` 非流解析也只在 `output_text` 非空时才允许 `output=[]`，空字符串不再被静默放过。最新本地实测：`Gemini` 的流式和非流工具链都可用，而两条 OpenAI-compatible 连接在非流工具路径上仍会显式暴露上游空响应 / `output=[]`。
- 项目与前置资产闭环：project CRUD、结构化摘要提示（原 setting completeness）、story asset generation / confirm
- 内容主链路闭环：outline / opening_plan / chapter / content version、章节确认与 stale 传播
- 工作流闭环：control plane、runtime、auto-review / fix、workflow logs / prompt replay / audit
- workflow hooks runtime 闭环：`script/webhook/agent` 已真实接入 workflow runtime，`PluginRegistry` 支持 execute/timeout，hook agent 依赖已进入 snapshot，builtin `auto_save_content` 可执行
- assistant runtime 第一阶段闭环：新增 `/api/v1/assistant/turn`，非 workflow 对话已支持 skill prompt、hook 生命周期与 `mcp` 插件调用；workflow snapshot 已可冻结 `resolved_mcp_servers`
- assistant 原生 tool-calling runtime `v1A` 已闭环：ordinary chat 现已支持本地 `project.read_documents / project.write_document` tool loop、`AssistantTurnRun / AssistantToolStep` 真值、structured continuation replay、recoverable tool error 回填、SSE `run_started / tool_call_start / tool_call_result / completed` 与真实 `state_version`；assistant 主链相关后端回归 `54 passed`，前端 assistant stream 定向测试已通过
- assistant stale-running-turn 恢复语义已补齐：`AssistantTurnRun` 现会记录本地 runtime claim（`host / pid / instance_id`）；若旧进程已中断导致残留 `running` run，runtime 会把该 run 显式终止为失败态，不再让同一 `client_turn_id` 永久卡在 `run_in_progress`，且不会静默重放整轮 turn
- assistant SSE 错误事件现已补齐 run 级元数据：stream error 默认会带 `run_id / conversation_id / client_turn_id / event_seq / state_version / ts`；运行中异常优先使用 `AssistantService` 附着的精确 stream meta，准备阶段失败则由 router 基于 request 回填最小元数据
- 前端 `AssistantTurnStreamTerminalError` 现已保留 run 级元数据：结构化 `error` 事件与 `cancelled tool_result -> EOF` 两条终止路径都会保留 `runId / conversationId / clientTurnId / eventSeq / stateVersion / ts`
- assistant 前端 continuity 口径进一步对齐：`Studio` 之外，`Incubator` 聊天也已记录 `latestCompletedRunId`，并在后续 turn 通过 `continuation_anchor.previous_run_id` 回传后端
- assistant 共享 stream client 现已把异常 EOF 收口成结构化终止错误：若已拿到 run/tool/chunk 元数据后流意外断开，会抛 `AssistantTurnStreamTerminalError(code=stream_interrupted)` 并保留最后一次事件元数据
- `Incubator` 空会话判定现已与 `Studio` 对齐：`latestCompletedRunId` 也会把会话视为非空，避免带 continuity 真值的会话被误复用成“新对话”
- assistant 共享 stream client 现已把 malformed SSE payload 收口成结构化终止错误：非法 JSON 不再上抛原始 `SyntaxError`，而是统一转成 `AssistantTurnStreamTerminalError(code=stream_payload_invalid, terminalStatus=failed)` 并尽量保留最后一次事件元数据
- assistant 规则层当前闭环：已支持用户规则 `/api/v1/assistant/rules/me` 与项目规则 `/api/v1/assistant/rules/projects/{project_id}`；运行时自动注入“用户长期规则 + 当前项目规则”，Web 全局设置与项目设置已补入口；规则真值文件分别落在 `apps/api/.runtime/assistant-config/users/<user_id>/AGENTS.md` 与 `apps/api/.runtime/assistant-config/projects/<project_id>/AGENTS.md`
- 多用户 assistant 体验第二轮收口：全局设置已整理为“AI 助手 / 模型连接”双入口，AI 偏好正式露出并与个人长期规则形成同一用户心智；孵化聊天默认会优先使用个人 AI 偏好，退出登录时会清空工作台项目上下文，避免账号串用；AI 偏好真值文件位于 `apps/api/.runtime/assistant-config/users/<user_id>/preferences.yaml`
- assistant 项目层配置闭环：项目设置页现已支持“项目长期规则 / 项目 AI 偏好 / 项目 Skills / 项目 MCP”；真值文件写入 `projects/<project_id>/AGENTS.md`、`preferences.yaml`、`skills/<skill_id>/SKILL.md`、`mcp_servers/<server_id>/MCP.yaml`；运行时按 `项目 -> 用户 -> 系统` 解析，其中 AI 偏好做字段级覆盖，Skills / MCP 做同 ID 命中覆盖
- assistant 配置方向已进一步收口：后续继续靠拢 Claude 的“文件放到约定位置即可生效”模式，但只保留适合小说创作场景的两层作用域（全局 / 项目）；普通用户主路径改为 `规则文件 / 当前会话 / 文稿上下文 / 模型连接`，`Skill / Agent / MCP` 变成显式增强能力，`Agents / Hooks` 保留为高级能力
- Studio 聊天显式 Skill 模式已落地：默认是“普通对话”，不再自动绑定系统内置 Skill；当前会话现支持“本次使用一次 / 当前会话持续使用”两种 Skill 语义，并按会话持久化。
- assistant 前端 Claude 化第二阶段收口：全局设置与聊天页现已统一主路径，默认先引导“个人长期规则 + 当前会话 + 模型连接”；`Skills / Agents / Hooks / MCP` 收进更明确的次级区域，并继续支持“可视化编辑 / 按文件编辑”双模式；用户仍可直接按 `SKILL.md / AGENT.md / HOOK.yaml / MCP.yaml` 约定编辑，但这些文件不再等同于普通聊天默认主链
- 用户自定义 Skills 最小闭环：大厅设置现已新增独立 `Skills` 页签，用户可创建、编辑、启用/停用、删除自己的 Skill，并在聊天页“模型与连接”里直接切换；Skill 真值文件位于 `apps/api/.runtime/assistant-config/users/<user_id>/skills/<skill_id>/SKILL.md`
- 用户自定义 Agents 最小闭环：大厅设置现已新增独立 `Agents` 页签，用户可创建、编辑、启用/停用、删除自己的 Agent，并在聊天页“模型与连接”里直接切换；Agent 真值文件位于 `apps/api/.runtime/assistant-config/users/<user_id>/agents/<agent_id>/AGENT.md`
- 用户自定义 Hooks 最小闭环：大厅设置现已新增独立 `Hooks` 页签，用户可创建、编辑、启用/停用、删除自己的 Hook，并在聊天页“模型与连接”里按当前会话选择启用；Hook 真值文件位于 `apps/api/.runtime/assistant-config/users/<user_id>/hooks/<hook_id>/HOOK.yaml`
- 用户自定义 MCP 最小闭环：大厅设置现已新增独立 `MCP` 页签，用户可创建、编辑、启用/停用、删除自己的 MCP，并在 Hooks 里直接绑定调用；MCP 真值文件位于 `apps/api/.runtime/assistant-config/users/<user_id>/mcp_servers/<server_id>/MCP.yaml`
- assistant 运行时一致性补丁：hook agent 现已和主回复共用同一套用户偏好与项目规则叠加逻辑，不再出现主回复与 hook agent 模型/口径不一致
- workflow runtime 模型回退闭环：已支持 candidate 构建、capability skip、retry、fallback exhausted pause/fail 语义；相关 pause reason 与 snapshot 已接入 state machine / review executor
- context / review / billing / export / analysis 已补到查询面板或最小业务闭环
- template + incubator 闭环：built-in sync、自定义模板、draft / create-project / conversation draft、完整度前移
- config_registry 管理闭环：skills / agents / hooks / workflows 查询与 detail / update，strict DTO + staged config 校验
- Config Registry 前端闭环：Lobby 子视图已支持 skills / agents / hooks / mcp_servers / workflows 列表、详情预览与 JSON 编辑保存
- Project Settings 前端闭环：`/workspace/project/:projectId/settings` 已支持项目摘要自由文本提炼/保存、项目规则、项目 AI 偏好、项目 Skills、项目 MCP、项目审计日志子页，以及未保存离开保护
- Credential Center 前端闭环：`/workspace/lobby/settings?tab=credentials` 已支持全局/项目作用域切换、项目入口、凭证编辑更新、审计子视图和未保存离开保护；编辑态保存成功后会立即以最新返回结果重建表单，`apiKey` 这类不会回显明文的字段不再让“返回项目大厅”误判为仍有未保存更改
- Credential Center 删除确认闭环：删除前现有显式确认弹窗，影响文案对齐后端作用域优先级与 usage 历史限制
- Credential Center 覆盖提示闭环：带项目上下文查看全局凭证时，可显式看到哪些 provider 已被项目级启用凭证接管
- Lab 前端 MVP 闭环：`/workspace/project/:projectId/lab` 已支持 `analysis_type / content_id / generated_skill_key` 过滤、详情删除确认、创建结果反馈与组件拆分
- Workspace Shell 折叠侧栏闭环：全局工作台侧栏现支持桌面端展开/收起、偏好持久化与小屏自动收口，相关导航纯函数已补单测
- Workspace UI 壳层优化闭环：`WorkspaceShell` 现已改为更克制的导航面板 + 主内容舞台结构，侧栏激活态、折叠态、导航语义和共用卡片层级已统一；同时补齐 `skip link`、`aria-live`、触控细节和输入提示，移动端不再显示无效的展开/收起切换按钮
- Studio 顶部 Tab 布局闭环：`Studio` 现已改为页头操作区 + 顶部 Tab + 右侧辅助卡片，章节目录只在章节面板内部展示，章节列表已显式区分 loading / error / empty
- Studio 文稿文件保存闭环：当前创作页已支持项目文稿文件 `GET/PUT`，默认保存到 `apps/api/.runtime/project-documents/projects/<project_id>/documents/`；文件层现在支持 `.md + .json`，并会在新建项目时直接创建一套空模板（项目说明、设定细分、`数据层/*.json`、章节规划、时间轴、附录、校验、导出），后续允许用户自行删改；正式 `大纲 / 开篇设计 / 正文章节` 继续走 DB 内容真值。`正文` 目录下允许新增卷目录和章节路径占位文件，但章节正文仍只通过 content 保存链更新。
- Studio 文稿树 CRUD 闭环：当前创作页左侧文稿树已从“固定骨架 + 自定义节点”改成“少量固定槽位 + 可编辑默认模板”；固定只保留 `设定 / 大纲 / 正文` 语义槽位和 DB 真值节点，其余模板节点都支持重命名、删除、新增与扩展。正文现在支持新增卷目录和章节创建；删除当前文稿时会优先回退到邻近文稿，不再直接跳到全局第一份。重命名/删除若影响当前打开文稿，会同步更新 `doc` 路由；聊天里已选的上下文路径也会随之重映射或移除
- Engine 控制区压缩闭环：`Engine` 现已改为页头控制区 + 顶部状态区 + 全宽详情区，workflow 输入、控制按钮、摘要与调试入口已从左侧控制栏收口
- 数据库演进闭环：Alembic baseline，startup 与文件型 SQLite helper 优先走 Alembic
- Web 工作台主子视图已基本路由化：Lobby / Incubator / Config Registry / Template Library / Recycle Bin / Global Settings / Project Settings / Studio / Engine / Lab

## 进行中 / 未完成

- 前端更多页面和交互完善
- 用户自定义 `Workflows` 仍未实现；当前用户侧已补到 `AI 偏好 + 用户规则 + 项目规则 + 用户 Skills + 用户 Agents + 用户 Hooks + 用户 MCP`
- agent 通用 tool-calling 尚未实现

## 当前仍有效的关键决策

- `provider` 负责渠道 / 凭证解析，协议由 `api_dialect` 决定，模型缺省由 `default_model` 决定
- 正文真值只在 `contents + content_versions`；`artifacts`、运行时摘要或预览结果都不是正文主真值
- `Studio` 项目文稿文件当前只是工作台文件层，不替代 `contents + content_versions`；它更适合项目说明、设定细化、章节规划、时间轴、附录、校验和自由整理文稿，正式大纲 / 开篇设计 / 正文章节仍走内容主链。正文目录下的卷目录和章节路径占位文件只负责树结构与导航，不保存正文真值。
- `Studio` 数据层 JSON 当前正式定位为结构化资料层：适合人物 / 势力 / 关系 / 事件等机器可读资料，但不替代 `ProjectSetting` 或 `contents + content_versions` 主真值。
- `Studio` 文稿编辑器当前已按文件类型分流：`.md` 继续走 Markdown 编辑 / 预览，`.json` 走 JSON 编辑 / 预览；其中 `数据层/人物.json`、`势力.json`、`人物关系.json`、`势力关系.json`、`隶属关系.json` 会组合成只读关系图预览，`结构定义.json`、`事件.json` 和其它 JSON 保持格式化预览，不提供手工连线编辑。
- `Studio` 文稿树当前正式语义是“少量固定槽位 + 一次性默认模板”：固定槽位只保留 `设定 / 大纲 / 正文`，默认模板在新建项目时直接以空文件写入文件层，后续不再因列表/读取而把已删除模板文稿偷偷补回来；正文新增章节时走 DB 章节创建链，并把路径挂到当前卷目录或正文根目录下。
- 投影视图（`character_profile` / `world_setting`）统一由 `project` 边界提供，不在 context / content 各自维护
- `ProjectSetting` 当前正式降级为“结构化摘要真值”：用于快速浏览、机器投影和默认值，不再因为字段缺口阻塞大纲/开篇/正文；但摘要一旦实质变更，已确认的大纲、开篇设计、章节任务和正文仍会按 impact 标记为 stale
- stale chapter task 必须先重建章节计划，不可直接编辑；前后端同步强制
- endpoint 安全策略必须同时落在写入入口和运行时出口
- 程序化 Alembic 优先复用现有 `connection` / `engine`，不要退回字符串化 URL
- config_registry 对外暴露语义化 DTO，写回前必须 staged full-config 校验，未知字段直接失败
- `assistant runtime` 当前正式口径：默认可直接走“规则 + 当前会话消息历史”的纯聊天；`skill_id` / `agent_id` 现在是可选增强而非硬前提，且 Studio 聊天已移除默认内置 Skill 绑定；Skill 模式已收口为“规则 + Skill + 当前会话历史 + 当前消息”，runtime 会自动补齐 Skill 未显式声明的 `conversation_history / user_input`；assistant turn 的 `messages` 只允许 `user / assistant`，规则和 Skill 不进入历史；`continuation_anchor_snapshot` 现已归一化冻结 validated direct-parent digest，不再在省略 `messages_digest` 时只剩 `previous_run_id`；assistant 内部目录标准化当前已把 turn 生命周期代码统一收口到 `apps/api/app/modules/assistant/service/turn/`，把 tooling descriptor/policy/executor/loop/store 文件统一收口到 `apps/api/app/modules/assistant/service/tooling/`，把 context 纯 support 文件统一收口到 `apps/api/app/modules/assistant/service/context/`，把 hook payload/runtime/provider 文件统一收口到 `apps/api/app/modules/assistant/service/hooks_runtime/`，把 rules DTO/service/support 统一收口到 `apps/api/app/modules/assistant/service/rules/`，把 preferences DTO/service/support 统一收口到 `apps/api/app/modules/assistant/service/preferences/`，把 skills DTO/file-store/service/support 统一收口到 `apps/api/app/modules/assistant/service/skills/`，并把 agents DTO/file-store/service/support、mcp DTO/file-store/service/support、hooks 配置 DTO/file-store/service/support 统一收口到 `apps/api/app/modules/assistant/service/agents/`、`apps/api/app/modules/assistant/service/mcp/`、`apps/api/app/modules/assistant/service/hooks/`；本轮根壳评估已完成，prompt render 已回收至 `service/context/assistant_prompt_render_support.py`，其余 `assistant_service.py / factory.py / dto.py` 继续保留为稳定根壳；`mcp` 继续通过 hook/plugin 路径执行，agent 通用 tool-calling 仍是下一阶段
- assistant tool-calling 当前正式口径：ordinary chat 已支持本地 `project.*` 工具串行执行；非 `openai_responses` provider 统一走结构化 runtime replay，不再把 continuation 压回自然语言 prompt；当前 tool definitions 已统一走 shared `tool_schema_compiler`，runtime replay/Responses continuation input 已统一走 shared `tool_continuation_codec`，默认 `portable_subset` 收口 required-only `anyOf`，Gemini 叠加 `gemini_compatible`；本轮若存在 visible `project.*` 工具，assistant prepare 会显式要求连接先通过 `tool_continuation_probe`，否则直接报业务错误；`tool_catalog_version` 现已独立收口为“本轮最终可见 descriptor 快照版本”，不再借用 `document_context.catalog_version`；项目范围工具提示现已同步进入显式 `tool_guidance` snapshot，prepare 会先解析 internal discovery decision，再按本轮 actual visible tools 收口后投影成 guidance snapshot，且当前 snapshot 已显式冻结 `discovery_source`；`document_context_recovery_snapshot` 除了进入 run snapshot，也会同步进入 `NormalizedInputItem(item_type=document_context_recovery)`，而 latest `document_context_injection_snapshot` 已进入 `AssistantTurnContext / AssistantTurnRunSnapshot / AssistantTurnRun` 与 hook payload，并被 prompt projection / prompt render 直接复用；initial prompt compaction snapshot 现已具备 `phase / level` 元信息，其中 `soft` 表示摘要之外仍保留最近原始消息，`hard` 表示历史已完全折叠到摘要里；并额外冻结 `compressed_messages_digest + projected_messages_digest + summary_anchor_keywords + protected_document_reasons + protected_document_binding_versions + document_context_collapsed + document_context_projection_mode + projected_document_context_snapshot + document_context_recovery_snapshot`，其中 `projected_document_context_snapshot` 已与 `document_context_injection_snapshot` 对齐；`fail` 当前不写入 snapshot，而是与 continuation compaction 共用 `budget_exhausted` terminal error；`NormalizedInputItem(item_type=compacted_context)` 当前 `content` 保留摘要文本，`payload` 直接复用完整 `compaction_snapshot`；`before_assistant_response / after_assistant_response` hook payload 当前也会同步暴露 latest `request.document_context_bindings_snapshot / request.document_context_recovery_snapshot / request.document_context_injection_snapshot / request.compaction_snapshot / request.tool_guidance_snapshot / request.tool_catalog_version / request.exposed_tool_names_snapshot`；latest continuation request view 现已进入显式 `continuation_request_snapshot`，并与 `provider_continuation_state / continuation_compaction_snapshot` 分离；latest tool-loop continuation budget compaction 现已进入显式 `continuation_compaction_snapshot`，并会记录 `compressed_items_digest + projected_items_digest + compacted_tool_names + compacted_document_refs + compacted_document_versions + compacted_catalog_versions`，其中 `soft` 表示仅发生 item 内部 payload trimming，`hard` 表示 top-level item 删除或 `content_items` 槽删除，`fail` 则与 initial prompt compaction 一样显式返回共享 `budget_exhausted` 终止错误；共享前端 stream client 目前明确以 `completed / error / cancelled tool_result` 为终止真值优先级
- assistant tool-calling `v1B` 当前已推进到 continuity-first 文稿工具面：`project.list_documents / search_documents / read_documents / write_document` 已接入 runtime；长历史 compaction、tool-loop continuation budget、metadata-only 文稿搜索已收口；`grant_bound` 写路径现已具备显式 `approval_grant` 骨架，并把 grant snapshot 落到 `AssistantToolStep / AssistantTurnRun`
- assistant SSE 当前正式口径：除普通 `completed`/tool 事件外，`error` 事件也应尽量携带同一 run 的结构化元数据，前端不再只依赖裸错误消息来推断归属
- 用户 Hook 当前正式支持 `agent | mcp` 两类动作；MCP 会先解析用户自己的 `mcp_servers/<server_id>/MCP.yaml`，找不到再回退系统 MCP
- 多用户 assistant 配置当前正式口径：平台可保留系统内置 `skill/agent/hook/mcp/workflow` 作为可选能力；普通用户当前正式拥有个人偏好、个人长期规则、个人 Skills、个人 Agents、个人 Hooks、个人 MCP、项目长期规则和项目 AI 偏好；这些能力当前均以文件为主真值；用户自定义 `Workflows` 仍待补齐
- runtime hardening 当前已补齐：assistant hook-agent 会按 agent 类型传 `response_format`；MCP provider 会显式拒绝 disabled server / `is_error=true`；workflow staged config 会拒绝 assistant-only hook 事件和 before/after stage 错绑
- 轻权限边界当前正式口径：普通业务面继续 owner-only；控制面写操作走 `EASYSTORY_CONFIG_ADMIN_USERNAMES` 轻量白名单。当前已覆盖 `config_registry` 与模板创建/更新/删除，模板读取仍只要求登录

## 仍需注意的坑点

- aiosqlite 沙箱挂起不是业务回归（0.21.0 / 0.22.1 非沙箱都正常）
- unified exec 进程数告警是工具层会话配额问题，不是仓库代码回归
- workflow_snapshot 恢复需剥离运行时扩展字段，否则 WorkflowConfig extra key 校验失败
- PromptReplay.response_text 是文本列，结构化 LLM 响应需先 JSON 序列化再落库
- DB 事务 + 文件系统副作用：先 commit 再做不可回滚的文件删除
- async 语义审查不要误把基础设施命名（AsyncSessionFactory 等）当待清理对象
- shared/runtime 改为惰性导出，避免 settings -> runtime -> llm tool provider 循环导入

## 最近活跃窗口（2026-03-26 ~ 03-30）

- 2026-03-27：完成 Workspace / Studio / Engine 的一轮布局收口，工作台侧栏、页头骨架、状态区和移动端细节已统一。
- 2026-03-28：assistant 配置主真值切到 `apps/api/.runtime/assistant-config/`，多用户体验改为“AI 助手 / 模型连接”双入口，并补齐未保存离开保护。
- 2026-03-29：修复本地 SQLite 开发库迁移卡死导致的“页面一直加载中”；登录、项目大厅、AI 聊天、模型连接页恢复。
- 2026-03-29：完成用户自定义 Skills 闭环，真值文件落到 `users/<user_id>/skills/<skill_id>/SKILL.md`；聊天页可直接切换 Skill。
- 2026-03-29：完成用户自定义 MCP + Hook(mcp) 闭环，真值文件落到 `users/<user_id>/mcp_servers/<server_id>/MCP.yaml`；Hook 可直接绑定用户 MCP。
- 2026-03-30：继续按 Claude 风格收口前端主路径，保留“长期规则 + Skills + 模型连接”为默认心智，`Agents / Hooks / MCP` 进入更明确的次级区域。
- 2026-03-30：补齐项目级 Skills / MCP，文件真值落到 `projects/<project_id>/skills/<skill_id>/SKILL.md` 与 `projects/<project_id>/mcp_servers/<server_id>/MCP.yaml`，运行时按 `项目 -> 用户 -> 系统` 解析；浏览器已实测 `Skills -> MCP` 无输入切换不再弹未保存提示。
- 2026-04-04：修复模型连接编辑页保存后 dirty 误报；根因是编辑表单未在保存成功后立即重建基线，尤其 `apiKey` 不回显时会长期判脏。前端 `lint` 与 `test:unit` 已通过，并已在浏览器真实验证“编辑 -> 保存 -> 返回项目大厅”不再弹未保存提示。
- 2026-04-06：assistant 原生 tool-calling runtime `v1A` 继续收口：非 `openai_responses` provider 改为结构化 replay，recoverable tool error 可回填模型继续推理，SSE `state_version` 回到 run 真值；`assistant_service + continuation + assistant_api` 共 `54 passed`，前端共享 stream client 终止优先级测试补齐并通过。
- 2026-04-06：继续补齐 assistant stale-run 恢复语义：`AssistantTurnRun` 新增本地 runtime claim（`host / pid / instance_id`），旧进程中断留下的 `running` run 现在会被显式收口为 failed，而不是永久 `run_in_progress`；相关 assistant 后端回归已通过。
- 2026-04-06：继续完善 SSE 错误语义：router/stream runtime 现已为 `error` 事件补齐 run 关联元数据，API 与前端 stream fixture 同步到真实 error 形状；`assistant_api`、相关 `assistant_service` 异常路径和前端 stream 测试已通过。
- 2026-04-06：继续收口前端 stream 终止真值：`AssistantTurnStreamTerminalError` 现在会保留 `error` 与 `cancelled` 两类终止路径的 run 元数据；过程中修正了一次 camelCase/snake_case 二次转换导致的 `runId` 丢失问题，定向前端测试与 `eslint` 已通过。
- 2026-04-06：补齐 `Incubator` 聊天 continuity：session/store/request builder/成功提交链已接入 `latestCompletedRunId -> continuation_anchor.previous_run_id`，避免与 `Studio` 在 run continuity 语义上继续漂移；相关前端定向测试 `5 passed`，`eslint` 通过。
- 2026-04-06：继续完善共享 stream client：异常 EOF 不再抛裸 `Error`，而是统一转成带最后事件元数据的 `stream_interrupted` 结构化终止错误；assistant stream 定向测试与 `eslint` 已通过。
- 2026-04-06：修正 `Incubator` store 边角语义：空会话判定已把 `latestCompletedRunId` 纳入非空条件，与 `Studio` 保持一致；相关 `Incubator` store/request/submit` 定向测试与 `eslint` 已通过。
- 2026-04-06：继续强化共享 stream client 的协议异常暴露：malformed SSE payload 不再向上冒原始 `SyntaxError`，而是统一转成 `stream_payload_invalid` 结构化终止错误；中途修正了“误把正常 `error` 事件也包成 payload invalid”的实现错误，相关定向测试与 `eslint` 已通过。
- 2026-04-06：assistant 文稿工具继续稳步推进到 `v1B`：补齐 `project.search_documents` 契约、continuity-first 搜索排序、长历史 compaction/budget、tool-loop continuation 预算，以及 `project.write_document` 的显式 `approval_grant` 骨架；当前 grant 已进入 policy decision、execution context、tool step snapshot 与 turn run snapshot，定向后端回归已通过。
- 2026-04-07 ~ 2026-04-09：assistant runtime context governance、模型工具兼容层与凭证能力真值主线已收口：tool name alias codec、`tool_schema_compiler / tool_call_codec / tool_continuation_codec / stream_event_normalizer`、conformance probes、`interop_profile` 与分模式 `stream_tool_* / buffered_tool_*` 已打通 verifier -> assistant runtime -> Credential Center；assistant 在 visible `project.*` 工具存在时会按本轮 `stream` 模式要求对应能力，连接关键字段变更会清空验证状态，Credential Center 已区分 `验证连接 / 验证流式工具 / 验证非流工具` 并展示双模式工具能力摘要；同一窗口内 reasoning/compat 继续收口为“协议级边界 + 上游显式报错”：`llm_reasoning_validation` 不再按具体 GPT/Gemini 子型号做本地硬控，OpenAI Chat 官方端点优先使用 `max_completion_tokens`、第三方兼容网关继续保留 `max_tokens`，前端/偏好文案也会明确区分 `reasoning_effort` 与 `reasoning.effort` 的 dialect 差异。相关定向后端与前端测试已补齐并验证。
