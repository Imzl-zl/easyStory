# easyStory API 设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术设计 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-14 |
| 关联文档 | [系统架构设计](../架构/系统架构设计.md)、[数据库设计](./数据库设计.md) |

---

## 1. RESTful 规范

### URL 设计

- 使用名词复数：`/projects`、`/templates`
- 使用小写字母和连字符：`/model-profiles`
- 层级关系体现资源归属：`/projects/{id}/contents`

### HTTP 方法

| 方法 | 用途 | 示例 |
|-----|------|------|
| GET | 获取资源 | `GET /projects` |
| POST | 创建资源 | `POST /projects` |
| PUT | 全量更新 | `PUT /projects/{id}` |
| PATCH | 部分更新 | `PATCH /projects/{id}` |
| DELETE | 删除资源 | `DELETE /projects/{id}` |

### 状态码

| 状态码 | 含义 | 使用场景 |
|-------|------|----------|
| 200 | 成功 | GET、PUT、PATCH |
| 201 | 已创建 | POST |
| 204 | 无内容 | DELETE |
| 400 | 请求错误 | 参数校验失败 |
| 401 | 未认证 | 未登录 |
| 403 | 禁止访问 | 无权限 |
| 404 | 未找到 | 资源不存在 |
| 422 | 无法处理 | 业务逻辑错误 |

---

## 2. 统一响应格式

**成功响应**：
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

**错误响应**：
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数校验失败",
    "details": [...]
  }
}
```

**分页响应**：
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100
    }
  }
}
```

---

## 3. API 列表

所有接口统一前缀：`/api/v1`

### 项目管理

| 方法 | URL | 说明 |
|-----|-----|------|
| GET | `/projects` | 项目列表 |
| POST | `/projects` | 创建项目 |
| GET | `/projects/{id}` | 项目详情 |
| PUT | `/projects/{id}` | 更新项目 |
| DELETE | `/projects/{id}` | 删除项目 |
| POST | `/projects/{id}/start` | 启动工作流 |
| POST | `/projects/{id}/pause` | 暂停工作流 |

### 内容管理

| 方法 | URL | 说明 |
|-----|-----|------|
| GET | `/projects/{id}/contents` | 内容列表 |
| POST | `/projects/{id}/contents` | 创建内容 |
| GET | `/projects/{id}/contents/{cid}` | 内容详情 |
| PUT | `/projects/{id}/contents/{cid}` | 更新内容 |
| GET | `/projects/{id}/contents/{cid}/versions` | 版本历史 |

### 工作流管理

| 方法 | URL | 说明 |
|-----|-----|------|
| GET | `/projects/{id}/workflow-runs` | 工作流执行列表 |
| GET | `/workflow-runs/{id}` | 工作流执行详情 |
| POST | `/node-runs/{id}/approve` | 批准节点 |
| POST | `/node-runs/{id}/reject` | 拒绝节点 |
| POST | `/node-runs/{id}/retry` | 重试节点 |

### 配置管理

| 方法 | URL | 说明 |
|-----|-----|------|
| GET | `/model-profiles` | 模型档案列表 |
| POST | `/model-profiles` | 创建模型档案 |
| PUT | `/model-profiles/{id}` | 更新模型档案 |
| DELETE | `/model-profiles/{id}` | 删除模型档案 |
| GET | `/skills` | 技能列表 |
| POST | `/skills` | 创建技能 |
| GET | `/hooks` | 钩子列表 |
| POST | `/hooks` | 创建钩子 |
| GET | `/agents` | 智能体列表 |
| POST | `/agents` | 创建智能体 |

### 导出管理

| 方法 | URL | 说明 |
|-----|-----|------|
| POST | `/projects/{id}/exports` | 创建导出任务 |
| GET | `/projects/{id}/exports` | 导出列表 |
| GET | `/exports/{id}/download` | 下载文件 |

---

## 4. WebSocket 设计

**连接地址**：`ws://localhost:8000/api/v1/ws`

**消息类型**：

| 类型 | 说明 |
|-----|------|
| `workflow_started` | 工作流开始 |
| `node_started` | 节点开始执行 |
| `node_completed` | 节点执行完成 |
| `node_reviewing` | 节点等待审核 |
| `workflow_completed` | 工作流完成 |
| `workflow_failed` | 工作流失败 |

WebSocket 用于实时推送工作流执行状态，普通 CRUD 操作仍走 REST API。
