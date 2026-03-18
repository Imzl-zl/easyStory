# 10 - 用户认证与凭证管理

| 字段 | 内容 |
|---|---|
| 文档类型 | 设计规格 |
| 所属领域 | 用户模型、认证方案、凭证管理 |
| 优先级 | MVP 必须 |
| 来源 | design-review-supplement §4, §18 |

---

## 1. 概述

原设计完全没有用户概念。即使 MVP 只支持单用户，也应该预留用户模型，否则后期加用户系统需要大量改造。同时，系统需要管理多个模型供应商的 API Key，必须定义凭证的存储、加密、作用域和连通性测试机制。

本文档涵盖：
1. **MVP 用户模型** - 最简用户表，预留扩展性
2. **认证方案** - JWT 认证
3. **模型供应商凭证管理** - API Key 的存储、加密、优先级和测试

---

## 2. MVP 用户模型

### 2.1 User 模型

User 表包含基本字段：username（唯一）、email（可选）、hashed_password（bcrypt）、is_active。

> → 数据模型详见 [数据库设计](../specs/database-design.md) § users

### 2.2 Project 增加 owner 关联

Project 新增 `owner_id`（FK → users.id），与 User 为多对一关系。

> → 数据模型详见 [数据库设计](../specs/database-design.md) § projects

### 2.3 设计要点

- 用户与项目为一对多关系，通过 `owner_id` 关联
- 项目查询自动过滤 `owner_id`，实现基础数据隔离
- 后期加团队、角色、权限只需扩展，不需要改造核心表结构

---

## 3. 认证方案

### 3.1 技术选型

- 使用 JWT token 认证（FastAPI + python-jose）
- MVP 只需要注册 / 登录 / 登出三个端点

### 3.2 API 认证流程

```
注册: POST /api/auth/register
  -> 创建用户, 返回 JWT

登录: POST /api/auth/login
  -> 校验密码, 返回 JWT

业务请求: GET /api/projects
  -> Header: Authorization: Bearer <token>
  -> 中间件解析 token, 注入 current_user
  -> 查询自动过滤 owner_id = current_user.id
```

### 3.3 实现要点

- 所有业务 API 加 `current_user` 依赖注入
- 密码使用 bcrypt 哈希存储，明文不落库
- JWT 设置合理过期时间（建议 24 小时）

---

## 4. 模型供应商凭证管理

### 4.1 ModelCredential 存储模型

凭证表记录 API Key 的加密存储，支持三级作用域（system/user/project）、供应商标识、自定义 endpoint 和连通性验证时间。

> → 数据模型详见 [数据库设计](../specs/database-design.md) § model_credentials

### 4.2 字段说明

| 字段 | 说明 |
|------|------|
| `owner_type` | 凭证归属类型：system（系统级）/ user（用户级）/ project（项目级） |
| `owner_id` | 归属 ID，system 级时可为 None |
| `provider` | 模型供应商标识 |
| `encrypted_key` | AES-256-GCM 加密后的 API Key，明文永不落盘 |
| `base_url` | 可选，用于自定义 API endpoint（如代理、私有部署） |
| `last_verified_at` | 最后一次连通性测试通过时间 |

---

## 5. 凭证作用域与优先级

### 5.1 优先级链

```
项目级凭证 > 用户级凭证 > 系统级凭证（平台提供的公共 Key）
```

### 5.2 适用场景

| 作用域 | 场景 | 费用归属 |
|--------|------|---------|
| 项目级 | 工作室在"项目设置"配置项目专用 Key | 归项目 |
| 用户级 | 个人用户在"账户设置"配置自己的 API Key | 归用户 |
| 系统级 | 平台运营提供的公共 Key，作为兜底 | 按量计费归平台 |

### 5.3 解析逻辑

请求模型调用时，按优先级链查找第一个可用（`is_active = true`）的凭证。如果项目级有该 provider 的凭证则使用项目级，否则回退到用户级，再回退到系统级。

---

## 6. 安全要求

### 6.1 加密与存储

```yaml
credential_security:
  encryption: "AES-256-GCM"
  key_derivation: "PBKDF2"          # 从环境变量中的 master key 派生
  storage: "database"                # 加密后存库，明文永不落盘
  api_response: "masked"             # API 返回时掩码: "sk-...xxxx"
  audit_log: true                    # 凭证的增删改查都记审计日志
```

### 6.2 安全原则

- **存储**: API Key 使用 AES-256-GCM 加密后存入数据库，master key 从环境变量获取
- **传输**: API 返回凭证信息时，Key 始终掩码显示（如 `sk-...xxxx`）
- **审计**: 凭证的创建、修改、删除、使用均记录审计日志
- **派生**: 加密密钥通过 PBKDF2 从 master key 派生，非直接使用

---

## 7. 连通性测试

### 7.1 测试流程

```
用户添加/修改 API Key 后:
  |
  v
系统发送一个最小请求（如 "Hi", max_tokens=1）
  |
  v
验证结果:
  [OK] 连通正常 -> 记录 last_verified_at
  [ERR] 认证失败 -> 提示 "API Key 无效"
  [ERR] 网络超时 -> 提示 "无法连接到 {provider}"
  [ERR] 额度不足 -> 提示 "该 Key 余额不足"
```

### 7.2 设计要点

- 测试请求使用最小参数（`max_tokens=1`），避免产生实际费用
- 测试结果记录到 `last_verified_at`，用户可在 UI 查看凭证状态
- 支持手动重新测试（"重新验证"按钮）
- 凭证长时间未验证时，UI 可提示用户重新验证

### 7.3 费用归属

通过 `TokenUsage.credential_id` 关联到 `ModelCredential`，再通过 `owner_type / owner_id` 追溯费用归属方，实现项目级和用户级的费用分账。
