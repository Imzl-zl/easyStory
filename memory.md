# easyStory 项目状态

> 本文件是当前状态快照 + 最近活跃窗口，允许覆盖更新。
> 完整历史归档见 `memory/archive/`，稳定规律见 `tools.md`。

## 当前基线

- 后端测试：最近一次已知全量 `cd apps/api && ruff check app tests && pytest -q` 通过（记录日期：2026-03-23）
- 前端检查：最近一次已知 `pnpm --dir apps/web exec tsc --noEmit` + `pnpm --dir apps/web lint` + `pnpm --dir apps/web test:unit` 通过（记录日期：2026-03-25）
- 最后更新：2026-03-25

## 已完成能力

- 凭证与模型连接闭环：安全存储、endpoint policy、`api_dialect` 路由、旧库 schema reconcile
- 项目与前置资产闭环：project CRUD、setting completeness、story asset generation / confirm
- 内容主链路闭环：outline / opening_plan / chapter / content version、章节确认与 stale 传播
- 工作流闭环：control plane、runtime、auto-review / fix、workflow logs / prompt replay / audit
- context / review / billing / export / analysis 已补到查询面板或最小业务闭环
- template + incubator 闭环：built-in sync、自定义模板、draft / create-project / conversation draft、完整度前移
- config_registry 管理闭环：skills / agents / hooks / workflows 查询与 detail / update，strict DTO + staged config 校验
- 数据库演进闭环：Alembic baseline，startup 与文件型 SQLite helper 优先走 Alembic
- Web 工作台主子视图已基本路由化：Lobby / Incubator / Template Library / Recycle Bin / Settings / Studio / Engine

## 进行中 / 未完成

- 前端更多页面和交互完善

## 当前仍有效的关键决策

- `provider` 负责渠道 / 凭证解析，协议由 `api_dialect` 决定，模型缺省由 `default_model` 决定
- 正文真值只在 `contents + content_versions`；`artifacts`、运行时摘要或预览结果都不是正文主真值
- 投影视图（`character_profile` / `world_setting`）统一由 `project` 边界提供，不在 context / content 各自维护
- stale chapter task 必须先重建章节计划，不可直接编辑；前后端同步强制
- endpoint 安全策略必须同时落在写入入口和运行时出口
- 程序化 Alembic 优先复用现有 `connection` / `engine`，不要退回字符串化 URL
- config_registry 对外暴露语义化 DTO，写回前必须 staged full-config 校验，未知字段直接失败

## 仍需注意的坑点

- aiosqlite 沙箱挂起不是业务回归（0.21.0 / 0.22.1 非沙箱都正常）
- unified exec 进程数告警是工具层会话配额问题，不是仓库代码回归
- workflow_snapshot 恢复需剥离运行时扩展字段，否则 WorkflowConfig extra key 校验失败
- PromptReplay.response_text 是文本列，结构化 LLM 响应需先 JSON 序列化再落库
- DB 事务 + 文件系统副作用：先 commit 再做不可回滚的文件删除
- async 语义审查不要误把基础设施命名（AsyncSessionFactory 等）当待清理对象
- shared/runtime 改为惰性导出，避免 settings -> runtime -> llm tool provider 循环导入

## 最近活跃窗口（2026-03-22 ~ 03-25）

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
