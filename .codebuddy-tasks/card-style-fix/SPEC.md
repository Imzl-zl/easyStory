# Card Style Fix — 系统性修复不可见卡片边框

## 目标
将所有页面中使用不可见边框 (`border-line-soft bg-muted`, `border-line-glass`, `panel-muted` 无可见边框) 的卡片，统一替换为可见边框样式。

## 替换规则

### 1. 内联卡片 → 使用 AppCard / InfoPanel / MetricCard
- `rounded-2xl border border-line-soft bg-muted` → `InfoPanel` (有标题/描述) 或 `AppCard variant="muted"` (纯容器)
- `rounded-2xl border border-line-soft bg-glass` → `AppCard variant="glass"`
- `rounded-2xl border border-line-glass bg-glass` → `AppCard variant="glass"`
- 本地 `MetricCard` / `ReviewMetricCard` / `BillingMetricCard` / `LogsMetricCard` / `UsageMetric` / `ExecutionMetric` → 统一 `MetricCard`

### 2. CSS 类替换
- `panel-muted` (已修复边框为 `--line-strong`) — 保留，无需改
- `border-line-glass` → `border-line-strong`
- `hero-card` 中的 `border-line-glass` → `border-line-strong`

### 3. 共享 UI 组件
- `status-badge.tsx`: `border-line-glass` → `border-line-strong`
- `dialog-shell.tsx`: `border-line-glass` → `border-line-strong`

## 文件范围
约 50+ 文件，按模块分组执行：
1. 共享 UI (2 files)
2. Engine 面板 (11 files)
3. Studio 组件 (7 files)
4. Settings 组件 (17+ files)
5. Lobby 组件 (11+ files)
6. Lab 组件 (3 files)
7. Project Settings 组件 (3 files)
8. Config Registry 组件 (6 files)
9. globals.css (hero-card)

## 验证
- `pnpm --dir apps/web build` 无错误
- 视觉上所有卡片边框可见
