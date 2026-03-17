# easyStory 数据库设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术设计 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-14 |
| 更新时间 | 2026-03-14 |
| 关联文档 | [系统架构设计](./architecture.md) |

---

## 1. 实体关系

```
Project (项目)
  ├── 1:N → Content (内容)
  │         └── 1:N → content_versions (版本)
  ├── 1:N → Analysis (分析结果)
  ├── 1:N → WorkflowExecution (工作流执行)
  │         └── 1:N → NodeExecution (节点执行)
  │                   ├── 1:N → Artifact (产物)
  │                   └── 1:N → ReviewAction (审核动作)
  ├── 1:N → Export (导出)
  └── N:1 → Template (模板)
            └── 1:N → TemplateNode (模板节点)

独立配置（不与项目直接关联）：
Skill (技能)
Hook (钩子)
Agent (智能体)
```

---

## 2. 数据表设计

### 核心业务表

**Project（项目）**

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
| config | JSONB | 项目级配置 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**Content（内容）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| parent_id | UUID | 父内容 ID（支持内容层级关系，可为 NULL） |
| content_type | VARCHAR(50) | 类型：outline/chapter/character/world_setting |
| title | VARCHAR(255) | 标题 |
| chapter_number | INTEGER | 章节号（章节类型时有效） |
| order_index | INTEGER | 排序索引（用于章节顺序） |
| content | TEXT | 内容正文 |
| word_count | INTEGER | 字数 |
| status | VARCHAR(50) | 状态：draft/approved/stale/archived |
| metadata | JSONB | 元数据（标签、备注等） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| last_edited_at | TIMESTAMP | 最后编辑时间 |

**content_versions（版本快照）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| content_id | UUID | 内容 ID |
| version_number | INTEGER | 版本号（递增） |
| content | TEXT | 内容快照（全量存储） |
| change_summary | TEXT | 变更摘要 |
| change_source | VARCHAR(50) | 变更来源：user_edit/ai_generate/ai_fix/import |
| word_count | INTEGER | 该版本字数 |
| context_snapshot_hash | VARCHAR(64) | 生成时上下文快照的 SHA-256（用于溯源） |
| ai_conversation_id | UUID | AI 生成/精修时的会话 ID（可选） |
| created_at | TIMESTAMP | 创建时间 |

> v0.1 采用全量快照，v0.2 可按需迁移为增量差异存储。

**Analysis（分析结果）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| content_id | UUID | 内容 ID（可选，分析特定内容时使用） |
| analysis_type | VARCHAR(50) | 分析类型：plot/character/style/pacing/structure |
| result | JSONB | 分析结果（结构化数据） |
| suggestions | JSONB | 改进建议 |
| generated_skill_id | UUID | 自动生成的 Skill ID（可选） |
| created_at | TIMESTAMP | 创建时间 |

> 支持"小说分析功能"和"分析自动生成 Skill"核心需求。

**Template（模板）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| name | VARCHAR(255) | 模板名称 |
| description | TEXT | 描述 |
| genre | VARCHAR(100) | 适用题材 |
| config | JSONB | 模板配置 |
| is_builtin | BOOLEAN | 是否内置模板 |
| created_at | TIMESTAMP | 创建时间 |

**TemplateNode（模板节点）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| template_id | UUID | 模板 ID |
| node_order | INTEGER | 节点顺序 |
| node_type | VARCHAR(50) | 类型：generate/review/export |
| skill_id | VARCHAR(100) | 技能 ID |
| config | JSONB | 节点配置 |
| position_x | INTEGER | 节点 X 坐标（工作流可视化用） |
| position_y | INTEGER | 节点 Y 坐标（工作流可视化用） |
| ui_config | JSONB | UI 配置（颜色、图标等） |

---

### 工作流表

**WorkflowExecution（工作流执行）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| template_id | UUID | 模板 ID |
| status | VARCHAR(50) | 状态：created/running/paused/completed/failed/cancelled |
| current_node | INTEGER | 当前节点序号 |
| pause_reason | VARCHAR(50) | 暂停原因：user_request/budget_exceeded/review_failed/error |
| resume_from_node | VARCHAR(200) | 恢复时从哪个节点继续 |
| snapshot | JSONB | 暂停时的状态快照 |
| workflow_snapshot | JSONB | 启动时工作流配置快照（不可变） |
| skills_snapshot | JSONB | 启动时 Skills 配置快照（不可变） |
| agents_snapshot | JSONB | 启动时 Agents 配置快照（不可变） |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |

**NodeExecution（节点执行）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| workflow_execution_id | UUID | 工作流执行 ID |
| node_id | VARCHAR(200) | 节点 ID（来自 workflow 配置） |
| sequence | INTEGER | 迭代序号（循环节点）/0（非循环） |
| node_order | INTEGER | 节点顺序（用于 UI 列表排序，可冗余） |
| node_type | VARCHAR(50) | 类型：generate/review/export |
| status | VARCHAR(50) | 状态：pending/running/reviewing/fixing/completed/failed/skipped |
| input | JSONB | 输入数据 |
| output | JSONB | 输出数据 |
| retry_count | INTEGER | 重试次数（默认 0） |
| error_message | TEXT | 错误信息 |
| execution_time_ms | INTEGER | 执行时间（毫秒） |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |

> 约束：同一 `workflow_execution_id` 下，`(node_id, sequence)` 必须唯一，用于防重复生成与 `resume_workflow` 幂等（详见 `docs/design/17-cross-module-contracts.md`）。

**Artifact（产物）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| node_execution_id | UUID | 节点执行 ID |
| artifact_type | VARCHAR(50) | 类型：outline/chapter/character 等 |
| content | TEXT | 内容 |
| word_count | INTEGER | 字数 |
| created_at | TIMESTAMP | 创建时间 |

**ReviewAction（审核动作）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| node_execution_id | UUID | 节点执行 ID |
| agent_id | VARCHAR(100) | Agent ID（来自配置，非数据库外键） |
| review_type | VARCHAR(100) | 审核类型（自由字符串，与 Agent 定义一致） |
| result | VARCHAR(50) | 结果：passed/failed |
| issues | JSONB | 问题列表 |
| created_at | TIMESTAMP | 创建时间 |

---

### 配置缓存表

> 配置的主数据来源是 YAML 文件（文件系统），以下表用于索引和快速查询，启动时从文件同步。
>
> 模型相关说明：
> - 模型选择与参数在 Skill/Workflow/Node 配置中声明
> - 模型凭证在业务表 `model_credentials` 中加密存储（不走 YAML，不属于配置缓存表）

**Skill（技能）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| skill_id | VARCHAR(100) | 技能唯一标识（来自 YAML） |
| name | VARCHAR(255) | 名称 |
| category | VARCHAR(50) | 分类 |
| config | JSONB | 完整配置快照 |
| file_path | VARCHAR(255) | 对应 YAML 文件路径 |

**Hook（钩子）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| hook_id | VARCHAR(100) | 钩子唯一标识（来自 YAML） |
| trigger | VARCHAR(50) | 触发时机 |
| action_type | VARCHAR(50) | 动作类型：script/webhook/agent |
| action_config | JSONB | 动作配置 |
| file_path | VARCHAR(255) | 对应 YAML 文件路径 |

**Agent（智能体）**

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

**Export（导出记录）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| format | VARCHAR(20) | 格式：markdown/docx/pdf |
| filename | VARCHAR(255) | 文件名 |
| file_path | VARCHAR(500) | 文件路径（相对于导出目录） |
| file_size | INTEGER | 文件大小（字节） |
| created_at | TIMESTAMP | 创建时间 |

> 导出文件存储在文件系统，数据库只存路径和元数据。

---

## 3. 索引设计

### 核心查询索引

```sql
-- Content 表索引
CREATE INDEX idx_content_project_id ON Content(project_id);
CREATE INDEX idx_content_type_status ON Content(content_type, status);
CREATE INDEX idx_content_parent_id ON Content(parent_id);
CREATE INDEX idx_content_order_index ON Content(order_index);

-- content_versions 表索引
CREATE INDEX idx_content_versions_content_id ON content_versions(content_id);
CREATE INDEX idx_content_versions_content_version ON content_versions(content_id, version_number);

-- Analysis 表索引
CREATE INDEX idx_analysis_project_id ON Analysis(project_id);
CREATE INDEX idx_analysis_content_id ON Analysis(content_id);
CREATE INDEX idx_analysis_type ON Analysis(analysis_type);

-- WorkflowExecution 表索引
CREATE INDEX idx_workflow_execution_project_id ON WorkflowExecution(project_id);
CREATE INDEX idx_workflow_execution_status ON WorkflowExecution(status);

-- NodeExecution 表索引
CREATE INDEX idx_node_execution_workflow_id ON NodeExecution(workflow_execution_id);
CREATE INDEX idx_node_execution_workflow_node ON NodeExecution(workflow_execution_id, node_id, sequence);
CREATE INDEX idx_node_execution_status ON NodeExecution(status);

-- Artifact 表索引
CREATE INDEX idx_artifact_node_execution_id ON Artifact(node_execution_id);

-- ReviewAction 表索引
CREATE INDEX idx_review_action_node_execution_id ON ReviewAction(node_execution_id);

-- Export 表索引
CREATE INDEX idx_export_project_id ON Export(project_id);

-- 时间范围查询索引
CREATE INDEX idx_content_created_at ON Content(created_at);
CREATE INDEX idx_workflow_execution_started_at ON WorkflowExecution(started_at);
CREATE INDEX idx_analysis_created_at ON Analysis(created_at);
```

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

**全量版本快照**：v0.1 `content_versions` 表存全量内容，实现简单，后续视存储压力决定是否迁移为增量差异。

**内容层级关系**：`Content.parent_id` 支持内容的层级关系，例如章节可以属于某个卷或部分。

**工作流可视化**：`TemplateNode` 表的 `position_x`、`position_y`、`ui_config` 字段支持工作流可视化功能。

**节点执行监控**：`NodeExecution` 表的 `retry_count`、`error_message`、`execution_time_ms` 字段支持节点执行的监控和调试。

**文件系统存储**：导出文件存储在文件系统而非数据库 BLOB，提高性能和可维护性。

---

## 6. 未来扩展预留

以下功能在 v0.2 或更高版本中考虑添加：

- **用户系统**：User 表，支持多用户和权限管理
- **审计日志**：AuditLog 表，记录用户操作历史
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
| provider | VARCHAR(50) | 模型供应商：anthropic/openai/deepseek 等 |
| display_name | VARCHAR(100) | 显示名称 |
| encrypted_key | TEXT | AES-256-GCM 加密后的 API Key |
| base_url | VARCHAR(500) | 自定义 endpoint（可选） |
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
| model_name | VARCHAR(100) | 模型名称 |
| input_tokens | INTEGER | 输入 token 数 |
| output_tokens | INTEGER | 输出 token 数 |
| estimated_cost | FLOAT | 估算费用（美元） |
| created_at | TIMESTAMP | 创建时间 |

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
| key_characters | JSONB | 关键角色列表 |
| key_events | JSONB | 关键事件列表 |
| status | VARCHAR(50) | 状态：pending/generating/completed/failed/skipped |
| content_id | UUID | 关联生成的内容 ID（可选，FK → content.id） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

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
| superseded_by | UUID | 被哪条新事实替代（可选） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

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
| `projects` | 新增 `owner_id` (FK → users)、`deleted_at` |

---

*最后更新: 2026-03-17*
