# 项目设置页沉浸式体验升级 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the project settings UI to provide a minimal, centered, and immersive reading/editing experience, removing heavy borders and optimizing form layouts.

**Architecture:** We will modify the CSS grid constraints in the page layout to center the content area (`max-w-3xl`), remove the heavy `SectionCard` styling from form fieldsets in the editor, add a dirty-state indicator to the sidebar tabs, and update the audit panel with user-friendly preset filter pills.

**Tech Stack:** React, Next.js, Tailwind CSS, global CSS variables.

---

## Chunk 1: Page Layout & Sidebar Updates

### Task 1: Center and Restrict Content Width

**Files:**
- Modify: `apps/web/src/features/project-settings/components/project-settings-page.tsx`

- [ ] **Step 1: Update the layout wrapper classes**
  Change the layout so the right-side content area is centered and restricted in width for better reading flow.
  In `ProjectSettingsPage` (around line 114), find the `div` wrapping `ProjectSettingsContent`:
  ```tsx
  <div className="relative flex flex-col min-h-[600px] animate-[fadeIn_0.35s_cubic-bezier(0.16,1,0.3,1)]">
  ```
  Change it to:
  ```tsx
  <div className="relative flex flex-col min-h-[600px] animate-[fadeIn_0.35s_cubic-bezier(0.16,1,0.3,1)] max-w-3xl w-full mx-auto pb-24">
  ```
  *(Adding `max-w-3xl w-full mx-auto` centers the content and restricts it to ~768px. `pb-24` adds breathing room at the bottom).*

- [ ] **Step 2: Verify the layout change visually**
  Run the dev server and verify that navigating to project settings shows the right column constrained and centered, rather than stretching to the right edge of the 1600px container.

- [ ] **Step 3: Commit layout changes**
  ```bash
  git add apps/web/src/features/project-settings/components/project-settings-page.tsx
  git commit -m "style(ui): center and restrict project settings content width"
  ```

### Task 2: Add Dirty State Indicator (Dot) to Sidebar Tabs

**Files:**
- Modify: `apps/web/src/features/project-settings/components/project-settings-sidebar.tsx`

- [ ] **Step 1: Check existing dirty state implementation**
  Looking at `TabButton` in `project-settings-sidebar.tsx` (around line 187), the dirty dot is actually already implemented!
  ```tsx
  {dirty && (
    <span
      className="ml-auto w-2 h-2 rounded-full bg-[var(--accent-warning)]"
      aria-label="有未保存的更改"
    />
  )}
  ```
  *Self-correction: The dot is already there in the code, so we can skip implementing it. We will just verify it works.*

- [ ] **Step 2: Verify dirty dot functionality**
  Make a change in the project settings form without saving, and verify the orange dot appears next to the "设定" tab.

---

## Chunk 2: Form & Editor Visual Overhaul

### Task 3: Remove Heavy Card Styles from Fieldsets

**Files:**
- Modify: `apps/web/src/features/studio/components/project-setting-editor.tsx`

- [ ] **Step 1: Refactor fieldset classes**
  In `ProjectSettingEditorForm`, replace the heavy `fieldset` styling with a clean, borderless approach.
  Find all 4 instances of:
  ```tsx
  <fieldset className="border border-[var(--line-soft)] rounded-[var(--radius-lg)] p-7 m-0 bg-gradient-to-br from-[var(--bg-surface)] to-[rgba(255,255,255,0.95)] transition-all relative">
    <legend className="text-[0.75rem] font-semibold text-[var(--text-secondary)] px-2 ml-2 tracking-[0.08em] uppercase">...标题...</legend>
  ```
  Change them to:
  ```tsx
  <div className="space-y-4">
    <h3 className="text-lg font-semibold text-[var(--text-primary)]">...标题...</h3>
  ```
  *(We change `fieldset`/`legend` back to `div`/`h3` because semantic fieldsets sometimes struggle with flex/grid layouts in specific browsers, and we want a clean, open typography hierarchy instead of an boxed-in legend).*

- [ ] **Step 2: Adjust grid spacing**
  Ensure the grid inside those divs has appropriate spacing:
  ```tsx
  <div className="grid gap-x-8 gap-y-6 grid-cols-1 md:grid-cols-2">
  ```
  *(Increased horizontal gap `gap-x-8` for breathing room).*

- [ ] **Step 3: Add Focus Glow to Textareas**
  Find the 3 full-width textareas ("核心冲突", "剧情走向", "特殊要求").
  Update their wrapper divs from:
  ```tsx
  <div className="relative rounded-[var(--radius-md)] transition-all focus-within:shadow-[0_0_0_3px_rgba(90,122,107,0.12),0_2px_8px_rgba(90,122,107,0.08)] focus-within:bg-[rgba(255,255,255,0.02)]">
  ```
  To:
  ```tsx
  <div className="relative transition-all duration-300 focus-within:drop-shadow-[0_0_8px_rgba(90,122,107,0.15)]">
  ```
  *(Make the glow softer and wider using `drop-shadow` instead of sharp `box-shadow` borders).*

- [ ] **Step 4: Commit form style changes**
  ```bash
  git add apps/web/src/features/studio/components/project-setting-editor.tsx
  git commit -m "style(ui): flatten project setting form and enhance typography"
  ```

---

## Chunk 3: Audit Panel Refinement

### Task 4: Enhance Audit Filter UI

**Files:**
- Modify: `apps/web/src/features/project-settings/components/project-audit-panel.tsx`

- [ ] **Step 1: Refine the filter form layout**
  In `AuditFilterBar` (around line 93), change the heavy background:
  ```tsx
  <form
    className="panel-muted space-y-8 p-10"
  ```
  To a lighter, flatter look:
  ```tsx
  <form
    className="space-y-6 pb-6 border-b border-[var(--line-soft)]"
  ```

- [ ] **Step 2: Update the translation of Audit Log items**
  In `AuditLogCard` (around line 206), the text is currently:
  ```tsx
  <p className="text-sm text-[var(--text-secondary)]">
    操作人: {item.actor_user_id ?? "系统"} · 详情: {summarizeProjectAuditDetails(item.details)}
  </p>
  ```
  *Self-correction: The Chinese translation `操作人` and `详情` is already implemented in the code! We just need to ensure the preset pills work perfectly.*

- [ ] **Step 3: Commit audit panel changes**
  ```bash
  git add apps/web/src/features/project-settings/components/project-audit-panel.tsx
  git commit -m "style(ui): refine audit panel filter visuals"
  ```