# easyStory 项目状态

> 本文件是当前状态快照 + 最近活跃窗口，允许覆盖更新。
> 完整历史归档见 `memory/archive/`，稳定规律见 `tools.md`。

## 当前基线

- 后端测试：最近一次已知全量 `cd apps/api && ruff check app tests && pytest -q` 通过（记录日期：2026-03-23）
- 前端检查：最近一次已知 `pnpm --dir apps/web exec tsc --noEmit` + `pnpm --dir apps/web lint` + `pnpm --dir apps/web test:unit` 通过（记录日期：2026-03-30）
- 最后更新：2026-03-30

## 已完成能力

- 凭证与模型连接闭环：安全存储、endpoint policy、`api_dialect` 路由、auth strategy override、公网 http 显式测试开关、本地 provider interop probe、旧库 schema reconcile，以及连接级 `context_window_tokens / default_max_output_tokens`
- provider interop 深化闭环：本地 probe 已支持 `prompt/system_prompt/extra_headers/stream`，并对 Gemini probe 注入最小思考配置，避免默认 thinking 吞掉输出预算
- assistant / provider interop 流式口径已收口：assistant turn 后端默认 `stream=true`，前端非流 JSON 调用显式传 `stream=false`；credential verifier 与 provider interop probe 默认走流式；incubator / studio 聊天已移除“流式失败自动退回非流”
- Credential Center 高级兼容设置闭环：凭证现正式支持 `auth_strategy / api_key_header_name / extra_headers`，前后端和运行时请求链已对齐；其中 `extra_headers` 已收口为仅允许非敏感元数据头；连接级默认输出上限现已真实接入 runtime fallback
- 项目与前置资产闭环：project CRUD、结构化摘要提示（原 setting completeness）、story asset generation / confirm
- 内容主链路闭环：outline / opening_plan / chapter / content version、章节确认与 stale 传播
- 工作流闭环：control plane、runtime、auto-review / fix、workflow logs / prompt replay / audit
- workflow hooks runtime 闭环：`script/webhook/agent` 已真实接入 workflow runtime，`PluginRegistry` 支持 execute/timeout，hook agent 依赖已进入 snapshot，builtin `auto_save_content` 可执行
- assistant runtime 第一阶段闭环：新增 `/api/v1/assistant/turn`，非 workflow 对话已支持 skill prompt、hook 生命周期与 `mcp` 插件调用；workflow snapshot 已可冻结 `resolved_mcp_servers`
- assistant 规则层当前闭环：已支持用户规则 `/api/v1/assistant/rules/me` 与项目规则 `/api/v1/assistant/rules/projects/{project_id}`；运行时自动注入“用户长期规则 + 当前项目规则”，Web 全局设置与项目设置已补入口；规则真值文件分别落在 `apps/api/.runtime/assistant-config/users/<user_id>/AGENTS.md` 与 `apps/api/.runtime/assistant-config/projects/<project_id>/AGENTS.md`
- 多用户 assistant 体验第二轮收口：全局设置已整理为“AI 助手 / 模型连接”双入口，AI 偏好正式露出并与个人长期规则形成同一用户心智；孵化聊天默认会优先使用个人 AI 偏好，退出登录时会清空工作台项目上下文，避免账号串用；AI 偏好真值文件位于 `apps/api/.runtime/assistant-config/users/<user_id>/preferences.yaml`
- assistant 项目层配置闭环：项目设置页现已支持“项目长期规则 / 项目 AI 偏好 / 项目 Skills / 项目 MCP”；真值文件写入 `projects/<project_id>/AGENTS.md`、`preferences.yaml`、`skills/<skill_id>/SKILL.md`、`mcp_servers/<server_id>/MCP.yaml`；运行时按 `项目 -> 用户 -> 系统` 解析，其中 AI 偏好做字段级覆盖，Skills / MCP 做同 ID 命中覆盖
- assistant 配置方向已进一步收口：后续继续靠拢 Claude 的“文件放到约定位置即可生效”模式，但只保留适合小说创作场景的两层作用域（全局 / 项目）；普通用户主路径聚焦 `规则文件 / Skills / MCP`，`Agents / Hooks` 降到高级能力，不再作为一线配置心智
- assistant 前端 Claude 化第二阶段收口：全局设置与聊天页现已统一主路径，默认先引导“个人长期规则 + Skills + 模型连接”，`Agents / Hooks / MCP` 收进更明确的次级区域；同时 `Skills / Agents / Hooks / MCP` 设置页已支持“可视化编辑 / 按文件编辑”双模式，AI 设置首页也已加入用户层 / 项目层 / 系统层文件层级说明；用户可直接按 `SKILL.md / AGENT.md / HOOK.yaml / MCP.yaml` 约定编辑，不改变底层配置真值与运行时装配协议
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
- Credential Center 前端闭环：`/workspace/lobby/settings?tab=credentials` 已支持全局/项目作用域切换、项目入口、凭证编辑更新、审计子视图和未保存离开保护
- Credential Center 删除确认闭环：删除前现有显式确认弹窗，影响文案对齐后端作用域优先级与 usage 历史限制
- Credential Center 覆盖提示闭环：带项目上下文查看全局凭证时，可显式看到哪些 provider 已被项目级启用凭证接管
- Lab 前端 MVP 闭环：`/workspace/project/:projectId/lab` 已支持 `analysis_type / content_id / generated_skill_key` 过滤、详情删除确认、创建结果反馈与组件拆分
- Workspace Shell 折叠侧栏闭环：全局工作台侧栏现支持桌面端展开/收起、偏好持久化与小屏自动收口，相关导航纯函数已补单测
- Workspace UI 壳层优化闭环：`WorkspaceShell` 现已改为更克制的导航面板 + 主内容舞台结构，侧栏激活态、折叠态、导航语义和共用卡片层级已统一；同时补齐 `skip link`、`aria-live`、触控细节和输入提示，移动端不再显示无效的展开/收起切换按钮
- Studio 顶部 Tab 布局闭环：`Studio` 现已改为页头操作区 + 顶部 Tab + 右侧辅助卡片，章节目录只在章节面板内部展示，章节列表已显式区分 loading / error / empty
- Studio 文稿文件保存闭环：当前创作页已支持项目文稿文件 `GET/PUT`，默认保存到 `apps/api/.runtime/project-documents/projects/<project_id>/documents/`；其中 `设定/*`、`附录/*` 和 `大纲/章节规划.md` 走文件层，首次无文件时会按 `ProjectSetting` 摘要或章节列表回填；正式 `大纲 / 开篇设计 / 正文章节` 继续走 DB 内容真值
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
- `Studio` 项目文稿文件当前只是工作台文件层，不替代 `contents + content_versions`；它更适合设定、附录、章节规划和自由整理文稿，正式大纲 / 开篇设计 / 正文章节仍走内容主链
- 投影视图（`character_profile` / `world_setting`）统一由 `project` 边界提供，不在 context / content 各自维护
- `ProjectSetting` 当前正式降级为“结构化摘要真值”：用于快速浏览、机器投影和默认值，不再因为字段缺口阻塞大纲/开篇/正文；但摘要一旦实质变更，已确认的大纲、开篇设计、章节任务和正文仍会按 impact 标记为 stale
- stale chapter task 必须先重建章节计划，不可直接编辑；前后端同步强制
- endpoint 安全策略必须同时落在写入入口和运行时出口
- 程序化 Alembic 优先复用现有 `connection` / `engine`，不要退回字符串化 URL
- config_registry 对外暴露语义化 DTO，写回前必须 staged full-config 校验，未知字段直接失败
- `assistant runtime` 当前采用显式 `agent_id/skill_id + hook_ids` 装配，不把配置自动全局注入任意对话；`mcp` 当前通过 hook/plugin 路径可执行，agent 通用 tool-calling 仍是下一阶段
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

- 2026-03-26：完成 provider interop、本地 probe、assistant runtime 与 workflow hooks runtime 的第一轮真实闭环；运行时显式暴露错误，不做静默降级。
- 2026-03-27：完成 Workspace / Studio / Engine 的一轮布局收口，工作台侧栏、页头骨架、状态区和移动端细节已统一。
- 2026-03-28：assistant 配置主真值切到 `apps/api/.runtime/assistant-config/`，多用户体验改为“AI 助手 / 模型连接”双入口，并补齐未保存离开保护。
- 2026-03-29：修复本地 SQLite 开发库迁移卡死导致的“页面一直加载中”；登录、项目大厅、AI 聊天、模型连接页恢复。
- 2026-03-29：完成用户自定义 Skills 闭环，真值文件落到 `users/<user_id>/skills/<skill_id>/SKILL.md`；聊天页可直接切换 Skill。
- 2026-03-29：完成用户自定义 MCP + Hook(mcp) 闭环，真值文件落到 `users/<user_id>/mcp_servers/<server_id>/MCP.yaml`；Hook 可直接绑定用户 MCP。
- 2026-03-30：继续按 Claude 风格收口前端主路径，保留“长期规则 + Skills + 模型连接”为默认心智，`Agents / Hooks / MCP` 进入更明确的次级区域。
- 2026-03-30：补齐项目级 Skills / MCP，文件真值落到 `projects/<project_id>/skills/<skill_id>/SKILL.md` 与 `projects/<project_id>/mcp_servers/<server_id>/MCP.yaml`，运行时按 `项目 -> 用户 -> 系统` 解析；浏览器已实测 `Skills -> MCP` 无输入切换不再弹未保存提示。
