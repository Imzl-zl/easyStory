# easyStory 后端 Async 迁移计划

## 1. 背景

当前 `apps/api` 的正式技术路线与实装已经出现分叉。

- `docs/plans/2026-03-17-backend-core-v2.md` 明确写的是 `SQLAlchemy 2.0 (async)`、`pytest-asyncio`、`httpx` 异步测试基线。
- 但当前仓库实际落地的大多数 API 路由、依赖注入、数据库 session 与测试夹具仍是同步实现。

这次暴露出来的 `register` / API 内嵌测试阻塞，不是单个接口问题，而是这条分叉被运行时环境放大后的系统性故障。

## 2. 根因

### 2.1 官方执行模型

- FastAPI 官方文档说明：普通 `def` 的 path operation function 与 dependency 不会直接在事件循环里执行，而会放到外部线程池。
- Starlette 官方文档进一步明确：同步 endpoint、同步 background task 等会通过 `anyio.to_thread.run_sync` 放到线程池里执行。
- Starlette `TestClient` 也建立在 AnyIO portal 之上，不能视为绕过这条路径的独立基线。

### 2.2 本地最小复现

当前仓库依赖栈下，最小复现已经确认：

- `asyncio.to_thread(lambda: "ok")` 正常返回。
- `anyio.to_thread.run_sync(lambda: "ok")` 挂死。
- 极简 FastAPI 应用里，`async def` 路由正常，`def` 路由挂死。

当前确认版本：

- Python `3.13.12`
- FastAPI `0.135.1`
- Starlette `0.52.1`
- HTTPX `0.28.1`
- AnyIO `4.12.1`
- SQLAlchemy `2.0.48`

### 2.3 项目级根因

因此，真正根因不是某个业务模块，而是：

1. 当前 easyStory 后端的大多数 HTTP 面仍依赖同步路由 + 同步依赖执行路径。
2. 这条路径在当前运行时栈里依赖的 AnyIO 线程池桥接不可靠。
3. 项目此前没有按正式计划完成 async-first 迁移，导致问题面不是局部而是全局。

## 3. 决策

本项目后续不采用以下方案作为长期解法：

- 不继续围绕 `TestClient`、临时 `client_helper` 做表面补丁。
- 不把大量同步 service 用 `asyncio.to_thread()` 包起来长期运行。
- 不保留“同步 Session + 异步路由”这种混合基线作为正式架构。

正式目标收敛为：

1. 应用生命周期统一改为 `lifespan`。
2. 数据库基线迁移到 `create_async_engine`、`async_sessionmaker`、`AsyncSession`。
3. API 路由与依赖注入迁移到 `async def`。
4. API 测试迁移到 `pytest-asyncio + httpx.AsyncClient + ASGITransport + 显式 lifespan 管理`。
5. 删除所有仅为维持同步 transport 而存在的临时测试辅助代码。

## 4. 迁移阶段

### 阶段 1: Lifecycle 收敛

- `create_app()` 改为 `FastAPI(lifespan=...)`
- 启动校验与 builtin template sync 收敛到 lifespan

### 阶段 2: Shared DB 基线迁移

- `shared/db` 切换到 async engine / sessionmaker
- 提供统一 `AsyncSession` 依赖
- 重新校验 SQLite 开发环境与 PostgreSQL 生产路径

### 阶段 3: 首批模块迁移

优先顺序：

1. `user/auth`
2. `template`
3. `project`
4. `content`
5. `workflow` 及相关 `billing/review/context/observability/export`

原则：

- 先迁依赖面最集中、联调价值最高的链路。
- 一个模块迁完后再迁下一个，避免半同步半异步长期共存。

### 阶段 4: 测试基座重建

- 删除同步 API 测试 transport 辅助
- 收敛为 async fixtures、async client、显式 lifespan
- 将当前“API 卡死”从偶发人工排查变成可回归验证的基线

## 5. 非目标

- 本计划不同时扩展新业务范围。
- 本计划不通过 mock success / silent fallback 掩盖真实阻塞。
- 本计划不为了兼容当前同步基线而新增长期双真值架构。
