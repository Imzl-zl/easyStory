# 前端样式统一重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一 Ink 设计语言的主题色、消灭硬编码颜色、归一按钮体系和圆角、修复 Studio 共创助手对比度

**Architecture:** 重建 `globals.css` 的 `:root` Token 体系，补充 callout/toolbar/chat 语义 Token，新增 ink-toolbar-* CSS 类。然后逐模块替换组件中的硬编码颜色和分裂按钮，统一圆角为 4 级语义。

**Tech Stack:** CSS Custom Properties + Tailwind CSS 4 + React 19 (纯样式改动，不改业务逻辑)

**Spec:** `docs/superpowers/specs/2026-04-12-frontend-style-unification-design.md`

---

## 文件结构

### 修改 — globals.css (核心)

| 文件 | 职责 |
|------|------|
| `apps/web/src/app/globals.css` | 更新 `:root` Token、新增 CSS 复合类、更新 ink-button-secondary 背景 |

### 修改 — Studio 共创助手 (9 文件)

| 文件 | 职责 |
|------|------|
| `apps/web/src/features/studio/components/chat/studio-chat-composer.tsx` | 替换 Arco Button + 自定义工具栏按钮为 ink-toolbar-* + bg-white/N |
| `apps/web/src/features/studio/components/chat/studio-chat-message-bubble.tsx` | 替换 Arco Button 为 ink-button-secondary + 硬编码颜色 |
| `apps/web/src/features/studio/components/chat/studio-chat-history-panel.tsx` | 替换 Arco Button + 新对话/历史触发器 |
| `apps/web/src/features/studio/components/chat/studio-chat-skill-panel.tsx` | 替换硬编码颜色 + 自定义按钮为 ink-toolbar-* + chat token 引用 |
| `apps/web/src/features/studio/components/chat/ai-chat-panel.tsx` | 替换硬编码颜色 |
| `apps/web/src/features/studio/components/tree/document-tree.tsx` | `bg-[#b0bac8]` → token |
| `apps/web/src/features/studio/components/document/markdown-document-editor.tsx` | `bg-[#ffffff]` → token |
| `apps/web/src/features/studio/components/document/json-document-editor.tsx` | `bg-[#ffffff]` → token |
| `apps/web/src/features/studio/components/document/chapter-stale-notice.tsx` | callout-warning |

### 修改 — Incubator 模块 (5 文件)

| 文件 | 职责 |
|------|------|
| `apps/web/src/features/lobby/components/incubator/incubator-chat-panel.tsx` | 替换 Arco Button + 硬编码 rgba/渐变 |
| `apps/web/src/features/lobby/components/incubator/incubator-chat-panel-support.tsx` | 替换 Arco Button + 硬编码 rgba |
| `apps/web/src/features/lobby/components/incubator/incubator-chat-draft-panel-support.tsx` | 替换 Arco Button (2处) |
| `apps/web/src/features/lobby/components/incubator/incubator-chat-draft-guidance.tsx` | 替换 Arco Button |
| `apps/web/src/features/lobby/components/incubator/incubator-chat-history-panel.tsx` | 替换 Arco Button (2处) + 硬编码颜色 |

### 修改 — 认证和布局 (2 文件)

| 文件 | 职责 |
|------|------|
| `apps/web/src/features/auth/components/auth-form.tsx` | 提取渐变背景为 CSS 变量 |
| `apps/web/src/features/workspace/components/workspace-shell.tsx` | 替换硬编码 rgba |

### 修改 — Callout 横幅组件 (~15 文件)

| 文件 | 职责 |
|------|------|
| `apps/web/src/features/engine/components/engine-export-panel.tsx` | callout-success |
| `apps/web/src/features/engine/components/engine-task-form-panels.tsx` | callout-warning |
| `apps/web/src/features/config-registry/components/config-registry-page-primitives.tsx` | callout-info |
| `apps/web/src/features/config-registry/components/config-registry-skill-reader.tsx` | callout-info |
| `apps/web/src/features/settings/components/credential/credential-center-list.tsx` | 硬编码 → token |
| `apps/web/src/features/settings/components/credential/credential-center-form.tsx` | callout-info |
| `apps/web/src/features/lobby/components/projects/lobby-project-shelf.tsx` | 硬编码 → token |
| `apps/web/src/features/settings/components/assistant/assistant-preferences-form.tsx` | callout-warning |
| `apps/web/src/features/settings/components/assistant/assistant-skill-editor.tsx` | callout-warning |
| `apps/web/src/features/settings/components/assistant/assistant-hook-guided-fields.tsx` | callout-info |
| `apps/web/src/features/settings/components/assistant/assistant-agent-guided-editor.tsx` | callout-info |
| `apps/web/src/features/settings/components/assistant/assistant-getting-started-panel.tsx` | 渐变 → CSS 变量 |
| `apps/web/src/features/settings/components/assistant/assistant-config-file-map-panel.tsx` | 渐变 → CSS 变量 |
| `apps/web/src/features/project-settings/components/project-setting-summary-editor.tsx` | callout-warning |
| `apps/web/src/features/project-settings/components/project-setting-summary-panel.tsx` | callout-warning |
| `apps/web/src/features/studio/components/document/chapter-stale-notice.tsx` | callout-warning |
| `apps/web/src/features/engine/components/engine-task-panel.tsx` | callout-warning |
| `apps/web/src/features/engine/components/engine-workflow-status-callout.tsx` | callout-warning + callout-info |
| `apps/web/src/features/lobby/components/templates/template-library-editor-panel.tsx` | callout-warning + callout-info |
| `apps/web/src/features/lobby/components/incubator/incubator-preview.tsx` | callout-warning + callout-info + accent-info |
| `apps/web/src/components/ui/app-select.tsx` | callout-warning |
| `apps/web/src/features/lobby/components/incubator/incubator-panels-support.tsx` | 硬编码 → token |
| `apps/web/src/features/lobby/components/incubator/incubator-chat-settings-panel.tsx` | callout-info |

---

## Task 1: 更新 globals.css — 主题色 Token

**Files:**
- Modify: `apps/web/src/app/globals.css` (`:root` 部分)

- [ ] **Step 1: 更新 `:root` 中的主题色 Token**

在 `globals.css` 的 `:root { ... }` 中替换以下值：

```
--accent-primary: #7c6e5d;
--accent-primary-hover: #6d604f;
--accent-primary-dark: #5b5040;
--accent-primary-soft: rgba(124, 110, 93, 0.12);
--accent-primary-muted: rgba(124, 110, 93, 0.14);
--accent-secondary: #9a9088;  /* 暖棕调和，配合新 primary */
--accent-tertiary: #b8b4ae;  /* 微调，跟随暖色调 */
--accent-success: #6b8f71;
--accent-warning: #b8944a;
--accent-danger: #b85c5c;
--accent-ink: #7c6e5d;
--accent-danger-active: rgba(160, 75, 75, 0.9);
--line-strong: rgba(124, 110, 93, 0.20);
--line-focus: rgba(124, 110, 93, 0.28);
--bg-elevated: #ffffff;
```

新增缺失 Token：
```
--accent-info: #5a8faa;
--accent-info-soft: rgba(90, 143, 170, 0.10);
--accent-info-muted: rgba(90, 143, 170, 0.18);
```

- [ ] **Step 2: 更新 Arco 主题色同步**

将 body 中的 `--arco-color-primary-6` 系列值更新为新 `#7c6e5d` 及衍生色：

```
--arco-color-primary-6: #7c6e5d;
--arco-color-primary-5: #8c7e6d;
--arco-color-primary-4: #9c8e7d;
--arco-color-primary-3: #ac9e8d;
--arco-color-primary-2: #bcae9d;
--arco-color-primary-1: #ccbead;
--arco-color-primary-7: #6d604f;
--arco-color-primary-8: #5b5040;
--arco-color-primary-9: #4a4030;
--arco-color-primary-10: #3a3020;
```

- [ ] **Step 3: 验证构建**

Run: `cd apps/web && npx next build 2>&1 | head -20`
Expected: 构建成功，无 CSS 相关错误

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/app/globals.css
git commit -m "style: 更新主题色 Token 为暖棕文学风格"
```

---

## Task 2: 更新 globals.css — 新增语义 Token 和 CSS 类

**Files:**
- Modify: `apps/web/src/app/globals.css`

- [ ] **Step 1: 在 `:root` 末尾新增语义 Token**

```css
/* Callout 语义色 */
--callout-info-bg: rgba(58, 124, 165, 0.07);
--callout-info-border: rgba(58, 124, 165, 0.16);
--callout-warning-bg: rgba(183, 121, 31, 0.08);
--callout-warning-border: rgba(183, 121, 31, 0.20);
--callout-success-bg: rgba(47, 107, 69, 0.08);
--callout-success-border: rgba(47, 107, 69, 0.18);
--callout-danger-bg: rgba(184, 92, 92, 0.08);
--callout-danger-border: rgba(184, 92, 92, 0.16);

/* Toolbar 语义色 */
--toolbar-bg: var(--bg-surface);
--toolbar-bg-hover: rgba(124, 110, 93, 0.08);
--toolbar-bg-active: rgba(124, 110, 93, 0.14);
--toolbar-border: var(--line-strong);
--toolbar-text: var(--text-secondary);
--toolbar-text-active: var(--accent-primary);

/* Chat 语义色 */
--chat-user-bubble-bg: var(--bg-muted);
--chat-assistant-bubble-bg: var(--accent-primary-soft);
--chat-skill-panel-bg: var(--bg-surface);
--chat-skill-option-active-bg: var(--accent-primary-soft);

/* 场景渐变 */
--auth-bg-gradient: radial-gradient(circle at top left, rgba(196,167,125,0.18), transparent 30%), radial-gradient(circle at right 20%, rgba(90,154,170,0.16), transparent 28%), linear-gradient(180deg, #ebeef3 0%, #f4efe7 48%, #f4f5f7 100%);
--workspace-shell-accent-gradient: radial-gradient(circle at top left, rgba(124,110,93,0.04), transparent 26%);
```

- [ ] **Step 2: 在现有 CSS 类之后新增 callout 复合类**

在 `.badge--danger { ... }` 之后，新增：

```css
.callout-info {
  background: var(--callout-info-bg);
  border: 1px solid var(--callout-info-border);
  border-radius: var(--radius-2xl);
  padding: 12px 16px;
}
.callout-warning {
  background: var(--callout-warning-bg);
  border: 1px solid var(--callout-warning-border);
  border-radius: var(--radius-2xl);
  padding: 12px 16px;
}
.callout-success {
  background: var(--callout-success-bg);
  border: 1px solid var(--callout-success-border);
  border-radius: var(--radius-2xl);
  padding: 12px 16px;
}
.callout-danger {
  background: var(--callout-danger-bg);
  border: 1px solid var(--callout-danger-border);
  border-radius: var(--radius-2xl);
  padding: 12px 16px;
}
```

- [ ] **Step 3: 在现有 ink-pill 之后新增 toolbar CSS 类**

在 `.ink-pill:disabled { ... }` 之后，新增完整的 `ink-toolbar-icon`、`ink-toolbar-chip`、`ink-toolbar-toggle` 定义（完整 CSS 见 spec 第四节 4.2）。**注意：三个类都必须包含 `:focus-visible { outline: 2px solid var(--accent-primary); outline-offset: 2px; }` 以保证键盘可访问性。**

**设计说明：** callout Token（`--callout-info-*`）和 accent-info Token（`--accent-info-*`）是两套独立调色。callout 用于横幅/面板背景（低透明度），accent-info 用于文字/图标/徽章（高饱和度）。分开定义是为了暗色模式时可独立调参。

- [ ] **Step 4: 更新 `ink-button-secondary` 的 background**

将 `.ink-button-secondary` 的 `background: var(--bg-surface)` 改为 `background: var(--bg-elevated)`。

- [ ] **Step 5: 验证构建**

Run: `cd apps/web && npx next build 2>&1 | head -20`
Expected: 构建成功

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/globals.css
git commit -m "style: 新增 callout/toolbar/chat 语义 Token 和 CSS 复合类"
```

---

## Task 2.5: 圆角统一 — 批量替换

**前置依赖：** Task 2（CSS 类已就位）

**规则：**
- 新增 CSS 类（`ink-toolbar-*`、`callout-*`）已内置正确圆角，无需额外处理
- 此 Task 处理现有组件中直接使用 Tailwind `rounded-*` 的情况

**替换映射：**
| 当前 | 替换为 | 适用场景 |
|------|--------|---------|
| `rounded` (6px) | 保持（`--radius-xs` 内部 token） | 状态标签 |
| `rounded-md` (8px) | 保持（`--radius-sm` 内部 token） | 附件 pill |
| `rounded-xl` (16px) | `rounded-2xl` | 面板内部区域、下拉触发 |
| `rounded-full` (9999px) | `rounded-pill` | chip/触发器按钮 |
| `rounded-[10px]` | `rounded-lg` | 空状态图标 |

**注意：** `rounded-lg` (12px)、`rounded-2xl` (20px)、`rounded-3xl`+ (hero-card 内置) 保持不变。

- [ ] **Step 1: 全局搜索替换 `rounded-xl` → `rounded-2xl`**

Run:
```bash
cd apps/web/src && grep -rn "rounded-xl\b" --include="*.tsx" | grep -v "rounded-2xl\|rounded-3xl\|rounded-4xl\|rounded-5xl\|globals.css" | head -30
```
在列出的文件中，将独立的 `rounded-xl` 替换为 `rounded-2xl`（面板内部区域）。注意不要影响已经是 `rounded-2xl` 或更大圆角的。

- [ ] **Step 2: 全局搜索替换 `rounded-full` → `rounded-pill`**

Run:
```bash
cd apps/web/src && grep -rn "rounded-full" --include="*.tsx" | grep -v "globals.css" | head -30
```
在列出的文件中，将按钮/触发器上的 `rounded-full` 替换为 `rounded-pill`。

- [ ] **Step 3: 验证构建**

Run: `cd apps/web && npx next build 2>&1 | head -20`

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "style: 圆角统一 — rounded-xl→2xl, rounded-full→pill"
```

---

**Files:**
- Modify: `apps/web/src/features/studio/components/chat/studio-chat-composer.tsx`

- [ ] **Step 1: 替换 ToolbarIconButton 内联样式为 `ink-toolbar-icon`**

找到 `ToolbarIconButton` 组件（内联函数或子组件），将其 className 从自定义 Tailwind 替换为 `ink-toolbar-icon`。

- [ ] **Step 2: 替换 ToolbarChipButton 为 `ink-toolbar-chip`**

找到 `ToolbarChipButton` 组件，替换为使用 `ink-toolbar-chip` 类，通过 `data-active` 控制激活态。

- [ ] **Step 3: 替换 ToolbarToggleButton 为 `ink-toolbar-toggle`**

找到 `ToolbarToggleButton` 组件，替换为使用 `ink-toolbar-toggle` 类，通过 `aria-pressed` 控制激活态。

- [ ] **Step 4: 替换 ReasoningChipButton 为 `ink-toolbar-chip`**

找到 `ReasoningChipButton` 组件，替换为 `ink-toolbar-chip` + `data-active`。

- [ ] **Step 5: 替换发送按钮的 Arco `<Button>` 为 `<button className="ink-button">`**

将 `<Button type="primary" shape="round" loading={isResponding} ...>` 替换为 `<button className="ink-button" disabled={isResponding || !canChat}>`。Loading 态通过条件渲染内部图标/文字实现。

- [ ] **Step 6: 替换渠道下拉触发器**

找到渠道选择触发器元素（`bg-white/92 shadow-xs` + `rounded-xl`），替换为使用 `ink-toolbar-chip` 类 + 适当增大尺寸（添加 `h-10 px-3`）。

- [ ] **Step 7: 替换 `bg-white/N` 半透明背景**

搜索文件中所有 `bg-white/92`、`bg-white/90`、`bg-white/95` 等用法，替换为 `bg-surface/92`、`bg-surface/90`、`bg-surface/95`。

- [ ] **Step 8: 移除 `@arco-design/web-react` 的 Button import（如果仅此处使用）**

如果 `studio-chat-composer.tsx` 中 `Button` 不再被其他地方引用，从 import 中移除。

- [ ] **Step 7: 验证构建 + 视觉检查**

Run: `cd apps/web && npx next build 2>&1 | head -20`
Expected: 构建成功

- [ ] **Step 8: Commit**

```bash
git add apps/web/src/features/studio/components/chat/studio-chat-composer.tsx
git commit -m "style: Studio Composer 按钮统一为 ink-toolbar-* 体系"
```

---

## Task 4: Studio 聊天面板 — 替换按钮和硬编码颜色

**Files:**
- Modify: `apps/web/src/features/studio/components/chat/studio-chat-message-bubble.tsx`
- Modify: `apps/web/src/features/studio/components/chat/studio-chat-history-panel.tsx`
- Modify: `apps/web/src/features/studio/components/chat/studio-chat-skill-panel.tsx`
- Modify: `apps/web/src/features/studio/components/chat/ai-chat-panel.tsx`

- [ ] **Step 1: studio-chat-message-bubble.tsx — 替换 Arco Button**

将 3 个 `<Button size="mini" shape="round" type="secondary">` 替换为 `<button className="ink-button-secondary text-xs h-7 px-2.5">`。
替换 `bg-[rgba(61,61,61,0.06)]` / `bg-[rgba(61,61,61,0.05)]` → `bg-surface-hover`。

- [ ] **Step 2: studio-chat-history-panel.tsx — 替换 Arco Button + 触发器**

将"新对话"按钮替换为 `<button className="ink-button-secondary text-xs h-7.5 px-3">`。
将历史记录触发器替换为 `<button className="ink-toolbar-chip">`。
将删除按钮 `<Button shape="circle" status="danger" type="text">` 替换为 `<button className="ink-icon-button text-accent-danger">`。
替换 `bg-[#f3ede3]` → `bg-muted`。

- [ ] **Step 3: studio-chat-skill-panel.tsx — 替换硬编码颜色和按钮**

逐元素替换：
- `bg-[rgba(43,33,21,0.08)]` → `bg-surface-hover`
- `bg-[rgba(125,153,178,0.07)]` → `bg-accent-primary-soft`
- `bg-[rgba(238,244,234,0.86)]`（选项卡片激活态）→ `bg-[var(--chat-skill-option-active-bg)]`
- `bg-[rgba(249,246,239,0.92)]`（面板背景）→ `bg-[var(--chat-skill-panel-bg)]` + `backdrop-blur`
- `bg-[#ffffff]` → `bg-surface`
- `bg-white/92` 等 → `bg-surface/92`
- Skill 触发器和 mode 按钮替换为 `ink-toolbar-chip`

- [ ] **Step 4: ai-chat-panel.tsx — 替换硬编码颜色**

替换硬编码 rgba 颜色为对应 token。

- [ ] **Step 5: 验证构建**

Run: `cd apps/web && npx next build 2>&1 | head -20`

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/features/studio/components/chat/
git commit -m "style: Studio 聊天面板统一按钮体系和消灭硬编码颜色"
```

---

## Task 5: Studio 文档编辑器 — 替换硬编码颜色

**Files:**
- Modify: `apps/web/src/features/studio/components/tree/document-tree.tsx`
- Modify: `apps/web/src/features/studio/components/document/markdown-document-editor.tsx`
- Modify: `apps/web/src/features/studio/components/document/json-document-editor.tsx`
- Modify: `apps/web/src/features/studio/components/document/chapter-stale-notice.tsx`

- [ ] **Step 1: document-tree.tsx** — `bg-[#b0bac8]` → `bg-text-tertiary/40` 或合适的 token

- [ ] **Step 2: markdown-document-editor.tsx** — `bg-[#ffffff]` → `bg-surface`

- [ ] **Step 3: json-document-editor.tsx** — `bg-[#ffffff]` → `bg-surface`

- [ ] **Step 4: chapter-stale-notice.tsx** — `border-[rgba(183,121,31,0.24)] bg-[rgba(183,121,31,0.08)]` → `callout-warning` 类

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/studio/
git commit -m "style: Studio 文档编辑器和通知替换硬编码颜色"
```

---

## Task 6: Incubator 模块 — 替换 Arco Button 和硬编码颜色

**Files:**
- Modify: `apps/web/src/features/lobby/components/incubator/incubator-chat-panel.tsx`
- Modify: `apps/web/src/features/lobby/components/incubator/incubator-chat-panel-support.tsx`
- Modify: `apps/web/src/features/lobby/components/incubator/incubator-chat-draft-panel-support.tsx`
- Modify: `apps/web/src/features/lobby/components/incubator/incubator-chat-draft-guidance.tsx`
- Modify: `apps/web/src/features/lobby/components/incubator/incubator-chat-history-panel.tsx`

- [ ] **Step 1: incubator-chat-panel.tsx**

替换发送按钮 `<Button type="primary" shape="round">` → `<button className="ink-button">`。
替换 `bg-[rgba(31,27,22,0.05)]` → `bg-surface-hover`。
替换 `bg-[linear-gradient(...)]` → CSS 变量引用。

- [ ] **Step 2: incubator-chat-panel-support.tsx**

替换 `<Button>` → `<button className="ink-button-secondary">`。
替换 `border-[rgba(183,121,31,0.16)]` / `bg-[rgba(183,121,31,0.1)]` → `callout-warning` 类。

- [ ] **Step 3: incubator-chat-draft-panel-support.tsx**

替换 2 个 `<Button>` → `<button className="ink-button-secondary">`。
替换 `bg-[rgba(183,121,31,0.14)]` → `callout-warning` 类或 `bg-accent-warning/14`。

- [ ] **Step 4: incubator-chat-draft-guidance.tsx**

替换 `<Button>` → `<button className="ink-button-secondary">`。

- [ ] **Step 5: incubator-chat-history-panel.tsx**

替换 2 个 `<Button>` → `<button className="ink-button">` / `<button className="ink-button-secondary">`。
替换 `bg-[#f3ede3]` → `bg-muted`。

- [ ] **Step 6: 验证构建**

Run: `cd apps/web && npx next build 2>&1 | head -20`

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/features/lobby/components/incubator/
git commit -m "style: Incubator 模块统一按钮体系和消灭硬编码颜色"
```

---

## Task 7: 认证和布局 — 替换硬编码颜色

**Files:**
- Modify: `apps/web/src/features/auth/components/auth-form.tsx`
- Modify: `apps/web/src/features/workspace/components/workspace-shell.tsx`

- [ ] **Step 1: auth-form.tsx**

将主背景的 `[background:radial-gradient(...)...linear-gradient(...)]` 替换为 `[background:var(--auth-bg-gradient)]`。

- [ ] **Step 2: workspace-shell.tsx**

将 `[background:radial-gradient(circle_at_top_left,rgba(125,153,178,0.04),transparent_26%),var(--bg-canvas)]` 替换为 `[background:var(--workspace-shell-accent-gradient),var(--bg-canvas)]`。

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/auth/components/auth-form.tsx apps/web/src/features/workspace/components/workspace-shell.tsx
git commit -m "style: 认证和布局背景渐变提取为 CSS 变量"
```

---

## Task 8: Callout 横幅组件批量替换 (Part 1 — Engine + Config + Credential)

**Files:**
- Modify: `apps/web/src/features/engine/components/engine-export-panel.tsx`
- Modify: `apps/web/src/features/engine/components/engine-task-form-panels.tsx`
- Modify: `apps/web/src/features/engine/components/engine-task-panel.tsx`
- Modify: `apps/web/src/features/engine/components/engine-workflow-status-callout.tsx`
- Modify: `apps/web/src/features/config-registry/components/config-registry-page-primitives.tsx`
- Modify: `apps/web/src/features/config-registry/components/config-registry-skill-reader.tsx`
- Modify: `apps/web/src/features/settings/components/credential/credential-center-list.tsx`
- Modify: `apps/web/src/features/settings/components/credential/credential-center-form.tsx`

**替换规则：**
- `bg-[rgba(58,124,165,0.07~0.1)]` + 对应 `border-[rgba(58,124,165,...)]` → `callout-info` 类
- `bg-[rgba(47,107,69,0.08)]` + 对应 border → `callout-success` 类
- `bg-[rgba(31,27,22,0.06)]` / `bg-[rgba(31,27,22,0.18)]` → `bg-surface-hover` / `bg-surface-active`

- [ ] **Step 1: 逐文件替换硬编码为 callout-* 类**

- [ ] **Step 2: 验证构建**

Run: `cd apps/web && npx next build 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/engine/ apps/web/src/features/config-registry/ apps/web/src/features/settings/components/credential/
git commit -m "style: Engine/Config/Credential 组件 callout 横幅统一"
```

---

## Task 9: Callout 横幅组件批量替换 (Part 2 — Settings + Project + Lobby)

**Files:**
- Modify: `apps/web/src/features/settings/components/assistant/preferences/assistant-preferences-form.tsx`
- Modify: `apps/web/src/features/settings/components/assistant/skills/assistant-skill-editor.tsx`
- Modify: `apps/web/src/features/settings/components/assistant/hooks/assistant-hook-guided-fields.tsx`
- Modify: `apps/web/src/features/settings/components/assistant/agents/assistant-agent-guided-editor.tsx`
- Modify: `apps/web/src/features/settings/components/assistant/common/assistant-getting-started-panel.tsx`
- Modify: `apps/web/src/features/settings/components/assistant/common/assistant-config-file-map-panel.tsx`
- Modify: `apps/web/src/features/project-settings/components/project-setting-summary-editor.tsx`
- Modify: `apps/web/src/features/project-settings/components/project-setting-summary-panel.tsx`
- Modify: `apps/web/src/features/lobby/components/projects/lobby-project-shelf.tsx`
- Modify: `apps/web/src/components/ui/app-select.tsx`

**替换规则：**
- `bg-[rgba(183,121,31,0.08~0.14)]` + border → `callout-warning`
- `bg-[rgba(196,136,61,0.08~0.16)]` + border → `callout-warning`
- `bg-[rgba(58,124,165,0.07~0.1)]` + border → `callout-info`
- `bg-[linear-gradient(...)]` → CSS 变量引用

- [ ] **Step 1: 逐文件替换**

- [ ] **Step 2: 验证构建**

Run: `cd apps/web && npx next build 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/settings/components/assistant/ apps/web/src/features/project-settings/ apps/web/src/features/lobby/components/projects/ apps/web/src/components/ui/app-select.tsx
git commit -m "style: Settings/Project/Lobby 组件 callout 横幅统一"
```

---

## Task 10: Incubator 辅助模块 + 模板编辑器 + Preview

**Files:**
- Modify: `apps/web/src/features/lobby/components/incubator/incubator-panels-support.tsx`
- Modify: `apps/web/src/features/lobby/components/incubator/incubator-chat-settings-panel.tsx`
- Modify: `apps/web/src/features/lobby/components/incubator/incubator-preview.tsx`
- Modify: `apps/web/src/features/lobby/components/templates/template-library-editor-panel.tsx`

**替换规则：**
- `border-[rgba(19,19,18,0.08)]` → `border-line-soft`
- `bg-[rgba(58,124,165,0.08~0.1)]` + border → `callout-info`
- `bg-[rgba(183,121,31,0.14)]` + border → `callout-warning`
- incubator-preview 中 `accent-info` 引用需确保 Task 1 中 `--accent-info` Token 已定义

- [ ] **Step 1: 替换硬编码**

- [ ] **Step 2: 验证构建**

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/features/lobby/components/incubator/
git commit -m "style: Incubator 辅助模块替换硬编码颜色"
```

---

## Task 11: 全局验证

- [ ] **Step 1: 搜索残留硬编码颜色**

Run:
```bash
cd apps/web/src && grep -rn 'bg-\[rgba(' --include="*.tsx" --include="*.ts" | grep -v "globals.css" | grep -v "dangerouslySetInnerHTML" | head -30
```
Expected: 无结果（注意：如果一行同时有 rgba 和 var(--)，仍然会被捕获，需要人工判断）

- [ ] **Step 2: 搜索残留 Arco Button 直接使用**

Run:
```bash
cd apps/web/src && grep -rn '<Button ' --include="*.tsx" | grep -v "ink-button" | head -20
```
Expected: 无结果

- [ ] **Step 3: 搜索残留 `bg-[#` 硬编码**

Run:
```bash
cd apps/web/src && grep -rn 'bg-\[#' --include="*.tsx" | head -20
```
Expected: 无结果

- [ ] **Step 4: 构建验证**

Run: `cd apps/web && npx next build`
Expected: 构建成功

- [ ] **Step 5: 最终 Commit（如有修复）**

```bash
git add -A
git commit -m "style: 前端样式统一重构完成 — 残留清理"
```
