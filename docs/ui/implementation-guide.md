# easyStory UI 实施指南

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术实施规格 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-31 |
| 最后更新 | 2026-03-31 |
| 适用范围 | 前端开发团队 |

---

## 1. 文档角色

本文件只记录当前前端实现真值和可执行约束，不再承载探索性方案。

边界如下：

- 页面语义与布局原则：`docs/ui/ui-design.md`
- 探索草图与提案归档：`docs/ui/ui-design-v2.md`
- 运行时样式 token 真值：`apps/web/src/app/globals.css`
- Tailwind 工具映射：`apps/web/tailwind.config.ts`
- 类名合并工具：`apps/web/src/lib/utils/cn.ts`

---

## 2. 当前前端结构

### 2.1 路由与实现分层

```text
src/app/**                  路由入口与页面装配
src/features/**             页面级与业务级组件
src/components/ui/**        共享 UI 原件
src/lib/**                  API、store、hooks、utils
src/app/globals.css         运行时全局样式与 token 真值
```

### 2.2 当前真实主路径

```text
src/app/workspace/
├── lobby/page.tsx
├── lobby/new/page.tsx
├── lobby/settings/page.tsx
├── lobby/config-registry/page.tsx
├── lobby/recycle-bin/page.tsx
├── lobby/templates/page.tsx
└── project/[projectId]/
    ├── studio/page.tsx
    ├── engine/page.tsx
    ├── lab/page.tsx
    └── settings/page.tsx
```

### 2.3 当前共享 UI 原件

当前仓库已经存在一批共享 UI 原件，后续新增原件应优先复用或延续这套命名：

- `app-select`
- `code-block`
- `dialog-shell`
- `empty-state`
- `page-header-shell`
- `section-card`
- `status-badge`
- `unsaved-changes-dialog`

页面级复杂布局和强业务语义组件继续留在 `src/features/<domain>/components/`。

---

## 3. 样式系统真值

### 3.1 Tailwind 4 接入方式

当前项目采用 Tailwind CSS 4，`globals.css` 的接入方式是：

```css
@import "tailwindcss";
```

不使用旧的：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 3.2 运行时 token 命名

当前运行时 token 以 `globals.css` 为准，命名分组如下：

```css
:root {
  --bg-canvas: #f8f6f1;
  --bg-surface: #ffffff;
  --bg-muted: #f3f0e8;
  --bg-elevated: #ffffff;

  --line-soft: rgba(61, 61, 61, 0.09);
  --line-strong: rgba(61, 61, 61, 0.16);
  --line-focus: rgba(90, 122, 107, 0.4);

  --text-primary: #3d3d3d;
  --text-secondary: #6b6b6b;
  --text-tertiary: #9b9a97;
  --text-placeholder: #b4b4b4;

  --accent-primary: #5a7a6b;
  --accent-primary-hover: #4a6a5b;
  --accent-secondary: #8b7355;
  --accent-tertiary: #c4a77d;
  --accent-success: #5a8a6b;
  --accent-warning: #c4883d;
  --accent-danger: #c45a5a;
  --accent-ink: #5a9aaa;
}
```

文档和工具映射都必须跟这套命名对齐，不再使用 `--color-*` 作为当前真值。

### 3.3 Tailwind 映射原则

`tailwind.config.ts` 只做对运行时 token 的语义映射，不创造第二套设计 token。

推荐类名语义：

- 背景：`bg-canvas` `bg-surface` `bg-muted`
- 边线：`border-line-soft` `border-line-strong`
- 文字：`text-text-primary` `text-text-secondary`
- 强调色：`bg-accent-primary` `text-accent-primary`

### 3.4 全局样式职责

`globals.css` 当前除了 token，还承载这些运行时职责：

- 基础 reset
- `body` 与标题排版
- 输入框、按钮、卡片等基础 class
- Arco 主题色桥接

因此它不是纯 token 文件，调整时要按“运行时总入口”对待。

---

## 4. 何时使用什么

### 4.1 决策树

```
需要样式？
  ├─ 是全局语义 token？
  │   └─ 改 globals.css 中的 CSS Variables
  │
  ├─ 是页面布局、间距、对齐？
  │   └─ 优先用 Tailwind utilities
  │
  ├─ 是复杂局部视觉或交互动效？
  │   └─ 允许继续使用 feature 级 CSS Module
  │
  └─ 是多处复用的通用交互外壳？
      └─ 抽到 src/components/ui/**
```

### 4.2 具体规则

#### 规则 1：设计 token 只引用真实变量名

```tsx
<div
  style={{
    background: "var(--bg-surface)",
    color: "var(--text-primary)",
    borderRadius: "var(--radius-md)",
  }}
/>
```

不要在实现文档里再写一套 `--color-paper`、`--color-text-primary` 的平行真值。

#### 规则 2：布局优先用 Tailwind

```tsx
<section className="flex min-h-0 flex-col gap-4 p-6 lg:grid lg:grid-cols-[280px_minmax(0,1fr)]">
  ...
</section>
```

#### 规则 3：复杂局部样式允许继续使用 CSS Module

当前仓库已经大量使用 `*.module.css`，尤其在这些区域：

- `workspace-shell`
- `lobby-page`
- `incubator-page`
- `studio-page`
- `engine-page`

这些文件是现状的一部分，不需要为了“全 Tailwind”强行回退。

#### 规则 4：共享组件优先走真实 import 路径

`cn` 的当前真实路径是：

```tsx
import { cn } from "@/lib/utils/cn";
```

不要写成不存在的 `@/lib/utils` 聚合入口。

---

## 5. 组件组织规则

### 5.1 当前推荐分层

```text
src/components/ui/**                共享 UI 原件
src/features/<domain>/components/** 业务与页面组件
src/app/**                          路由页面和装配入口
```

### 5.2 抽组件标准

- 跨多个 feature 复用，才进入 `src/components/ui/**`
- 仍然强绑定某个页面语义，留在 `src/features/**`
- 不为了“看起来像组件库”提前抽空壳组件

### 5.3 示例

```tsx
import { cn } from "@/lib/utils/cn";

interface SurfaceCardProps {
  className?: string;
  children: React.ReactNode;
}

export function SurfaceCard({ className, children }: SurfaceCardProps) {
  return (
    <section
      className={cn(
        "rounded-lg border border-line-soft bg-surface shadow-sm",
        className,
      )}
    >
      {children}
    </section>
  );
}
```

---

## 6. 页面开发检查清单

### 6.1 开发前

- [ ] 先看 `docs/ui/ui-design.md`，确认页面语义
- [ ] 先看真实路由和现有 feature 目录，不凭空新增 `v2/demo` 结构
- [ ] 确认是否已有可复用 UI 原件
- [ ] 确认是否需要继续沿用现有 CSS Module

### 6.2 开发中

- [ ] 颜色、文字、边线、阴影都引用 `globals.css` 真值
- [ ] 布局优先使用 Tailwind utilities
- [ ] 局部复杂样式按需使用 CSS Module
- [ ] 模型、工具、上传等会话控件靠近输入区，不抢正文主位
- [ ] 页面文案保持创作者语义

### 6.3 开发后

- [ ] 桌面与移动端都检查布局是否保持正文优先
- [ ] 检查焦点态和键盘导航
- [ ] 检查无障碍与对比度
- [ ] 检查文档说明是否与实际代码结构一致
