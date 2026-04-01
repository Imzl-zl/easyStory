# easyStory 项目文档

本目录包含 easyStory AI 小说创作平台的所有设计和技术文档。

---

## 文档导航

### 技术规范（specs/）

| 文档 | 状态 | 说明 |
|------|------|------|
| [技术栈确定](./specs/tech-stack.md) | 生效 | 最终技术选型决策 |
| [系统架构设计](./specs/architecture.md) | 生效 | 分层架构 + MCP 预留 |
| [数据库设计](./specs/database-design.md) | 生效 | 数据模型和表结构 |
| [配置格式规范](./specs/config-format.md) | 生效 | Skills/Agents/Hooks/Workflows YAML 格式 |

### 功能设计（design/）

| 编号 | 文档 | 优先级 | 内容 |
|------|------|--------|------|
| 00 | [设计索引](./design/00-index.md) | - | 模块总览 + 验收标准 |
| 01 | [核心工作流](./design/01-core-workflow.md) | 🔴 | 节点系统 + 双模式 + 状态机 |
| 02 | [上下文注入](./design/02-context-injection.md) | 🔴 | 三层优先级 + Story Bible + 裁剪 |
| 03 | [审核精修](./design/03-review-and-fix.md) | 🔴 | ReviewResult Schema + 聚合 + 精修 |
| 04 | [章节生成](./design/04-chapter-generation.md) | 🔴 | 循环 + 拆分 + 动态终止 |
| 05 | [内容编辑](./design/05-content-editor.md) | 🔴 | 编辑器 + 版本 + 下游影响 |
| 06 | [创作设定](./design/06-creative-setup.md) | 🔴 | 对话设定 + 结构化输出 + 模板 |
| 07 | [小说分析](./design/07-novel-analysis.md) | 🟡 | 上传 + 分析 + Skill 生成 |
| 08 | [成本控制](./design/08-cost-and-safety.md) | 🔴 | 预算 + 安全阀 + Dry-run |
| 09 | [错误处理](./design/09-error-handling.md) | 🔴 | 分类 + 重试 + 模型降级 |
| 10 | [用户认证](./design/10-user-and-credentials.md) | 🔴 | User 模型 + 凭证管理 |
| 11 | [导出](./design/11-export.md) | 🔴/🟡 | 🔴 TXT/Markdown；🟡 DOCX/EPUB/高级排版 |
| 12 | [流式输出](./design/12-streaming-and-interrupt.md) | 🟡 | SSE + 中途打断 |
| 13 | [AI 偏好学习](./design/13-ai-preference-learning.md) | 🟡 | 记忆系统 + 编辑分析 |
| 14 | [伏笔追踪](./design/14-foreshadowing-tracking.md) | 🟡 | 生命周期 + 自动检测 |
| 15 | [写作面板](./design/15-writing-dashboard.md) | 🟡 | 指标 + 趋势 |
| 16 | [MCP 预留](./design/16-mcp-architecture.md) | 🔴 | 三方向 + 架构约束 |
| 17 | [跨模块契约](./design/17-cross-module-contracts.md) | 🔴 | 并发幂等 + 安全 + 级联 |
| 18 | [数据备份](./design/18-data-backup.md) | 🟡 | 软删除 + 回收站 + 日志 |
| 19 | [前置创作资产](./design/19-pre-writing-assets.md) | 🔴 | 设定/大纲/开篇/章节衔接链路 |

### UI 交互设计（ui/）

| 文档 | 说明 |
|------|------|
| [UI 设计规范](./ui/ui-design.md) | MVP 对齐后的工作台 IA 与视觉基线 |
| [UI 交互补充](./ui/ui-interaction-supplement.md) | MVP 对齐后的交互规则、状态映射与边界态 |

### 实施计划（plans/）

| 文档 | 说明 |
|------|------|
| [后端核心实施计划（V2）](./plans/2026-03-17-backend-core-v2.md) | 后端核心实现路线（以设计文档为准） |
| [前置创作资产实施计划](./plans/2026-03-19-pre-writing-assets.md) | 设定/大纲/开篇设计/章节衔接补充计划 |
| [前端 UI 重构计划](./plans/2026-03-31-web-ui-restructure-plan.md) | 主路径页面的 creator-first 重构顺序与参考锚点 |

> 当前计划覆盖后端核心、前置创作资产补充设计，以及前端 UI 重构路径。发生冲突时，以对应设计文档和当前代码真值为准。

---

## 文档阅读顺序

### 新成员入门

1. **核心工作流** → 理解核心功能和设计理念
2. **系统架构设计** → 了解技术架构
3. **技术栈确定** → 了解技术选型
4. **设计索引** → 了解全部模块和验收标准

### 开发人员

1. **设计索引** → 了解模块全貌和验收标准
2. **核心工作流** → 理解业务逻辑
3. **数据库设计** → 了解数据模型
4. **配置格式规范** → 了解配置系统
5. 按开发任务查阅对应的 design/ 文件

### 后端环境配置

- 后端运行时环境变量模板位于 `apps/api/.env.example`。
- 本地启动前先复制为 `apps/api/.env`，再填写必需项。
- 当前必需项：
  - `EASYSTORY_JWT_SECRET`
- 条件必需项：
  - `EASYSTORY_CREDENTIAL_MASTER_KEY`
    在使用 `Credential Center` 创建、加密或验证模型凭证前必须配置。
- 当前可选项：
  - `EASYSTORY_DATABASE_URL`
  - `EASYSTORY_JWT_EXPIRE_HOURS`
  - `EASYSTORY_CORS_ALLOWED_ORIGINS`
  - `EASYSTORY_CORS_ALLOWED_ORIGIN_REGEX`
  - `EASYSTORY_ALLOW_PRIVATE_MODEL_ENDPOINTS`
    默认只允许公网 `https` 模型 endpoint；只有确实需要访问本地 / 私网模型网关时才显式开启。
  - `EASYSTORY_ALLOW_INSECURE_PUBLIC_MODEL_ENDPOINTS`
    默认不允许公网 `http` 模型 endpoint；只有在受控代理或兼容测试环境下才显式开启。
  - `EASYSTORY_CONFIG_ADMIN_USERNAMES`
    逗号分隔的控制面管理员用户名白名单；只有命中的用户才能访问 `/api/v1/config/*` 和模板写接口，默认空列表表示全部拒绝控制面写权限。

### 后端本地启动

1. 进入后端目录并准备运行时配置：

   ```bash
   cd apps/api
   cp .env.example .env
   ```

2. 编辑 `apps/api/.env`，至少把 `EASYSTORY_JWT_SECRET` 改成真实随机字符串。
   `EASYSTORY_CREDENTIAL_MASTER_KEY` 只在使用 `Credential Center` 创建、加密或校验模型凭证时需要。

3. 安装依赖并启动开发服务：

   ```bash
   cd apps/api
   uv sync --extra dev
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. 启动后可访问：
   - API 文档：`http://127.0.0.1:8000/docs`
   - 健康检查：`http://127.0.0.1:8000/healthz`

5. 数据库默认行为：
   - 如果未设置 `EASYSTORY_DATABASE_URL`，后端默认使用 `apps/api/.runtime/easystory.db`
   - 应用启动时会自动执行数据库初始化和 Alembic upgrade，不需要先手动建库

6. 如需手动执行迁移，可在 `apps/api` 下运行：

   ```bash
   uv run alembic -c alembic.ini upgrade head
   ```

7. 如果后端日志长期停在 `Waiting for application startup.`，且本机访问
   `http://127.0.0.1:8000/healthz` 失败，通常说明本地 SQLite 开发库进入了
   “表已存在，但 Alembic revision 状态损坏”的异常状态。若这份本地库数据不重要，
   可先备份旧库，再让后端自动重建：

   ```bash
   cd apps/api
   mv .runtime/easystory.db .runtime/easystory.db.bak-$(date +%Y%m%d-%H%M%S)
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   - `mv` 是“备份并移走旧库”，不会直接删除。
   - 新库会在下一次启动时由 Alembic 自动重建。
   - 真正启动成功的标志是日志里出现 `Application startup complete.`，
     并且 `http://127.0.0.1:8000/healthz` 返回 `200`。

---

## 优先级说明

- 🔴 MVP 必须实现（后期改造成本高）
- 🟡 MVP 建议简化实现（提升可用性）
- 🟢 第二阶段扩展

---

## 文档目录结构

```
docs/
├── README.md                    # 本文件
├── specs/                       # 技术规范
│   ├── tech-stack.md
│   ├── architecture.md
│   ├── database-design.md
│   └── config-format.md
├── design/                      # 功能设计（18 个模块）
│   ├── 00-index.md             # 索引 + 验收标准
│   ├── 01-core-workflow.md     # ~ 18-data-backup.md
│   └── ...
├── ui/                          # UI 交互设计
│   ├── ui-design.md
│   └── ui-interaction-supplement.md
└── plans/                       # 实施计划
    └── 2026-03-17-backend-core-v2.md
```

---

*最后更新: 2026-03-28*
