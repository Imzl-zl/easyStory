# easyStory AGENTS

## 0. 实施基线

- 环境：Windows 11
- Python：3.13
- 后端技术栈：FastAPI、SQLAlchemy 2、Pydantic 2
- 配置根目录：`config/`
- 后端标准验证命令：`cd apps/api && ruff check app tests && pytest -q`

## 1. 作用

- 本文件是项目级**硬规则**，只保留需要长期约束实现结构的内容。
- 详细架构说明、字段设计、流程细节不放在这里，统一放 `docs/`。
- 目标：约束结构，避免所有逻辑堆到一个地方，避免双真值和后期维护失控。

## 2. Source of Truth

发生冲突时，按以下优先级执行：

1. `docs/specs/architecture.md`
2. `docs/specs/database-design.md`
3. `docs/specs/config-format.md`
4. 相关 `docs/design/*.md`
5. 相关 `docs/plans/*.md`
6. 本文件

说明：

- 本文件负责“项目规则”。
- `docs/specs` 和 `docs/design` 负责“正式设计”。
- 本文件不得扩展出第二套架构真值。
- 项目根 `tools.md` / `memory.md` 只作为代理协作恢复与知识沉淀辅助，不得覆盖正式设计真值。

## 3. 架构基线

- 本项目采用**模块化单体**，不是微服务优先。
- 后端正式实现边界以 `Entry -> Service -> Engine -> Infrastructure` 为准。
- “按业务模块分域”是对上述 4 层的补充约束，不是替代。
- 任何新实现都必须同时满足：
  - 分层清晰
  - 按业务域分模块
  - 真值源唯一

## 4. 模块规则

后端按业务域拆分，至少包含以下模块：

- `project`：项目与 `ProjectSetting`
- `content`：`Outline / OpeningPlan / Chapter / ContentVersion`
- `workflow`：工作流执行、节点执行、章节任务、过程产物
- `review`：审核与精修
- `context`：上下文注入与 Story Bible
- `analysis`：小说分析与分析结果
- `credential`：模型凭证与系统默认凭证池策略
- `billing`：token、成本、预算
- `export`：导出
- `observability`：执行日志、审计、Prompt 回放
- `config_registry`：YAML 配置加载、缓存、校验

规则：

- 一个业务规则只能有一个主归属模块。
- 一个数据表只能有一个主归属模块。
- 禁止把跨模块编排逻辑和具体业务规则混写在一起。

## 5. 目录规则

根目录职责：

- `apps/api`：后端
- `apps/web`：前端
- `config`：Skills / Agents / Hooks / Workflows YAML
- `docs`：需求、设计、规格、计划
- `tools.md`：项目协作知识、常用命令、模式、坑点
- `memory.md`：项目近期任务、决策、问题与当前状态日志

后端目标结构：

```text
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

必须遵守：

- ORM 基类统一放在 `apps/api/app/shared/db/base.py`
- ORM 模型统一放在 `apps/api/app/modules/<module>/models/`
- `apps/api/app/modules/model_registry.py` 只负责 ORM 注册，不承载业务逻辑
- 不再保留根级 `apps/api/app/models` 作为聚合层或兼容层
- 不允许继续把业务代码放回根级 `service / engine / infrastructure / schemas`

## 6. Agent 协作文件规则

- 开始任务前，优先检查项目根 `tools.md` 与 `memory.md` 是否存在；存在时先读，再进入大范围搜索或改动。
- 只读取当前项目根的协作文件，不引入额外全局目录协议，不无目的批量加载。
- `tools.md` 只记录可复用的项目协作知识、命令、模式和坑点；允许整理重写，但写入前必须先读。
- `memory.md` 只记录本项目近期任务、关键决策、问题和当前状态；必须仅追加，禁止覆盖历史；写入前必须先读。
- `tools.md` / `memory.md` 属于协作辅助，不是产品功能真值，不得与 `docs/specs`、`docs/design`、`docs/plans`、`config` 和当前代码冲突。
- 发生冲突时，以正式设计、配置和当前代码为准；协作文件只负责帮助恢复上下文，不负责改写正式规则。
- 完成任务、做出关键决策或解决关键问题后，应把必要信息追加到 `memory.md`；反复验证的稳定规律再整理进 `tools.md` 或正式文档。

## 7. 分层依赖规则

固定依赖方向：

```text
api -> service -> engine -> infrastructure
service -> domain logic
engine -> domain logic
infrastructure -> domain models
```

补充约束：

- `api` 不写核心业务规则
- `service` 不依赖 HTTP 请求/响应对象
- `engine` 负责流程执行，不吞掉业务域内部规则
- `infrastructure` 不决定业务规则
- 模块之间只能通过显式接口、DTO、应用服务交互
- 禁止跨模块直接操作对方内部持久化细节

## 8. shared / core 规则

`shared` 或当前 `core` 只允许放真正跨模块复用的基础设施：

- 配置加载基础能力
- 数据库基类、会话、事务封装
- 通用异常
- 通用日志、事件
- 小型纯工具函数

禁止放：

- 项目规则
- 内容状态流转
- 审核策略
- 凭证优先级逻辑
- 导出业务判断

如果某段逻辑只服务一个业务域，就必须回到对应模块。

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

## 11. 前端规则

- 前端放在 `apps/web`
- 页面负责路由和装配
- 业务交互按 feature / module 拆分
- 共享组件只放复用 UI
- 远程状态与本地交互状态分离

## 12. 文档同步规则

以下变化必须同步更新本文件与对应 `docs/`：

- 架构分层变化
- 模块边界变化
- 表归属变化
- 真值源变化
- 新增或废弃核心目录
- 新增关键跨模块约束

最低要求：

- 架构变更：更新 `docs/specs/architecture.md`
- 数据边界变更：更新 `docs/specs/database-design.md`
- 配置边界变更：更新 `docs/specs/config-format.md`
- 实施路线变更：更新相关 `docs/plans/*.md`

## 13. 禁止事项

- 禁止把新业务继续堆进全局 `models` / `services`
- 禁止跨模块直接读写对方内部状态
- 禁止在 `workflow` 中硬编码内容、审核、导出细节
- 禁止把 `shared/core` 做成大杂烩
- 禁止一个业务概念在多个位置重复定义
- 禁止修改正式设计后不更新本文件
- 禁止把 `tools.md` / `memory.md` 当成正式设计替代品
- 禁止静默覆盖 `memory.md` 历史记录
- 禁止跨项目混写协作记忆

## 14. 维护原则

- 本文件必须保持**短、小、硬**。
- 适合放进每次会话读取的只有规则，不是大段说明。
- 项目记忆与阶段性状态不进入本文件；近期状态进 `memory.md`，可复用协作知识进 `tools.md`，正式设计进 `docs/`。
- 当本文件接近 200 行时，优先删除重复规则，并把解释性内容迁回 `docs/specs`、`docs/design`、`docs/plans`。
- 发现本文件过长或承载了应放入 `docs/` 的内容时，应主动压缩。
