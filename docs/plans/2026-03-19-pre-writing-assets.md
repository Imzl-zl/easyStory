# easyStory 前置创作资产实施计划

> 文档状态：历史实施记录
>
> 当前正式边界请以 [前置创作资产](../design/19-pre-writing-assets.md)、[创作设定](../design/06-creative-setup.md)、[系统架构设计](../specs/architecture.md) 和当前代码为准。本计划保留为当时的实施拆解，不单独代表当前真值。

**Goal:** 为 easyStory 增加“前置创作资产”能力，明确并落地 `ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter` 的标准创作链路，提升章节生成稳定性和前几章质量。

**Source of Truth:** [前置创作资产](../design/19-pre-writing-assets.md)、[创作设定](../design/06-creative-setup.md)、[上下文注入](../design/02-context-injection.md)、[章节生成](../design/04-chapter-generation.md)。与本计划有冲突时，以设计文档为准。

---

## 1. 已定设计边界

1. 世界观设定和角色设定归属 `ProjectSetting`，不新增第二套真值源
2. `Outline` 是章节拆分前的独立确认产物
3. “黄金开头”统一收敛为 `OpeningPlan`，它是结构化阶段约束，不是正文
4. 章节上下文按“长期约束 / 阶段约束 / 当前执行”分层注入
5. 新项目从零开始生成正文前，默认先确认 `Outline` 与 `OpeningPlan`
6. MVP 中 `Outline` 与 `OpeningPlan` 优先复用 `Content + ContentVersion`，不急着拆新表

---

## 2. 范围与非目标

### 2.1 范围

- `ProjectSetting` 结构补齐：世界观与角色设定的结构化边界
- `Outline` / `OpeningPlan` 的产物与审批链路
- `chapter_split` 对 `Outline + OpeningPlan` 的依赖
- `ContextBuilder` 的阶段化注入规则
- 服务层 / API / UI 中与前置创作资产直接相关的入口

### 2.2 非目标

- 不在本计划中引入独立的“角色数据库”“世界观数据库”
- 不做自动小说策划全量代理化
- 不在 MVP 内实现复杂的剧情分析或自动开篇评分系统

---

## 3. 实施阶段

### Phase 1: 资产建模与存储表示

**目标：** 先把数据边界定稳，避免后续一边写代码一边改模型。

#### Task 1: 收敛 `ProjectSetting` 结构

交付：

- 明确 `ProjectSetting` 中的世界观、角色、核心冲突、规模字段
- `character_profile` / `world_setting` 改为从 `ProjectSetting` 投影的上下文视图

验收：

- 文档和 Schema 中不再出现“角色设定是另一套主数据”的表述
- 完整度检查可直接针对 `ProjectSetting` 执行

#### Task 2: 确定 `Outline` / `OpeningPlan` 的存储方式

最优选择：

- 两者都作为 `Content` 类型保存
- 正文继续走 `ContentVersion`
- `OpeningPlan` 修改必须创建新版本

验收：

- `Outline` 与 `OpeningPlan` 都能被版本化
- 不新增不必要的独立主表

### Phase 2: 工作流与审批关口

**目标：** 把“先想清楚再批量生成”变成系统默认路径。

#### Task 3: 补齐工作流节点链路

标准节点：

```text
outline -> opening_plan -> chapter_split -> chapter_gen
```

要求：

- `opening_plan` 依赖 `outline`
- `chapter_split` 依赖 `outline + opening_plan`
- 新项目默认不允许直接从空设定跳到 `chapter_gen`

#### Task 4: 增加确认关口

要求：

- `Outline` 需要确认后才能进入 `OpeningPlan`
- `OpeningPlan` 需要确认后才能执行 `chapter_split`
- 导入已有项目或从中途续写时，允许显式记录跳过原因

### Phase 3: ContextBuilder 与 Prompt 注入

**目标：** 让前置资产真正进入生成链路，而不是只停留在页面或文档层。

#### Task 5: 增加 `opening_plan` 注入类型

要求：

- ContextBuilder 支持 `opening_plan`
- 默认在第 1-3 章高优先级注入
- 第 4 章后降级为按需引用

#### Task 6: 分层注入策略落地

分层：

- 长期约束：`project_setting` / `character_profile` / `world_setting` / `outline` / `story_bible`
- 阶段约束：`opening_plan` / 当前阶段目标 / 近期伏笔
- 当前执行：`chapter_task` / `previous_chapters` / `chapter_summary`

验收：

- `chapter_task` 保持当前章最高优先级
- `OpeningPlan` 不会长期挤占中后期上下文预算

### Phase 4: 服务层与 API

**目标：** 提供用户可以真实操作的服务接口，而不是只在引擎内部假设资产存在。

#### Task 7: Project / Outline / OpeningPlan 服务能力

至少包括：

- 创建和更新 `ProjectSetting`
- 生成、保存、确认 `Outline`
- 生成、保存、确认 `OpeningPlan`
- 在上游资产变更后重新触发 `chapter_split`

#### Task 8: API 路由补齐

建议接口分组：

- `POST /projects/{id}/setting/complete-check`
- `POST /projects/{id}/outline/generate`
- `POST /projects/{id}/outline/approve`
- `POST /projects/{id}/opening-plan/generate`
- `POST /projects/{id}/opening-plan/approve`
- `POST /projects/{id}/chapter-tasks/regenerate`

### Phase 5: 前端交互与验证

**目标：** 让“前置创作资产”成为清晰可操作的创作流程，而不是隐藏机制。

#### Task 9: 创作准备区 UI

页面顺序建议：

```text
项目设定 -> 大纲 -> 开篇设计 -> 章节任务 -> 正文
```

要求：

- 每一步都展示当前状态：未开始 / 草稿 / 待确认 / 已确认
- 让用户清楚知道自己卡在哪个关口

#### Task 10: 验证与回归

必须覆盖：

- 新项目从零开始的完整链路
- 修改 `ProjectSetting` 后对 `Outline` / `OpeningPlan` / `ChapterTask` 的影响
- 前 1-3 章正确注入 `OpeningPlan`
- 第 4 章以后 `OpeningPlan` 不再长期高优先级注入
- 导入已有项目时的跳过开篇设计路径

---

## 4. 与现有后端核心计划的衔接

本计划不替代 [后端核心实施计划（V2）](./2026-03-17-backend-core-v2.md)，而是补充其以下部分：

| 本计划 | 后端核心计划中的对应位置 |
|------|----------------------|
| `ProjectSetting` 结构收敛 | 数据模型层 / ProjectService |
| `Outline` / `OpeningPlan` 版本化 | Content / ContentVersion 相关任务 |
| `opening_plan` 注入类型 | ContextBuilder 相关任务 |
| `outline -> opening_plan -> chapter_split -> chapter_gen` | WorkflowEngine / WorkflowService |
| 开篇设计审批接口 | API 层内容与工作流相关任务 |

---

## 5. 完成标准

- 设计文档、实施计划、索引和架构描述全部采用同一条标准创作链路
- 新项目默认存在 `Outline` 与 `OpeningPlan` 两个明确确认关口
- 章节生成的上下文策略已经区分长期约束、阶段约束和当前执行
- 没有引入新的多套真值源或过度建模

---

*最后更新: 2026-03-19*
