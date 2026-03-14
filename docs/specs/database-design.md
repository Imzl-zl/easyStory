# easyStory 数据库设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术设计 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-14 |
| 更新时间 | 2026-03-14 |
| 关联文档 | [系统架构设计](./architecture.md)、[API 设计](./api-design.md) |

---

## 1. 实体关系

```
Project (项目)
  ├── 1:N → Content (内容)
  │         └── 1:N → Version (版本)
  ├── 1:N → Analysis (分析结果)
  ├── 1:N → WorkflowRun (工作流执行)
  │         └── 1:N → NodeRun (节点执行)
  │                   ├── 1:N → Artifact (产物)
  │                   └── 1:N → ReviewAction (审核动作)
  ├── 1:N → Export (导出)
  └── N:1 → Template (模板)
            └── 1:N → TemplateNode (模板节点)

独立配置（不与项目直接关联）：
ModelProfile (模型档案)
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
| model_profile_id | UUID | 模型配置 ID |
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
| status | VARCHAR(50) | 状态：draft/approved/archived |
| metadata | JSONB | 元数据（标签、备注等） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| last_edited_at | TIMESTAMP | 最后编辑时间 |

**Version（版本快照）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| content_id | UUID | 内容 ID |
| version_number | INTEGER | 版本号（递增） |
| content | TEXT | 内容快照（全量存储） |
| change_summary | TEXT | 变更摘要 |
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

**WorkflowRun（工作流执行）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| project_id | UUID | 项目 ID |
| template_id | UUID | 模板 ID |
| status | VARCHAR(50) | 状态：pending/running/paused/completed/failed |
| current_node | INTEGER | 当前节点序号 |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |

**NodeRun（节点执行）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| workflow_run_id | UUID | 工作流执行 ID |
| node_order | INTEGER | 节点顺序 |
| node_type | VARCHAR(50) | 类型：generate/review/export |
| status | VARCHAR(50) | 状态：pending/running/reviewing/fixing/completed/failed |
| input | JSONB | 输入数据 |
| output | JSONB | 输出数据 |
| retry_count | INTEGER | 重试次数（默认 0） |
| error_message | TEXT | 错误信息 |
| execution_time_ms | INTEGER | 执行时间（毫秒） |
| started_at | TIMESTAMP | 开始时间 |
| completed_at | TIMESTAMP | 完成时间 |

**Artifact（产物）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| node_run_id | UUID | 节点执行 ID |
| artifact_type | VARCHAR(50) | 类型：outline/chapter/character 等 |
| content | TEXT | 内容 |
| word_count | INTEGER | 字数 |
| created_at | TIMESTAMP | 创建时间 |

**ReviewAction（审核动作）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| node_run_id | UUID | 节点执行 ID |
| agent_id | VARCHAR(100) | Agent ID（来自配置，非数据库外键） |
| review_type | VARCHAR(100) | 审核类型（自由字符串，与 Agent 定义一致） |
| result | VARCHAR(50) | 结果：passed/failed |
| issues | JSONB | 问题列表 |
| created_at | TIMESTAMP | 创建时间 |

---

### 配置缓存表

> 配置的主数据来源是 YAML 文件（文件系统），以下表用于索引和快速查询，启动时从文件同步。

**ModelProfile（模型档案）**

| 字段 | 类型 | 说明 |
|-----|------|----- |
| id | UUID | 主键 |
| name | VARCHAR(255) | 档案名称 |
| provider | VARCHAR(50) | 提供商：openai/anthropic/google/custom |
| model_name | VARCHAR(100) | 模型名称 |
| api_key | VARCHAR(255) | API Key（加密存储） |
| base_url | VARCHAR(255) | 自定义 API 地址 |
| config | JSONB | 其他参数（temperature、max_tokens 等） |
| is_default | BOOLEAN | 是否默认档案 |

> ModelProfile 不来自 YAML，通过 Web UI 管理（涉及敏感的 API Key）。

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

-- Version 表索引
CREATE INDEX idx_version_content_id ON Version(content_id);
CREATE INDEX idx_version_content_version ON Version(content_id, version_number);

-- Analysis 表索引
CREATE INDEX idx_analysis_project_id ON Analysis(project_id);
CREATE INDEX idx_analysis_content_id ON Analysis(content_id);
CREATE INDEX idx_analysis_type ON Analysis(analysis_type);

-- WorkflowRun 表索引
CREATE INDEX idx_workflow_run_project_id ON WorkflowRun(project_id);
CREATE INDEX idx_workflow_run_status ON WorkflowRun(status);

-- NodeRun 表索引
CREATE INDEX idx_node_run_workflow_id ON NodeRun(workflow_run_id);
CREATE INDEX idx_node_run_status ON NodeRun(status);

-- Artifact 表索引
CREATE INDEX idx_artifact_node_run_id ON Artifact(node_run_id);

-- ReviewAction 表索引
CREATE INDEX idx_review_action_node_run_id ON ReviewAction(node_run_id);

-- Export 表索引
CREATE INDEX idx_export_project_id ON Export(project_id);

-- 时间范围查询索引
CREATE INDEX idx_content_created_at ON Content(created_at);
CREATE INDEX idx_workflow_run_started_at ON WorkflowRun(started_at);
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

**配置数据与业务数据分离**：Skills/Agents/Hooks 的主数据来源是 YAML 文件，数据库只做缓存索引，避免双写冲突。ModelProfile 因涉及 API Key 加密，通过 Web UI 管理，不走 YAML。

**review_type 为自由字符串**：`ReviewAction.review_type` 不使用枚举，保持与用户自定义 Agent 配置的一致性。

**全量版本快照**：v0.1 `Version` 表存全量内容，实现简单，后续视存储压力决定是否迁移为增量差异。

**内容层级关系**：`Content.parent_id` 支持内容的层级关系，例如章节可以属于某个卷或部分。

**工作流可视化**：`TemplateNode` 表的 `position_x`、`position_y`、`ui_config` 字段支持工作流可视化功能。

**节点执行监控**：`NodeRun` 表的 `retry_count`、`error_message`、`execution_time_ms` 字段支持节点执行的监控和调试。

**文件系统存储**：导出文件存储在文件系统而非数据库 BLOB，提高性能和可维护性。

---

## 6. 未来扩展预留

以下功能在 v0.2 或更高版本中考虑添加：

- **用户系统**：User 表，支持多用户和权限管理
- **审计日志**：AuditLog 表，记录用户操作历史
- **协作功能**：支持多人实时协同编辑
- **增量版本存储**：Version 表迁移为增量差异存储

---

*最后更新: 2026-03-14*
