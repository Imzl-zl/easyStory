# easyStory 项目状态

> 本文件是当前状态快照 + 最近活跃窗口，允许覆盖更新。
> 完整历史归档见 `memory/archive/`，稳定规律见 `tools.md`。

## 当前基线

- 后端测试：最近一次已知全量 `cd apps/api && ruff check app tests && pytest -q` 通过（记录日期：2026-03-23）
- 前端检查：最近一次已知 `pnpm --dir apps/web exec tsc --noEmit` + `pnpm --dir apps/web lint` 通过（记录日期：2026-03-23）
- 最后更新：2026-03-24

## 已完成能力

- 凭证与模型连接闭环：安全存储、endpoint policy、`api_dialect` 路由、旧库 schema reconcile
- 项目与前置资产闭环：project CRUD、setting completeness、story asset generation / confirm
- 内容主链路闭环：outline / opening_plan / chapter / content version、章节确认与 stale 传播
- 工作流闭环：control plane、runtime、auto-review / fix、workflow logs / prompt replay / audit
- context / review / billing / export / analysis 已补到查询面板或最小业务闭环
- template + incubator 闭环：built-in sync、自定义模板、draft / create-project / conversation draft、完整度前移
- config_registry 管理闭环：skills / agents / hooks / workflows 查询与 detail / update，strict DTO + staged config 校验
- 数据库演进闭环：Alembic baseline，startup 与文件型 SQLite helper 优先走 Alembic
- Web 工作台基座已可用：Engine / Studio、stale 章节引导层

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

## 最近活跃窗口（2026-03-22 ~ 03-24）

- 2026-03-22：完成 review follow-up、模型连接方言化、Alembic 初始迁移与 DB 初始化链收口
- 2026-03-23：完成 config_registry skills / agents / hooks / workflows detail / update 闭环，并收口 strict DTO + staged validation
- 2026-03-23：完成 template 自定义模板、incubator draft / create-project / conversation draft 与完整度前移
- 2026-03-24：收口协作文件边界：`AGENTS.md` 管规则，`tools.md` 管稳定知识，`memory.md` 管当前快照；`docs/` 改为按需查
