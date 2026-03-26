# easyStory 数据库设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术设计 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-14 |
| 更新时间 | 2026-03-19 |
| 关联文档 | [系统架构设计](./architecture.md) |

---

## 1. 实体关系

> 约定：本节以**物理表名**为准，括号内标注领域对象名称；后文 SQL 示例也统一使用物理表名（如 `contents`、`workflow_executions`）。

```
projects (Project，项目)
  ├── 1:N → contents (Content，内容)
  │         └── 1:N → content_versions (版本)
  ├── 1:N → analyses (Analysis，分析结果)
  ├── 1:N → workflow_executions (WorkflowExecution，工作流执行)
  │         └── 1:N → node_executions (NodeExecution，节点执行)
  │                   ├── 1:N → artifacts (Artifact，产物)
  │                   └── 1:N → review_actions (ReviewAction，审核动作)
  ├── 1:N → exports (Export，导出)
  └── N:1 → templates (Template，模板)
            └── 1:N → template_nodes (TemplateNode，模板节点)

独立配置（不与项目直接关联）：
skills (Skill，技能)
hooks (Hook，钩子)
agents (Agent，智能体)
```

---

## 2. 数据表设计

### 核心业务表

**projects（Project，项目）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| name | VARCHAR(255) | 项目名称 |
| genre | VARCHAR(100) | 题材 |
| target_words | INTEGER | 目标字数 |
| status | VARCHAR(50) | 状态：draft/active/completed/archived |
| template_id | UUID | 模板 ID |
| owner_id | UUID | 所属用户 ID（FK → users.id） |
| deleted_at | TIMESTAMP | 软删除时间（回收站） |
| project_setting | JSONB | 项目设定（ProjectSetting，长期约束唯一真值源） |
| allow_system_credential_pool | BOOLEAN | 是否允许解析到系统级默认凭证池，默认 false |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

> `project_setting` 在 MVP 中直接承载结构化 `ProjectSetting` 文档，不作为运行态杂项配置大杂烩。运行时快照、模板配置和节点临时参数应分别进入 `workflow_snapshot`、`Template.config`、`NodeExecution.input/output` 等边界明确的位置。
>
> 当前 `ProjectSetting` 采用固定 schema：`genre`、`sub_genre`、`target_readers`、`tone`、`core_conflict`、`plot_direction`、`protagonist`、`key_supporting_roles`、`world_setting`、`scale`、`special_requirements`。禁止继续写入 `worldview`、`target_length` 等模糊旧键。
>
> `allow_system_credential_pool` 是显式安全开关，默认关闭；仅当该值为 `true` 时，凭证解析才允许继续回退到系统级默认凭证池。

**contents（Content，内容）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| parent_id | UUID | 父内容 ID（支持内容层级关系，可为 NULL） |
| content_type | VARCHAR(50) | 类型：outline/opening_plan/chapter |
| title | VARCHAR(255) | 标题 |
| chapter_number | INTEGER | 章节号（章节类型时有效） |
| order_index | INTEGER | 排序索引（用于章节顺序） |
| status | VARCHAR(50) | 状态：draft/approved/stale/archived |
| metadata | JSONB | 元数据（标签、备注等） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| last_edited_at | TIMESTAMP | 最后编辑时间 |

> `character_profile` 与 `world_setting` 在 MVP 中作为 `ProjectSetting` 的结构化投影参与上下文注入，不作为独立 `Content` 主类型存储。
>
> 硬约束：
> - 同一 `project_id` 最多只允许一个 `outline` 容器
> - 同一 `project_id` 最多只允许一个 `opening_plan` 容器
> - `chapter` 的逻辑身份由 `(project_id, chapter_number)` 唯一标识
> - `chapter_number` 仅 `content_type='chapter'` 时允许非空，且必须大于 0

**content_versions（版本快照）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| content_id | UUID | 内容 ID |
| version_number | INTEGER | 版本号（递增） |
| content_text | TEXT | 内容快照（全量存储） |
| change_summary | TEXT | 变更摘要 |
| created_by | VARCHAR(50) | 创建者：system/user/ai_assist/auto_fix/ai_partial |
| change_source | VARCHAR(50) | 变更来源：user_edit/ai_generate/ai_fix/import |
| word_count | INTEGER | 该版本字数 |
| context_snapshot_hash | VARCHAR(64) | 生成时上下文快照的 SHA-256（用于溯源） |
| ai_conversation_id | UUID | AI 生成/精修时的会话 ID（可选） |
| is_current | BOOLEAN | 是否当前版本（默认 true；创建新版本时旧版本置 false） |
| is_best | BOOLEAN | 是否用户选择的最佳版本（同一 Content 最多一条 true） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

> v0.1 采用全量快照，v0.2 可按需迁移为增量差异存储。
>
> 字段说明：
> - `created_by`：记录"谁做的"操作者身份（system/user/ai_assist/auto_fix/ai_partial）
> - `change_source`：记录"变更动因"（user_edit/ai_generate/ai_fix/import），两个字段职责互补，不冗余
>
> 硬约束：
> - `UNIQUE (content_id, version_number)`
> - 同一 `content_id` 最多一条 `is_current=true`
> - 同一 `content_id` 最多一条 `is_best=true`

**analyses（Analysis，分析结果）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| content_id | UUID | 内容 ID（可选，分析特定内容时使用） |
| analysis_type | VARCHAR(50) | 分析类型：plot/character/style/pacing/structure |
| source_title | VARCHAR(255) | 来源标题快照（可选） |
| analysis_scope | JSONB | 分析范围快照（章节范围/采样策略/采样结果） |
| result | JSONB | 分析结果（结构化数据） |
| suggestions | JSONB | 改进建议 |
| generated_skill_key | VARCHAR(100) | 自动生成的 Skill 逻辑 ID（可选，对应 `skills.skill_id`） |
| created_at | TIMESTAMP | 创建时间 |

> 支持"小说分析功能"和"分析自动生成 Skill"核心需求。`source_title` 与 `analysis_scope` 用于保留最小可追溯输入快照，避免原始文件按保留策略清理后无法解释分析结果来源。
>
> 若分析结果落地为 Skill，业务记录应引用配置层的逻辑 `skill_id`，而不是配置缓存表的 UUID 主键，避免把缓存层误当主数据。

> Schema 演进边界：正式数据库结构变更通过 `apps/api/alembic/` 下的 Alembic revision 管理；`shared/db/bootstrap.py` 仅保留开发期初始化与遗留库最小 reconcile，不再作为长期 schema 演进真值。

**templates（Template，模板）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| name | VARCHAR(255) | 模板名称 |
| description | TEXT | 描述 |
| genre | VARCHAR(100) | 适用题材 |
| config | JSONB | 模板级默认配置（仅静态默认值） |
| is_builtin | BOOLEAN | 是否内置模板 |
| created_at | TIMESTAMP | 创建时间 |

**template_nodes（TemplateNode，模板节点）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| template_id | UUID | 模板 ID |
| node_order | INTEGER | 节点顺序 |
| node_type | VARCHAR(50) | 类型：generate/review/export |
| skill_id | VARCHAR(100) | 技能 ID |
| config | JSONB | 节点静态默认配置（与 workflow node shape 对齐） |
| position_x | INTEGER | 节点 X 坐标（工作流可视化用） |
| position_y | INTEGER | 节点 Y 坐标（工作流可视化用） |
| ui_config | JSONB | UI 展示配置（颜色、图标等） |

> `Template.config` 只保存模板级默认值，例如推荐 workflow、引导问题、默认导出参数；不得写入项目私有数据、运行时状态或执行快照。
>
> `TemplateNode.config` 只保存节点静态默认配置；用户在项目内的修改应进入项目上下文或 `workflow_snapshot`，不回写模板。

---

### 工作流表

**workflow_executions（WorkflowExecution，工作流执行）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| template_id | UUID | 模板 ID |
| status | VARCHAR(50) | 状态：created/running/paused/completed/failed/cancelled |
| current_node_id | VARCHAR(200) | 当前节点 ID（来自 workflow 配置） |
| pause_reason | VARCHAR(50) | 暂停原因：user_request/user_interrupted/budget_exceeded/review_failed/error/loop_pause/max_chapters_reached |
| resume_from_node | VARCHAR(200) | 恢复时从哪个节点 ID 继续 |
| snapshot | JSONB | 暂停时的运行时快照（最小 Schema 见下） |
| workflow_snapshot | JSONB | 启动时工作流配置快照（不可变） |
| skills_snapshot | JSONB | 启动时 Skills 配置快照（不可变） |
| agents_snapshot | JSONB | 启动时 Agents 配置快照（不可变） |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |

> `snapshot` 存放在 `workflow_executions.snapshot` 字段中，用于恢复执行；它是运行时快照，不同于启动时不可变的 `workflow_snapshot / skills_snapshot / agents_snapshot`。
>
> `current_node_id` 与 `resume_from_node` 均使用 workflow 中定义的 `node_id` 字符串，不再混用“节点序号”和“节点 ID”两套口径；展示顺序由 workflow 节点顺序或 `NodeExecution.node_order` 决定。
>
> 业务不变量：同一 `project_id` 同时最多只允许一个 active `WorkflowExecution`（`created` / `running` / `paused`），该约束应落成库级部分唯一索引，服务层只作为补充保护。
>
> 最小建议 Schema：
> ```json
> {
>   "current_node_id": "chapter_gen",
>   "current_node_execution_id": "uuid",
>   "current_sequence": 7,
>   "resume_context": {
>     "chapter_task_id": "uuid",
>     "chapter_number": 7
>   },
>   "completed_nodes": [
>     {"node_id": "outline", "sequence": 0, "status": "completed"}
>   ],
>   "pending_actions": [
>     {"type": "user_decision", "source": "interrupted_generation"}
>   ],
>   "partial_artifacts": [
>     {"content_version_id": "uuid", "created_by": "ai_partial"}
>   ]
> }
> ```

**node_executions（NodeExecution，节点执行）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| workflow_execution_id | UUID | 工作流执行 ID |
| node_id | VARCHAR(200) | 节点 ID（来自 workflow 配置） |
| sequence | INTEGER | 同一 `workflow_execution_id + node_id` 下的执行序号 |
| node_order | INTEGER | 节点顺序（用于 UI 列表排序，可冗余） |
| node_type | VARCHAR(50) | 类型：generate/review/export |
| status | VARCHAR(50) | 状态：pending/running/running_stream/reviewing/fixing/interrupted/completed/failed/skipped |
| input | JSONB | 输入数据 |
| output | JSONB | 输出数据 |
| retry_count | INTEGER | 重试次数（默认 0） |
| error_message | TEXT | 错误信息 |
| execution_time_ms | INTEGER | 执行时间（毫秒） |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |

> 约束：同一 `workflow_execution_id` 下，`(node_id, sequence)` 必须唯一，用于防重复生成与 `resume_workflow` 幂等（详见 `docs/design/17-cross-module-contracts.md`）。
>
> `sequence` 是物理执行序号，不等同于业务上的 `chapter_number`。章节循环的逻辑身份由 `chapter_tasks.chapter_number` 与 `node_executions.input.chapter_task_id / chapter_number` 共同标识；同一章节的重试或手动重跑会创建新的 `NodeExecution` 并分配新的 `sequence`。

**artifacts（Artifact，产物）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| node_execution_id | UUID | 节点执行 ID |
| artifact_type | VARCHAR(50) | 类型：content_version_ref/review_report/context_report/prompt_bundle 等 |
| content_version_id | UUID | 关联内容版本 ID（正式正文/大纲/OpeningPlan 产物时使用，可选，FK → content_versions.id） |
| payload | JSONB | 产物负载（结构化报告、引用信息、轻量文本片段） |
| word_count | INTEGER | 文本型产物字数快照（可选） |
| created_at | TIMESTAMP | 创建时间 |

> `Artifact` 用于执行过程产物追踪，不作为正文真值源。正式的 `outline / opening_plan / chapter` 内容必须落在 `Content + content_versions`；`Artifact` 对这类产物只保留 `content_version_id` 引用或辅助负载。

**review_actions（ReviewAction，审核动作）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| node_execution_id | UUID | 节点执行 ID |
| agent_id | VARCHAR(100) | Agent ID（来自配置，非数据库外键） |
| reviewer_name | VARCHAR(255) | Reviewer 显示名称 |
| review_type | VARCHAR(100) | 审核类型（自由字符串，与 Agent 定义一致） |
| status | VARCHAR(50) | 结果：passed/failed/warning |
| score | NUMERIC(5, 2) | 评分（0-100，可选） |
| summary | TEXT | 审核摘要 |
| issues | JSONB | `ReviewIssue[]` 结构化问题列表 |
| execution_time_ms | INTEGER | 审核耗时（毫秒） |
| tokens_used | INTEGER | 消耗 token 数 |
| created_at | TIMESTAMP | 创建时间 |

> `ReviewAction` 存储的是“单个 reviewer 的结构化审核结果”，字段应与 `ReviewResult` 对齐；聚合结果由运行时聚合器产生，可落在 `NodeExecution.output` 或独立响应 DTO 中。
>
> reviewer 超时、执行异常、返回非法 Schema 等**执行层失败**不属于 `ReviewAction`，应单独作为审核执行失败记录处理，不能伪装成 `issues` 写入本表。

---

### 配置缓存表

> 配置的主数据来源是 YAML 文件（文件系统），以下表用于索引和快速查询，启动时从文件同步。
>
> 模型相关说明：
> - 模型选择与参数在 Skill/Workflow/Node 配置中声明
> - 模型凭证在业务表 `model_credentials` 中加密存储（不走 YAML，不属于配置缓存表）

**skills（Skill，技能）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| skill_id | VARCHAR(100) | 技能唯一标识（来自 YAML） |
| name | VARCHAR(255) | 名称 |
| category | VARCHAR(50) | 分类 |
| config | JSONB | 完整配置快照 |
| file_path | VARCHAR(255) | 对应 YAML 文件路径 |

**hooks（Hook，钩子）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| hook_id | VARCHAR(100) | 钩子唯一标识（来自 YAML） |
| trigger | VARCHAR(50) | 触发时机 |
| action_type | VARCHAR(50) | 动作类型（MVP 内置：script/webhook/agent，通过 PluginRegistry 可扩展） |
| action_config | JSONB | 动作配置 |
| file_path | VARCHAR(255) | 对应 YAML 文件路径 |

**agents（Agent，智能体）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| agent_id | VARCHAR(100) | 智能体唯一标识（来自 YAML） |
| name | VARCHAR(255) | 名称 |
| agent_type | VARCHAR(50) | 类型：writer/reviewer/checker |
| config | JSONB | 完整配置快照 |
| file_path | VARCHAR(255) | 对应 YAML 文件路径 |

---

### 导出表

**exports（Export，导出记录）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| format | VARCHAR(20) | 格式：txt/markdown/docx（pdf 延后，不进入 MVP 枚举） |
| filename | VARCHAR(255) | 文件名 |
| file_path | VARCHAR(500) | 文件路径（相对于导出目录） |
| file_size | INTEGER | 文件大小（字节） |
| config_snapshot | JSONB | 导出配置快照 |
| created_at | TIMESTAMP | 创建时间 |

> 导出文件存储在文件系统，数据库只存路径和元数据。

---

## 3. 索引与唯一约束

### 核心查询索引

```sql
-- contents 表索引与约束
CREATE INDEX idx_contents_project_id ON contents(project_id);
CREATE INDEX idx_contents_type_status ON contents(content_type, status);
CREATE INDEX idx_contents_parent_id ON contents(parent_id);
CREATE INDEX idx_contents_order_index ON contents(order_index);
ALTER TABLE contents
ADD CONSTRAINT ck_contents_chapter_number_by_type
CHECK (
  (
    content_type = 'chapter'
    AND chapter_number IS NOT NULL
    AND chapter_number > 0
  )
  OR (
    content_type IN ('outline', 'opening_plan')
    AND chapter_number IS NULL
  )
);
CREATE UNIQUE INDEX uq_contents_project_outline
ON contents(project_id)
WHERE content_type = 'outline';
CREATE UNIQUE INDEX uq_contents_project_opening_plan
ON contents(project_id)
WHERE content_type = 'opening_plan';
CREATE UNIQUE INDEX uq_contents_project_chapter_number
ON contents(project_id, chapter_number)
WHERE content_type = 'chapter';

-- content_versions 表索引
CREATE INDEX idx_content_versions_content_id ON content_versions(content_id);
ALTER TABLE content_versions
ADD CONSTRAINT uq_content_versions_version_number
UNIQUE (content_id, version_number);
CREATE UNIQUE INDEX uq_content_versions_current_true ON content_versions(content_id) WHERE is_current = TRUE;
CREATE UNIQUE INDEX uq_content_versions_best_true ON content_versions(content_id) WHERE is_best = TRUE;

-- analyses 表索引
CREATE INDEX idx_analyses_project_id ON analyses(project_id);
CREATE INDEX idx_analyses_content_id ON analyses(content_id);
CREATE INDEX idx_analyses_type ON analyses(analysis_type);

-- workflow_executions 表索引
CREATE INDEX idx_workflow_executions_project_id ON workflow_executions(project_id);
CREATE INDEX idx_workflow_executions_status ON workflow_executions(status);
CREATE UNIQUE INDEX uq_workflow_execution_active_project
ON workflow_executions(project_id)
WHERE status IN ('created', 'running', 'paused');

-- node_executions 表索引
CREATE INDEX idx_node_executions_workflow_id ON node_executions(workflow_execution_id);
CREATE INDEX idx_node_executions_status ON node_executions(status);
ALTER TABLE node_executions
ADD CONSTRAINT uq_node_execution_unique
UNIQUE (workflow_execution_id, node_id, sequence);

-- artifacts 表索引
CREATE INDEX idx_artifacts_node_execution_id ON artifacts(node_execution_id);

-- review_actions 表索引
CREATE INDEX idx_review_actions_node_execution_id ON review_actions(node_execution_id);

-- token_usages 表索引
CREATE INDEX idx_token_usages_project_usage_type_created_at
ON token_usages(project_id, usage_type, created_at);
CREATE INDEX idx_token_usages_node_execution_id ON token_usages(node_execution_id);

-- exports 表索引
CREATE INDEX idx_exports_project_id ON exports(project_id);

-- 时间范围查询索引
CREATE INDEX idx_contents_created_at ON contents(created_at);
CREATE INDEX idx_workflow_executions_started_at ON workflow_executions(started_at);
CREATE INDEX idx_analyses_created_at ON analyses(created_at);

-- chapter_tasks 唯一约束
ALTER TABLE chapter_tasks
ADD CONSTRAINT uq_chapter_task_plan
UNIQUE (workflow_execution_id, chapter_number);
```

> PostgreSQL 16.x 生产环境应按以上 SQL 落成硬约束；SQLite 开发环境需要保持等价唯一性约束，禁止在实现层只靠业务代码“约定保证”。

---

## 4. 数据库选型

| 阶段 | 数据库 | 说明 |
|------|--------|----- |
| 开发 / 本地演示 | SQLite 3.x | 零配置，快速启动 |
| 正式部署 | PostgreSQL 16.x | 稳定可靠，JSONB 支持好 |

ORM 使用 SQLAlchemy 2.0，支持平滑切换，无需改业务代码。

---

## 5. 设计说明

**配置数据与业务数据分离**：Skills/Agents/Hooks/Workflows 的主数据来源是 YAML 文件，数据库只做缓存索引，避免双写冲突。模型凭证（API Key）在 `model_credentials` 表中加密存储，通过 Web UI 管理，不走 YAML。

**review_type 为自由字符串**：`ReviewAction.review_type` 不使用枚举，保持与用户自定义 Agent 配置的一致性。

**内容正文与元信息分离**：`Content` 表只记录元信息（类型、标题、章节号、状态等），正文内容全部存储在 `content_versions` 表中。查询当前正文时通过 `content_versions.is_current=true` 获取；并通过部分唯一索引确保同一 `Content` 只有一个 current 版本、最多一个 best 版本。这保证了版本管理的单一职责，避免了 Content 和 ContentVersion 正文不一致的风险。

**全量版本快照**：v0.1 `content_versions` 表存全量内容，实现简单，后续视存储压力决定是否迁移为增量差异。

**内容层级关系**：`Content.parent_id` 支持内容的层级关系，例如章节可以属于某个卷或部分。

**工作流可视化**：`TemplateNode` 表的 `position_x`、`position_y`、`ui_config` 字段支持工作流可视化功能。

**节点执行监控**：`NodeExecution` 表的 `retry_count`、`error_message`、`execution_time_ms` 字段支持节点执行的监控和调试。

**文件系统存储**：导出文件存储在文件系统而非数据库 BLOB，提高性能和可维护性。

---

## 6. 未来扩展预留

以下功能在 v0.2 或更高版本中考虑添加：

- **协作功能**：支持多人实时协同编辑
- **增量版本存储**：content_versions 表迁移为增量差异存储

---

## 7. 补充设计新增表

> 以下表来自设计审查补充文档，详见 [design/](../design/) 各模块设计。

### users（用户）

> 详见 [10-user-and-credentials](../design/10-user-and-credentials.md)

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| username | VARCHAR(100) | 用户名（唯一） |
| email | VARCHAR(200) | 邮箱（可选） |
| hashed_password | VARCHAR(200) | bcrypt 哈希密码 |
| is_active | BOOLEAN | 是否激活，默认 true |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### model_credentials（模型供应商凭证）

> 详见 [10-user-and-credentials](../design/10-user-and-credentials.md)

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| owner_type | VARCHAR(20) | 归属类型：system/user/project |
| owner_id | UUID | 归属 ID（system 级时可为 NULL） |
| provider | VARCHAR(50) | 渠道键 / Provider Key，用于按作用域解析凭证 |
| api_dialect | VARCHAR(50) | 接口类型：`openai_chat_completions / openai_responses / anthropic_messages / gemini_generate_content` |
| display_name | VARCHAR(100) | 显示名称 |
| encrypted_key | TEXT | AES-256-GCM 加密后的 API Key |
| base_url | VARCHAR(500) | 自定义 endpoint（可选；默认只允许公网 `https`，本地/私网需显式允许） |
| default_model | VARCHAR(100) | 连接级默认模型名 |
| auth_strategy | VARCHAR(50) | 可选鉴权覆盖：`bearer / x_api_key / x_goog_api_key / custom_header`；未设置时跟随 `api_dialect` 默认值 |
| api_key_header_name | VARCHAR(100) | 可选；仅在 `custom_header` 模式下指定 API Key Header 名称 |
| extra_headers | JSONB | 可选；附加请求头对象，不允许覆盖运行时保留头 |
| is_active | BOOLEAN | 是否启用，默认 true |
| last_verified_at | TIMESTAMP | 最后连通性测试通过时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### token_usages（Token 使用记录）

> 详见 [08-cost-and-safety](../design/08-cost-and-safety.md)

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID（FK → projects.id） |
| node_execution_id | UUID | 节点执行 ID（可选，FK → node_executions.id） |
| credential_id | UUID | 凭证 ID（FK → model_credentials.id） |
| usage_type | VARCHAR(20) | 用途类型：generate/review/fix/analysis/dry_run |
| model_name | VARCHAR(100) | 模型名称 |
| input_tokens | INTEGER | 输入 token 数 |
| output_tokens | INTEGER | 输出 token 数 |
| estimated_cost | NUMERIC(12, 6) | 估算费用（美元，精确数值） |
| created_at | TIMESTAMP | 创建时间 |

> `usage_type` 是统计与预算分析的强制分组维度，不能仅依赖 `node_execution_id` 或 `node_type` 反推；例如 `dry_run` 场景天然没有 `node_execution_id`。

### execution_logs（工作流执行日志）

> 详见 [18-data-backup](../design/18-data-backup.md)

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| workflow_execution_id | UUID | 工作流执行 ID |
| node_execution_id | UUID | 节点执行 ID（可选） |
| level | VARCHAR(20) | 日志级别：INFO/WARNING/ERROR |
| message | TEXT | 日志消息 |
| details | JSONB | 扩展详情（错误堆栈等） |
| created_at | TIMESTAMP | 创建时间 |

### audit_logs（安全审计日志）

> 详见 [10-user-and-credentials](../design/10-user-and-credentials.md) 与 [18-data-backup](../design/18-data-backup.md)

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| actor_user_id | UUID | 操作用户 ID（可选，system 事件时可为 NULL） |
| event_type | VARCHAR(50) | 事件类型：credential_create / credential_update / credential_delete / credential_verify / credential_enable / credential_disable / project_delete / project_restore |
| entity_type | VARCHAR(50) | 实体类型：model_credential / project |
| entity_id | UUID | 实体 ID |
| details | JSONB | 扩展详情（provider、owner_type、验证结果等） |
| created_at | TIMESTAMP | 创建时间 |

### prompt_replays（Prompt/响应回放）

> 详见 [18-data-backup](../design/18-data-backup.md)

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| node_execution_id | UUID | 节点执行 ID |
| replay_type | VARCHAR(20) | 类型：generate/review/fix |
| model_name | VARCHAR(100) | 模型名称 |
| prompt_text | TEXT | 完整 Prompt |
| response_text | TEXT | 完整响应 |
| input_tokens | INTEGER | 输入 token 数 |
| output_tokens | INTEGER | 输出 token 数 |
| created_at | TIMESTAMP | 创建时间 |

### chapter_tasks（章节任务列表）

> 详见 [04-chapter-generation](../design/04-chapter-generation.md)

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID（FK → projects.id） |
| workflow_execution_id | UUID | 工作流执行 ID（FK → workflow_executions.id） |
| chapter_number | INTEGER | 章节号 |
| title | VARCHAR(255) | 章节标题 |
| brief | TEXT | 章节摘要/任务描述 |
| key_characters | JSONB | 关键角色列表（JSON 数组，`string[]`） |
| key_events | JSONB | 关键事件列表（JSON 数组，`string[]`） |
| status | VARCHAR(50) | 状态：pending/generating/interrupted/completed/failed/skipped/stale |
| content_id | UUID | 关联生成的内容 ID（可选，FK → content.id） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

> 硬约束：`UNIQUE (workflow_execution_id, chapter_number)`。`interrupted` 为非终态，表示用户在生成过程中主动停止，等待后续恢复或改写决策；`stale` 表示上游设定或前置资产已变化，当前章节计划已过期，必须重新执行 `chapter_split` 后才能继续使用。

### story_facts（Story Bible 事实库）

> 详见 [02-context-injection](../design/02-context-injection.md)

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID（FK → projects.id） |
| chapter_number | INTEGER | 来源章节号 |
| source_content_version_id | UUID | 绑定到具体内容版本 |
| fact_type | VARCHAR(50) | 类型：character_state/location/timeline/setting_change/foreshadowing/relationship |
| subject | VARCHAR(255) | 主题（如人物名、地点名） |
| content | TEXT | 事实内容 |
| is_active | BOOLEAN | 是否有效，默认 true |
| conflict_status | VARCHAR(20) | 冲突状态：none/potential/confirmed |
| conflict_with_fact_id | UUID | 冲突指向的事实 ID（可选，自关联） |
| superseded_by | UUID | 被哪条新事实替代（可选） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

> 新事实写入前需和当前 active facts 做冲突检查。`potential` 表示检测到疑似矛盾但暂未确认，`confirmed` 表示已确认冲突，默认不自动注入到上下文中。
>
> 当前上下文注入只读取 `is_active=true`、`superseded_by is null` 且 `conflict_status != 'confirmed'` 的事实。

### 其他补充表（简要说明）

| 表名 | 用途 | 详见 |
|------|------|------|
| `writing_preferences` | 用户写作偏好 | [13-ai-preference-learning](../design/13-ai-preference-learning.md) |
| `edit_patterns` | 编辑模式记录 | [13-ai-preference-learning](../design/13-ai-preference-learning.md) |
| `foreshadowings` | 伏笔追踪 | [14-foreshadowing-tracking](../design/14-foreshadowing-tracking.md) |
| `foreshadowing_events` | 伏笔发展事件 | [14-foreshadowing-tracking](../design/14-foreshadowing-tracking.md) |
| `mcp_server_configs` | MCP Server 配置（第二阶段） | [16-mcp-architecture](../design/16-mcp-architecture.md) |

### 修改表

| 表 | 变更 |
|----|------|
| `projects` | 新增 `owner_id` (FK → users)、`deleted_at`、`allow_system_credential_pool` |

---

*最后更新: 2026-03-19*
