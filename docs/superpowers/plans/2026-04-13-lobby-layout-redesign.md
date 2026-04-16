# 首页(Lobby)聚焦式书架布局重设计 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 精简首页侧栏间距、删除品牌标题噪音、搜索框前置为首个交互元素。

**Architecture:** 单文件改动 (`lobby-page.tsx`)，纯 UI 布局调整，不涉及数据层、路由或状态管理变更。所有改动复用现有 Design Token。

**Tech Stack:** Next.js 15, React 19, Tailwind CSS v4

**Spec:** `docs/superpowers/specs/2026-04-13-lobby-layout-redesign.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `apps/web/src/features/lobby/components/projects/lobby-page.tsx` | 首页核心组件，所有布局改动集中于此 |
| No change | `apps/web/src/components/ui/metric-card.tsx` | 组件保留，仅首页不再使用 |
| No change | `apps/web/src/features/lobby/components/projects/lobby-project-shelf.tsx` | 项目卡片网格不变 |
| No change | `apps/web/src/features/lobby/components/projects/lobby-project-model.ts` | 搜索逻辑不变 |

---

## Task 1: 精简侧栏 — 删除标题区、压缩间距

**Files:**
- Modify: `apps/web/src/features/lobby/components/projects/lobby-page.tsx:71-84`

这是侧栏部分的所有改动，集中在一个代码块中。

- [ ] **Step 1: 修改 aside 容器和内容**

将 L71-84 的 aside 块替换为以下代码：

```tsx
<aside className="panel-glass lg:sticky top-[5.5rem] flex flex-col gap-1 p-3 lg:p-4 max-lg:order-2">
  <nav className="flex flex-row lg:flex-col gap-1 overflow-x-auto scrollbar-hide max-lg:-mx-1 max-lg:px-1">
    {LOBBY_NAV_ITEMS.map((item) => (
      <LobbySidebarLink item={item} key={item.href} />
    ))}
  </nav>
  <div className="mt-auto flex flex-col gap-2 pt-3 max-lg:hidden">
    <Link
      className="flex items-center justify-center gap-1.5 rounded-2xl border border-dashed border-border px-4 py-2.5 text-[0.84rem] text-text-secondary transition-colors hover:bg-accent-soft hover:text-accent-primary"
      href="/workspace/lobby/settings?tab=assistant"
    >
      打开我的助手
    </Link>
    {model.templatePreviewNames.length > 0 && (
      <p className="text-text-tertiary text-[0.78rem] leading-relaxed px-1">
        当前节奏：{model.templatePreviewNames.join(" · ")}
      </p>
    )}
  </div>
</aside>
```

改动要点：
- 删除标题区 `div.grid.gap-2.px-1.pt-1`（"书架" + "作品空间"）
- padding: `p-4 lg:p-5` → `p-3 lg:p-4`
- nav gap: `gap-1.5` → `gap-1`
- "当前节奏"从独立卡片精简为一行小字，有模板时显示，无模板时隐藏
- "打开我的助手"按钮移入侧栏底部（max-lg:hidden，移动端靠导航项"我的助手"）

- [ ] **Step 2: 修改 LobbySidebarLink 间距**

> 注意：Step 1 已修改了 aside 块导致行号偏移，请通过搜索 `LobbySidebarLink` 组件定位。

在该组件的 className 中替换：
- `p-3.5 pl-4` → `p-2.5 pl-3`
- `before:top-3.5 before:bottom-3.5` → `before:top-2.5 before:bottom-2.5`

- [ ] **Step 3: 目视验证侧栏**

在浏览器打开 `/workspace/lobby`，检查：
- 导航项从顶部开始，间距明显缩小
- "打开我的助手"出现在侧栏底部
- "当前节奏"为小字（有模板时显示）
- 激活态指示条对齐正常

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/features/lobby/components/projects/lobby-page.tsx
git commit -m "refactor(lobby): 精简侧栏 — 删除标题区、压缩间距、助手按钮移入底部"
```

---

## Task 2: 重构主区域 — 搜索框前置、删除品牌标题

**Files:**
- Modify: `apps/web/src/features/lobby/components/projects/lobby-page.tsx:87-128`

主区域改动：删除 header + 重构搜索区。

- [ ] **Step 1: 删除 MetricCard import**

删除 L6 的 `import { MetricCard } from "@/components/ui/metric-card";`

- [ ] **Step 2: 替换 main 区域内容**

将 L87-128 的整个 `<main>` 块替换为：

```tsx
<main className="grid gap-5 min-w-0 max-lg:order-1">
  <div className="flex flex-wrap gap-3 items-center max-lg:flex-col max-lg:stretch">
    <input
      className="ink-input-roomy min-h-12 flex-1 max-lg:w-full text-[0.95rem]"
      placeholder="搜索作品名、题材或模板…"
      value={model.searchText}
      onChange={(event) => model.setSearchText(event.target.value)}
    />
    <Link className="ink-button whitespace-nowrap max-lg:w-full max-lg:text-center" href="/workspace/lobby/new">
      新建作品
    </Link>
  </div>

  <p className="text-text-tertiary text-[0.84rem]">
    {model.searchText
      ? `筛选出 ${filteredProjectCount} 部作品`
      : `共 ${projectCount} 部作品`}
  </p>

  <LobbyProjectShelf
    actionMutation={model.actionMutation}
    deletedOnly={false}
    error={model.projectsQuery.error}
    isLoading={model.projectsQuery.isLoading}
    projects={model.filteredProjects}
    templateNameById={model.templateNameById}
  />
</main>
```

改动要点：
- 删除整个 header 区块（"继续创作" + 大标题 + 按钮）
- 搜索框提升为第一个元素，无 label、无 panel-shell 包裹
- "新建作品"按钮与搜索框同行
- 统计精简为一行条件文字（无搜索/有搜索两种状态）
- main gap 从 `gap-6` → `gap-5`

- [ ] **Step 3: 修改网格列宽**

在外层 grid 容器（L70）中，将 `272px` 改为 `240px`：

```
lg:[grid-template-columns:240px_minmax(0,1fr)]
```

- [ ] **Step 4: 清理不再使用的变量**

检查 `helperText` 变量。如果 Task 1 中已将 templatePreviewNames 用于"当前节奏"文字，则 `helperText` 不再被引用，应删除：

```tsx
// 删除以下代码
const helperText = model.templatePreviewNames.length > 0
  ? `最近常用模板：${model.templatePreviewNames.join(" · ")}`
  : "新建作品后，助手和模板自动就位。";
```

> 注：`model.templateCount` 不再在本文件被引用（原 MetricCard 使用），但它是 model 返回值的一部分，删除 import 无需处理 model 内部。

- [ ] **Step 5: 目视验证主区域**

在浏览器检查：
- 搜索框是主区域第一个元素
- "新建作品"按钮在搜索框右侧同行
- 统计文字在搜索框下方（"共 N 部作品"）
- 输入搜索词后统计文字变为"筛选出 M 部作品"
- 项目卡片网格正常显示
- 移动端：搜索框全宽，新建按钮独占一行

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/features/lobby/components/projects/lobby-page.tsx
git commit -m "refactor(lobby): 搜索框前置、删除品牌标题、统计精简为一行文字"
```

---

## Task 3: 最终验证与清理

- [ ] **Step 1: 全页面功能回归**

在浏览器中测试以下场景：
1. 搜索框输入关键词 → 卡片实时过滤 → 统计文字更新
2. 点击侧栏"我的作品"→ 当前页面正常
3. 点击侧栏"打开我的助手"→ 跳转正常
4. 点击"新建作品"→ 跳转正常
5. 点击项目卡片"继续创作"→ 跳转正常
6. 缩小窗口到移动端宽度 → aside 下移、导航横向、搜索全宽

- [ ] **Step 2: 清理无用 import**

确认 `MetricCard` import 已删除，无其他未使用的 import。

- [ ] **Step 3: 验证无 TypeScript 错误**

```bash
cd apps/web && npx tsc --noEmit --pretty 2>&1 | head -20
```

Expected: 无与 `lobby-page.tsx` 相关的错误。

- [ ] **Step 4: Final commit（如有清理改动）**

```bash
git add -A
git commit -m "chore(lobby): 清理首页布局重设计遗留"
```
