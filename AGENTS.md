# easyStory AGENTS

## 0. 实施基线
- 环境：Windows 11 / Ubuntu 24.04
- Python：3.13
- 后端技术栈：FastAPI、SQLAlchemy 2、Pydantic 2
- 配置根目录：`config/`
- 后端标准验证命令：`cd apps/api && ruff check app tests && pytest -q`

## 1. 作用
- 本文件只保留长期有效的项目级硬规则。
- 详细架构、字段设计、流程细节统一放 `docs/`。
- 目标：约束结构，避免逻辑堆积、双真值和后期维护失控。

## 2. Source of Truth
发生冲突时，按以下优先级执行：
1. `docs/specs/architecture.md`
2. `docs/specs/database-design.md`
3. `docs/specs/config-format.md`
4. 相关 `docs/design/*.md`
5. 相关 `docs/plans/*.md`
6. 本文件
- 本文件只负责项目规则，不得扩展出第二套架构真值。
- `docs/specs` 和 `docs/design` 负责正式设计。
- 项目根 `tools.md` / `memory.md` 只作为代理协作恢复与知识沉淀辅助，不得覆盖正式设计真值。

## 3. 架构基线
- 本项目采用**模块化单体**，不是微服务优先。
- 后端正式实现边界以 `Entry -> Service -> Engine -> Infrastructure` 为准；按业务模块分域是补充约束，不是替代。
- 任何新实现都必须同时满足：分层清晰、按业务域分模块、真值源唯一。

## 4. 模块规则
- 后端按业务域拆分，至少包含以下模块：
- `project`：项目与 `ProjectSetting`
- `content`：`Outline / OpeningPlan / Chapter / ContentVersion`
- `workflow`：工作流执行、节点执行、章节任务、过程产物
- `assistant`：非 workflow 的通用对话运行时、skill/hook/mcp 能力装配
- `review`：审核与精修
- `context`：上下文注入与 Story Bible
- `analysis`：小说分析与分析结果
- `credential`：模型凭证与系统默认凭证池策略
- `billing`：token、成本、预算
- `export`：导出
- `observability`：执行日志、审计、Prompt 回放
- `config_registry`：YAML 配置加载、缓存、校验
- 一个业务规则只能有一个主归属模块。
- 一个数据表只能有一个主归属模块。
- 禁止把跨模块编排逻辑和具体业务规则混写在一起。

## 5. 目录规则
- 根目录职责：
- `apps/api`：后端
- `apps/web`：前端
- `config`：Skills / Agents / Hooks / MCP Servers / Workflows YAML
- `docs`：需求、设计、规格、计划
- `tools.md`：项目协作知识、常用命令、模式、坑点
- `memory.md`：项目当前状态快照与最近活跃窗口
- `memory/archive/`：按月归档的完整历史日志
- 后端目标结构：
```text
apps/api/
  alembic/
    versions/
apps/api/app/
  entry/
  shared/
    db/
  modules/
    model_registry.py
    <module>/
      entry/
      models/
      service/
      engine/
      infrastructure/
      schemas/
```
- 必须遵守：
- 数据库迁移资产统一放在 `apps/api/alembic/`
- ORM 基类统一放在 `apps/api/app/shared/db/base.py`
- ORM 模型统一放在 `apps/api/app/modules/<module>/models/`
- `apps/api/app/modules/model_registry.py` 只负责 ORM 注册，不承载业务逻辑
- `apps/api/app/shared/db/bootstrap.py` 只负责开发期初始化与遗留 schema reconcile；正式结构演进入口是 Alembic revision
- 不再保留根级 `apps/api/app/models` 作为聚合层或兼容层
- 不允许继续把业务代码放回根级 `service / engine / infrastructure / schemas`

## 6. Agent 协作文件规则
- 开始任务前，若项目根存在 `tools.md` / `memory.md`，则先读；`memory/archive/` 只在需要追根因、恢复关键历史或核对旧决策时按需读取。
- `AGENTS.md` 只保留项目级硬规则，不写项目知识和阶段状态。
- `tools.md` 只记录跨会话仍有效的协作知识：稳定命令、关键入口、可复用模式、长期坑点。
- `memory.md` 只保留**当前状态快照 + 最近活跃窗口**，整体覆盖更新，不追加流水账；目标 ≤100 行，硬限制 ≤120 行。
- `docs/` 是正式设计真值，但按需读取；协作文件信息不足，或与正式设计、配置、当前代码疑似冲突时，再查对应 `docs/`。
- 写入前先判断归属：规则进 `AGENTS.md`，稳定知识进 `tools.md`，当前状态进 `memory.md`，重要历史根因进 `memory/archive/`。
- 完成一个完整功能 / 修复闭环后再更新协作文件，不为每个小改动单独写一轮。
- `memory/archive/` 只记录重要根因、关键决策、非显然踩坑和后续恢复必需上下文；格式保持 `## [日期 | 标题]` + `Events / Changes / Insights`。
- 反复验证后仍长期有效的规律，整理进 `tools.md` 或正式文档，不留在 `memory.md` 或归档中重复。
- `tools.md` / `memory.md` 只用于协作恢复与上下文维护，不改写正式设计；发生冲突时，以 `docs/`、配置和当前代码为准。

## 7. 分层依赖规则
固定依赖方向：
```text
api -> service -> engine -> infrastructure
service -> domain logic
engine -> domain logic
infrastructure -> domain models
```
- `api` 不写核心业务规则
- `service` 不依赖 HTTP 请求 / 响应对象
- `engine` 负责流程执行，不吞掉业务域内部规则
- `infrastructure` 不决定业务规则
- 模块之间只能通过显式接口、DTO、应用服务交互
- 禁止跨模块直接操作对方内部持久化细节

## 8. shared / core 规则
- `shared` 或当前 `core` 只允许放真正跨模块复用的基础设施：配置加载基础能力、数据库基类 / 会话 / 事务封装、通用异常、通用日志 / 事件、小型纯工具函数。
- 禁止放项目规则、内容状态流转、审核策略、凭证优先级逻辑、导出业务判断。
- 如果某段逻辑只服务一个业务域，就必须回到对应模块。

## 9. workflow 特别规则
- `workflow` 只负责编排、状态机、执行记录、恢复语义。
- `workflow` 不拥有内容规则、审核规则、上下文规则、导出规则的最终定义权。
- `workflow` 通过调用 `content/review/context/export` 的公开服务完成协作。

## 10. 真值源规则
- `ProjectSetting` 是项目设定真值源
- `contents + content_versions` 是正文真值源
- `artifacts` 不是正文真值源
- 配置缓存表不是业务主真值源
- 同一业务概念禁止出现两套并行真值源

## 11. 实现尺度规则
- 这些规则用于压制职责堆积，不是为了机械卡行数；先看职责数和耦合度，再看纯行数。
- 函数目标 `<= 50` 行；超过即优先抽纯函数、helper 或局部状态钩子，避免继续加分支。
- 文件目标分档执行：
- `<= 200` 行：常态，优先保持在这个区间。
- `200-300` 行：允许，但提交前必须确认没有把视图、状态、请求、映射混写在一起。
- `300-450` 行：只允许出现在高信息密度文件，如 `schema/type mapping`、复杂页面装配层、状态 `store/model/support`、长表单 UI；此时必须优先寻找可拆的子组件、support 文件或状态 hook。
- `> 450` 行：视为未收口，除生成文件、协议清单、常量表、测试夹具外，默认要拆分。
- 页面与前端复杂组件默认按 `page/装配`、`view/ui`、`state/model`、`support` 拆分，不要把布局、交互状态、数据拼装和副作用堆在一个文件。
- 例外必须显式：生成文件、协议定义、常量清单、测试夹具可以放宽，但不得夹带业务逻辑；一旦开始承载业务逻辑，仍按上述分档执行。

## 12. 前端规则
- 前端放在 `apps/web`
- 页面负责路由和装配
- 业务交互按 feature / module 拆分
- 共享组件只放复用 UI
- 远程状态与本地交互状态分离
- **文案语言**：
  - 文案面向用户，不写开发者口吻
  - 菜单、按钮、页签、表单标签要短，默认用中文
  - `Skills / Agents / Hooks / MCP / Workflows` 这类正式专有名词保留原名，不乱翻译，不在短标签里中英混搭解释
  - 配置键、字段名、接口名、实现概念不能直接给用户看
  - 便于后续国际化时统一提取到 i18n 配置文件

## 13. 文档同步规则
- 以下变化必须同步更新本文件与对应 `docs/`：架构分层变化、模块边界变化、表归属变化、真值源变化、新增或废弃核心目录、新增关键跨模块约束。
- 最低要求：
- 架构变更：更新 `docs/specs/architecture.md`
- 数据边界变更：更新 `docs/specs/database-design.md`
- 配置边界变更：更新 `docs/specs/config-format.md`
- 实施路线变更：更新相关 `docs/plans/*.md`

## 14. 禁止事项
- 禁止把新业务继续堆进全局 `models` / `services`
- 禁止跨模块直接读写对方内部状态
- 禁止在 `workflow` 中硬编码内容、审核、导出细节
- 禁止把 `shared/core` 做成大杂烩
- 禁止一个业务概念在多个位置重复定义
- 禁止修改正式设计后不更新本文件
- 禁止把 `tools.md` / `memory.md` 当成正式设计替代品
- 禁止跨项目混写协作记忆

## 15. 维护原则
- 本文件必须保持**短、小、硬**，适合每次会话预读。
- 项目记忆与阶段性状态不进入本文件；近期状态进 `memory.md`，可复用协作知识进 `tools.md`，正式设计进 `docs/`。
- 当本文件接近 200 行时，优先删除重复规则，并把解释性内容迁回 `docs/specs`、`docs/design`、`docs/plans`。
- 发现本文件过长或承载了应放入 `docs/` 的内容时，应主动压缩。
