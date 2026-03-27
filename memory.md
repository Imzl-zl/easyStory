# easyStory 项目状态

> 本文件是当前状态快照 + 最近活跃窗口，允许覆盖更新。
> 完整历史归档见 `memory/archive/`，稳定规律见 `tools.md`。

## 当前基线

- 后端测试：最近一次已知全量 `cd apps/api && ruff check app tests && pytest -q` 通过（记录日期：2026-03-23）
- 前端检查：最近一次已知 `pnpm --dir apps/web exec tsc --noEmit` + `pnpm --dir apps/web lint` + `pnpm --dir apps/web test:unit` 通过（记录日期：2026-03-27）
- 最后更新：2026-03-27

## 已完成能力

- 凭证与模型连接闭环：安全存储、endpoint policy、`api_dialect` 路由、auth strategy override、公网 http 显式测试开关、本地 provider interop probe、旧库 schema reconcile
- provider interop 深化闭环：本地 probe 已支持 `prompt/system_prompt/extra_headers/stream`，并对 Gemini probe 注入最小思考配置，避免默认 thinking 吞掉输出预算
- Credential Center 高级兼容设置闭环：凭证现正式支持 `auth_strategy / api_key_header_name / extra_headers`，前后端和运行时请求链已对齐；其中 `extra_headers` 已收口为仅允许非敏感元数据头
- 项目与前置资产闭环：project CRUD、setting completeness、story asset generation / confirm
- 内容主链路闭环：outline / opening_plan / chapter / content version、章节确认与 stale 传播
- 工作流闭环：control plane、runtime、auto-review / fix、workflow logs / prompt replay / audit
- workflow hooks runtime 闭环：`script/webhook/agent` 已真实接入 workflow runtime，`PluginRegistry` 支持 execute/timeout，hook agent 依赖已进入 snapshot，builtin `auto_save_content` 可执行
- assistant runtime 第一阶段闭环：新增 `/api/v1/assistant/turn`，非 workflow 对话已支持 skill prompt、hook 生命周期与 `mcp` 插件调用；workflow snapshot 已可冻结 `resolved_mcp_servers`
- workflow runtime 模型回退闭环：已支持 candidate 构建、capability skip、retry、fallback exhausted pause/fail 语义；相关 pause reason 与 snapshot 已接入 state machine / review executor
- context / review / billing / export / analysis 已补到查询面板或最小业务闭环
- template + incubator 闭环：built-in sync、自定义模板、draft / create-project / conversation draft、完整度前移
- config_registry 管理闭环：skills / agents / hooks / workflows 查询与 detail / update，strict DTO + staged config 校验
- Config Registry 前端闭环：Lobby 子视图已支持 skills / agents / hooks / mcp_servers / workflows 列表、详情预览与 JSON 编辑保存
- Project Settings 前端闭环：`/workspace/project/:projectId/settings` 已支持项目设定编辑与项目审计日志子页
- Credential Center 前端闭环：`/workspace/lobby/settings?tab=credentials` 已支持全局/项目作用域切换、项目入口、凭证编辑更新与审计子视图
- Credential Center 删除确认闭环：删除前现有显式确认弹窗，影响文案对齐后端作用域优先级与 usage 历史限制
- Credential Center 覆盖提示闭环：带项目上下文查看全局凭证时，可显式看到哪些 provider 已被项目级启用凭证接管
- Lab 前端 MVP 闭环：`/workspace/project/:projectId/lab` 已支持 `analysis_type / content_id / generated_skill_key` 过滤、详情删除确认、创建结果反馈与组件拆分
- Workspace Shell 折叠侧栏闭环：全局工作台侧栏现支持桌面端展开/收起、偏好持久化与小屏自动收口，相关导航纯函数已补单测
- Studio 顶部 Tab 布局闭环：`Studio` 现已改为页头操作区 + 顶部 Tab + 右侧辅助卡片，章节目录只在章节面板内部展示，章节列表已显式区分 loading / error / empty
- Engine 控制区压缩闭环：`Engine` 现已改为页头控制区 + 顶部状态区 + 全宽详情区，workflow 输入、控制按钮、摘要与调试入口已从左侧控制栏收口
- 数据库演进闭环：Alembic baseline，startup 与文件型 SQLite helper 优先走 Alembic
- Web 工作台主子视图已基本路由化：Lobby / Incubator / Config Registry / Template Library / Recycle Bin / Global Settings / Project Settings / Studio / Engine / Lab

## 进行中 / 未完成

- 前端更多页面和交互完善
- assistant 聊天 UI 与 agent 通用 tool-calling 尚未实现

## 当前仍有效的关键决策

- `provider` 负责渠道 / 凭证解析，协议由 `api_dialect` 决定，模型缺省由 `default_model` 决定
- 正文真值只在 `contents + content_versions`；`artifacts`、运行时摘要或预览结果都不是正文主真值
- 投影视图（`character_profile` / `world_setting`）统一由 `project` 边界提供，不在 context / content 各自维护
- stale chapter task 必须先重建章节计划，不可直接编辑；前后端同步强制
- endpoint 安全策略必须同时落在写入入口和运行时出口
- 程序化 Alembic 优先复用现有 `connection` / `engine`，不要退回字符串化 URL
- config_registry 对外暴露语义化 DTO，写回前必须 staged full-config 校验，未知字段直接失败
- `assistant runtime` 当前采用显式 `agent_id/skill_id + hook_ids` 装配，不把配置自动全局注入任意对话；`mcp` 当前通过 hook/plugin 路径可执行，agent 通用 tool-calling 仍是下一阶段
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

## 最近活跃窗口（2026-03-22 ~ 03-27）

- 2026-03-22：完成 review follow-up、模型连接方言化、Alembic 初始迁移与 DB 初始化链收口
- 2026-03-23：完成 config_registry skills / agents / hooks / workflows detail / update 闭环，并收口 strict DTO + staged validation
- 2026-03-23：完成 template 自定义模板、incubator draft / create-project / conversation draft 与完整度前移
- 2026-03-24：收口协作文件边界：`AGENTS.md` 管规则，`tools.md` 管稳定知识，`memory.md` 管当前快照；`docs/` 改为按需查
- 2026-03-24：完成 Web Incubator 前端闭环：独立路由、模板问答 draft/create、自由描述 draft、Lobby 入口与导航高亮
- 2026-03-25：修复 Web Incubator review 问题：模板 loading/error 语义显式化，模板详情未就绪时阻断提交，自由描述 preview 支持 stale 提示
- 2026-03-25：补齐 Web Template Library 前端闭环：独立路由、模板列表筛选、详情快照、自定义模板 CRUD、内建模板复制与 Lobby 入口
- 2026-03-25：完成 Lobby 子视图路由化：回收站与全局设置拆出独立路由，Credential Center 支持审计日志子视图与默认 base_url 预填
- 2026-03-25：补齐 Engine 实时事件流：前端改为 `fetch + ReadableStream` 接 SSE，支持带鉴权订阅、静默 EOF 重连、异常断线提示、重连成功系统日志与终态停重连
- 2026-03-25：补齐 Engine Export Dialog：导出入口改为模态对话框，支持格式选择、章节任务预检、项目导出历史；后端 `stale` 导出口径与文档对齐
- 2026-03-25：收口 Engine review fixes：导出预检与后端 `stale` 规则对齐，SSE 本地状态改为 session 隔离且 4xx 停止重连，DialogShell 基础焦点管理通过 lint，导出定向 pytest 与前端 tsc/lint 全绿
- 2026-03-25：补齐 Engine SSE fatal error 显式提示：页面顶部新增 danger banner，不再只靠系统日志暴露 4xx；同时给 export/events support 补了 Node 原生单测链，`apps/web test:unit` 可执行
- 2026-03-25：收口 Engine workflow 切换状态一致性：`EnginePage` 现在对输入框和 selected execution 使用 workflow-bound 本地状态，手动载入已有 workflow 后会回写 `lastWorkflowByProject`，避免切换 workflow 时继续请求旧 prompt replay
- 2026-03-25：收口 Engine Prompt Replay 面板：新增独立 `EngineReplayPanel` 与 replay support/test，显式覆盖 workflow 未载入、execution 未就绪、replay 加载/失败/空态，并补齐模型名、token 用量与 prompt/response 折叠展示
- 2026-03-25：修复 Engine Prompt Replay 审查项：已有 execution/replay 数据时不再被 refetch 错误整块覆盖，Prompt/Response 折叠状态可跨 rerender 保持，execution 选择项补齐序列与短 ID 以避免同名歧义
- 2026-03-25：补齐 Engine pause reason 闭环：页面顶部新增暂停原因 callout，`review_failed`/`budget_exceeded` 可直接跳转到对应 tab，未载入 workflow 空态补显式“启动工作流”入口
- 2026-03-25：补齐 Engine 工作流启动前的 preparation 状态展示：`PreparationStatusPanel` 与 support 抽到 shared `project` feature，Studio / Engine 共用一套状态文案与映射；Engine 未载入 workflow 时先展示设定完整度、前置资产和下一步提示，并补显式 support 单测
- 2026-03-25：补齐 Engine 章节任务重建确认闭环：重建按钮改为“检查并确认”，新增确认对话框与固定风险文案“重建将覆盖当前章节计划，已生成的草稿将被标记为失效。”；确认后才真正调用重建接口，成功后对话框关闭并把焦点回到任务列表
- 2026-03-25：修复 Engine review issues：start 按钮现绑定 `project-preparation-status.can_start_workflow`，preparation 未就绪/加载中/查询失败时前端直接禁用并给出原因；`DialogShell` 支持可选焦点恢复目标，任务重建确认弹窗成功后回任务列表、取消后回触发按钮
- 2026-03-25：补齐 Engine 工作流摘要展示：顶部状态区改为中文 `status + mode` 徽标，左侧在 raw JSON 前新增 `Workflow Summary` 卡片，统一展示当前节点、恢复起点、启动/完成时间和 runtime snapshot；摘要逻辑收口到独立 support，并通过前端 `tsc/lint/test:unit`
- 2026-03-25：补齐 Engine overview 结构化执行概览：中央 `overview` tab 不再输出 raw JSON，改为概览指标 + 节点时间线；时间线以 `workflow.nodes` 为主顺序，用 `node executions` 补齐最新状态、时间、重试、产物与审查数量，并把“定义外节点”显式暴露；runtime 查询失败时直接展示错误，不伪造等待态
- 2026-03-25：收口 Engine detail 语义：右侧 detail tab 统一改为中文标签，tab 装配逻辑抽到独立 `EngineDetailPanel`；raw workflow JSON 改为折叠式调试入口，不再占左侧主信息层；前端 `tsc/lint/test:unit` 通过
- 2026-03-25：补齐 Engine execution 到 replay 入口联动：`overview` 节点时间线和 `logs` 执行卡都可直接切到 `Prompt Replay` 并选中对应 execution；同时 `logs` 面板在保留旧数据时改为顶部错误 banner，不再因 refetch 错误整块丢内容；新增 logs support/test 并纳入 `test:unit` 白名单，前端 `tsc/lint/test:unit` 通过
- 2026-03-25：修复 Engine review follow-up：统一 `logs/review/billing/context` 的时间展示为真实 UTC；`overview` 指标改为把 `skipped` 计入完成推进；`test:unit` 改为自动扫描 `src/features/**/*.test.ts`，避免新增 support 测试再次漏跑；前端 `tsc/lint/test:unit` 通过
- 2026-03-25：收口 Engine Prompt Replay URL 状态：`execution` 成为 Engine 页的唯一选中真值，`overview/logs -> replay` 一次性写入 `tab + execution`，workflow 切换与动作成功回写统一通过 helper 决定是否保留 execution；execution 列表加载完成后会显式清理 stale `execution` 参数，但 observability 查询失败时不静默清理；同时把 `EnginePage` 左栏与顶部 action 拆成独立组件，`engine-page.tsx` 降到 289 行，前端 `tsc/lint/test:unit` 通过
- 2026-03-25：补齐 Config Registry 前端管理页：Lobby 新增“配置中心”入口与 `/workspace/lobby/config-registry` 路由，已支持 skills / agents / hooks / workflows 的列表、详情预览和完整 JSON DTO 编辑保存；前端 contract 直接对齐后端 `ConfigRegistry` DTO，不再自造第二套字段语义；前端 `tsc/lint/test:unit` 通过
- 2026-03-25：补齐 Project Settings 前端子页：Lobby 项目卡新增“项目设置”入口，`/workspace/project/:projectId/settings` 已支持设定编辑与 `?tab=audit&event=` 项目审计过滤；工作台导航在 settings 子页下继续归属 Studio，前端 `tsc/lint/test:unit` 通过
- 2026-03-25：补齐 Credential Center 前端 scope/update 闭环：全局设置页现支持 `scope=user|project` 与 `project=:projectId` 语义，项目设置侧栏新增“项目凭证”入口，凭证列表支持编辑，表单支持 create/edit 两种模式与 update payload 精准构造；新增 query/payload support 单测，前端 `tsc/lint/test:unit` 通过
- 2026-03-25：补齐 Credential Center 删除确认交互：凭证列表删除改为显式确认弹窗，影响说明仅基于已确认规则（项目级 > 全局 > 系统[仅显式允许]、usage 历史会阻止删除、成功后写审计）；新增 delete confirm support 单测，前端 `tsc/lint/test:unit` 通过
- 2026-03-25：补齐 Credential Center 覆盖提示：在带项目上下文的全局凭证视图里，前端会并行查询当前项目凭证，并按 active provider 匹配显示“已被项目级重载”提示；覆盖提示查询失败时会显式报错，不做静默忽略；新增 override support 单测，前端 `tsc/lint/test:unit` 通过
- 2026-03-25：收口 Credential Center 动作状态语义：`actionMutation.variables` 现在作为唯一 pending action 真值，列表按钮可按 `credentialId + actionType` 显示“验证中/启用中/停用中/删除中...”；验证成功反馈时间统一改为 UTC 格式，并新增 action/feedback support 单测
- 2026-03-25：修复 Credential Center review issues：`audit` 子视图收口为只读审计视图，不再暴露 verify/enable/disable/delete；同时在 mutation 期间锁定 `scope`/`mode`/审计目标切换，避免 pending 语义和反馈上下文漂移
- 2026-03-25：补齐 Lab 前端 MVP：Lab 页面拆成 sidebar/detail/create/delete-confirm/feedback/support，列表支持 `analysis_type / content_id / generated_skill_key` 过滤；创建成功会根据当前过滤条件决定是否自动选中，删除后按相邻记录回退，顶栏反馈统一收口为 `info / danger`；refetch 失败时保留已有列表/详情数据，`result` 空对象在前端直接阻断
- 2026-03-26：补齐 provider interop 本地联调闭环：`shared/runtime` 现支持 `auth_strategy` / `api_key_header_name` override，并新增 `EASYSTORY_ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS` 显式测试开关；本地新增 `provider_interop_support.py` 与 `scripts/provider_interop_check.py`，用户提供的 GPT / Gemini / Anthropic profile 已保存到 ignored 本地文件，并已实测全部返回 `ok`：GPT 走 `openai_responses`，Anthropic `system` 需发 text block 数组，Gemini 保持 `generateContent`
- 2026-03-26：收口凭证兼容层实现：`model_credentials` 新增 `auth_strategy / api_key_header_name / extra_headers`，Credential Center 表单新增“高级兼容设置”，验证短提示改为自然句“今天天气真好。”
- 2026-03-26：收口凭证 review fixes：provider interop `--model` 覆写现会真正进入 probe 请求；`api_key_header_name` 不再允许覆盖运行时保留头；`extra_headers` 改为只允许非敏感元数据头，前后端校验与定向 pytest / tsc / test:unit 已通过
- 2026-03-26：完成 runtime/provider hardening：`project incubator` 改为复用统一 credential payload，workflow runtime 已补 candidate/capability/retry/model fallback 主链并把 `model_fallback_exhausted` 接到 pause/fail 语义；`workflow_runtime_*` 与 provider interop helper 已拆分到 support 文件，核心 mixin 均降到 300 行内
- 2026-03-26：完成 workflow hooks runtime 闭环：新增 `PluginRegistry.execute`、workflow hook providers（script/webhook/agent）、节点级 hook dispatch、hook agent snapshot 冻结与 `app.hooks.builtin.auto_save_content`；定向 `ruff + pytest` 已通过
- 2026-03-26：完成真实上游文字联调：`gpt / gemini / anthropic` 非流式与流式 probe 均对 `今天有什么新闻` 返回文字；其中 Gemini 初始返回半句，经确认是上游 `finishReason=MAX_TOKENS` + 默认 thinking 导致，probe 现已显式压低 thinking 配置后恢复为有效文本返回
- 2026-03-26：完成 assistant runtime 第一阶段：新增 `assistant` 模块与 `/api/v1/assistant/turn`，支持 skill 驱动 prompt、assistant hook 事件、`mcp_server` 配置加载、`mcp` hook provider 与 workflow `resolved_mcp_servers` snapshot；定向 `ruff + pytest` 已通过
- 2026-03-26：补齐 `mcp_servers` 配置管理闭环：`config_registry` 后端已支持 list/detail/update，Web 配置中心已新增 `mcp_servers` 类型；后端 `15` 个 config_registry 单测与前端 `tsc/lint/test:unit` 均通过
- 2026-03-26：完成 runtime/config hardening：assistant hook-agent `response_format` 与 workflow 对齐；`McpPluginProvider` 现在会显式拒绝 disabled server 和 `is_error=true`；workflow staged validation 会在写回前拒绝 assistant-only hook 事件和 stage 错绑；最终 `ruff + 35` 项定向 pytest 通过
- 2026-03-27：完成 Workspace Shell 全局侧栏折叠首轮改造：新增 `workspace-store.sidebarPreference + hasHydrated`，工作台壳层支持桌面 220/72 切换、小屏自动收口，并补齐 `workspace-shell-support` 单测；前端 `tsc/lint/test:unit` 通过
- 2026-03-27：完成 Studio 顶部 Tab 化：`StudioPage` 已改为页头 + 顶部 Tab + 右侧准备状态卡，章节目录内收至 `Chapter` 面板；同时修复章节列表状态语义，显式区分 loading / error / empty，避免假空态；前端 `tsc/lint/test:unit` 通过
- 2026-03-27：完成 Engine 控制区压缩：`EnginePage` 已改为页头控制区 + 顶部状态区 + 全宽详情区，workflow 输入、载入动作、控制按钮与导出入口收口到页头，摘要与调试入口移出旧左侧控制栏；前端 `tsc/lint/test:unit` 通过
