# easyStory 前端 UI 重构计划

> 文档状态：历史实施记录
>
> 当前 UI 真值请以 [docs/ui/README.md](../ui/README.md)、[前端页面 / 组件 / 样式对照](../ui/frontend-page-component-style-map.md)、相关页面级 UI 文档和当前前端代码为准。本计划保留为当时的重构路线，不再单独代表当前 UI 真值。

**Goal:** 在不重写主路由和核心数据链的前提下，把 easyStory 现有前端逐步收口为 creator-first 的创作产品，让主路径页面统一符合“书架 -> 起稿 -> 创作 -> 推进 -> 洞察”的产品心智。

**Source of Truth:** [UI 文档导航](../ui/README.md)、[前端页面 / 组件 / 样式对照](../ui/frontend-page-component-style-map.md)。涉及运行时样式时，以 `apps/web/src/app/globals.css` 与 `apps/web/tailwind.config.ts` 为准。

---

## 1. 已定边界

1. 前端主路径继续沿用现有路由，不新增第二套 `/demo` 或 `v2` 页面树
2. `src/app/**` 继续只做路由装配，重构主战场在 `src/features/**`
3. `src/components/ui/**` 只承载真正跨页面复用的 UI 原件，不为重构临时造新组件库
4. 样式真值继续收口在 `apps/web/src/app/globals.css` 与 `apps/web/tailwind.config.ts`
5. 页面语义、交互语义和技术配置必须保持单一真值，不再并行维护“概念版 UI”和“真实运行时 UI”
6. 重构优先改页面壳层、信息架构和交互语义，尽量不先动 API 契约和后端边界

---

## 2. 范围与非目标

### 2.1 本轮范围

- Workspace 全局壳层
- Lobby（书架）
- Incubator（项目起稿）
- Studio（创作桌面）
- Engine（推进）
- Lab（洞察）
- Project Settings（项目设置）
- Lobby Settings（大厅设置）
- Template Library（模板库）
- Recycle Bin（回收站）
- Config Registry（高级控制面，作为降级和收口对象）

### 2.2 非目标

- 不新建第二套路由体系
- 不先重写现有 query / mutation / store 基础设施
- 不先追求“全 Tailwind”或“全组件库化”
- 不把高级配置页重新抬回主路径中心

---

## 3. 当前源码锚点

### 3.1 路由入口

```text
apps/web/src/app/workspace/layout.tsx
apps/web/src/app/workspace/lobby/page.tsx
apps/web/src/app/workspace/lobby/new/page.tsx
apps/web/src/app/workspace/lobby/settings/page.tsx
apps/web/src/app/workspace/lobby/config-registry/page.tsx
apps/web/src/app/workspace/lobby/templates/page.tsx
apps/web/src/app/workspace/lobby/templates/[templateId]/page.tsx
apps/web/src/app/workspace/lobby/recycle-bin/page.tsx
apps/web/src/app/workspace/project/[projectId]/studio/page.tsx
apps/web/src/app/workspace/project/[projectId]/engine/page.tsx
apps/web/src/app/workspace/project/[projectId]/lab/page.tsx
apps/web/src/app/workspace/project/[projectId]/settings/page.tsx
```

### 3.2 页面实现主入口

```text
apps/web/src/features/workspace/components/workspace-shell.tsx
apps/web/src/features/lobby/components/projects/lobby-page.tsx
apps/web/src/features/lobby/components/incubator/incubator-page.tsx
apps/web/src/features/lobby/components/settings/lobby-settings-page.tsx
apps/web/src/features/lobby/components/templates/template-library-page.tsx
apps/web/src/features/lobby/components/recycle-bin/recycle-bin-page.tsx
apps/web/src/features/studio/components/page/studio-page.tsx
apps/web/src/features/engine/components/engine-page.tsx
apps/web/src/features/lab/components/lab-page.tsx
apps/web/src/features/project-settings/components/project-settings-page.tsx
apps/web/src/features/config-registry/components/config-registry-page.tsx
```

### 3.3 共享样式与 UI 原件

```text
apps/web/src/app/globals.css
apps/web/tailwind.config.ts
apps/web/src/components/ui/section-card.tsx
apps/web/src/components/ui/page-header-shell.tsx
apps/web/src/components/ui/dialog-shell.tsx
apps/web/src/components/ui/empty-state.tsx
apps/web/src/components/ui/status-badge.tsx
apps/web/src/components/ui/app-select.tsx
apps/web/src/components/ui/code-block.tsx
apps/web/src/components/ui/guarded-link.tsx
apps/web/src/components/ui/unsaved-changes-dialog.tsx
apps/web/src/lib/utils/cn.ts
```

---

## 4. 页面挂钩方案

### 4.1 Workspace Shell

**目标：** 让整个 Workspace 先具备“书架模式 / 创作模式 / 项目模式”三种清晰心智，而不是统一后台壳。

**路由 / 实现：**

- `apps/web/src/app/workspace/layout.tsx`
- `apps/web/src/features/workspace/components/workspace-shell.tsx`

**文档挂钩：**

- `docs/ui/README.md` 的 UI 主入口
- `docs/ui/frontend-page-component-style-map.md` 的页面与样式定位

**重构方向：**

- 收轻顶栏和导航噪音
- 保持当前 `pageMode` 结构，但强化不同模式下的视觉差异
- 让 Lobby 与 Studio 的壳层不再共用同一种后台语气

### 4.2 Lobby（书架）

**目标：** 把大厅明确收口为“作品入口”，而不是项目管理总览页。

**路由 / 实现：**

- `apps/web/src/app/workspace/lobby/page.tsx`
- `apps/web/src/features/lobby/components/projects/lobby-page.tsx`
- `apps/web/src/features/lobby/components/projects/lobby-project-shelf.tsx`
- `apps/web/src/features/lobby/components/projects/lobby-entry-card.tsx`

**文档挂钩：**

- `docs/ui/README.md` 的 UI 主入口
- `apps/web/UI-V2-README.md` 的 Lobby ASCII 草图

**重构方向：**

- 继续强化“书架 / 作品空间 / 继续创作”
- 把快速开始、模板、助手都围绕作品来组织
- 弱化“去设置页才能工作”的感觉

### 4.3 Incubator（项目起稿）

**目标：** 把起稿统一成创作者的启动舞台，而不是表单中心。

**路由 / 实现：**

- `apps/web/src/app/workspace/lobby/new/page.tsx`
- `apps/web/src/features/lobby/components/incubator/incubator-page.tsx`
- `apps/web/src/features/lobby/components/incubator/incubator-chat-panel.tsx`
- `apps/web/src/features/lobby/components/incubator/incubator-panels.tsx`
- `apps/web/src/features/lobby/components/incubator/incubator-page-model.ts`

**业务参考：**

- `apps/api/app/modules/project/service/project_incubator_service.py`

**文档挂钩：**

- `docs/ui/README.md` 的 UI 主入口
- `docs/design/06-creative-setup.md`
- `docs/design/19-pre-writing-assets.md`
- `apps/web/UI-V2-README.md` 的 Incubator ASCII 草图

**重构方向：**

- 对话起稿与模板起稿共用同一舞台，不拆成后台切页
- “先聊，再整理成项目草稿”的心智保持在页面一层
- 把反馈、草稿、创建项目动作全部收在创作语义里

### 4.4 Studio（创作桌面）

**目标：** 让 Studio 彻底像写作桌面，而不是三块功能区拼接的项目页。

**路由 / 实现：**

- `apps/web/src/app/workspace/project/[projectId]/studio/page.tsx`
- `apps/web/src/features/studio/components/page/studio-page.tsx`
- `apps/web/src/features/studio/components/tree/document-tree.tsx`
- `apps/web/src/features/studio/components/document/markdown-document-editor.tsx`
- `apps/web/src/features/studio/components/chat/ai-chat-panel.tsx`
- `apps/web/src/features/studio/components/chat/studio-chat-composer.tsx`

**业务参考：**

- `apps/web/src/features/studio/components/page/studio-page-support.ts`

**文档挂钩：**

- `docs/ui/README.md` 的 UI 主入口
- `docs/design/05-content-editor.md`
- `docs/design/02-context-injection.md`
- `docs/design/04-chapter-generation.md`
- `docs/design/19-pre-writing-assets.md`
- `apps/web/UI-V2-README.md` 的 Studio ASCII 草图

**重构方向：**

- 左栏明确是资料树，不是配置树
- 中栏正文是主舞台
- 右栏助手是共创侧板，不是控制台
- 模型、上下文、上传、发送等能力继续贴近输入区，而不是回到顶部控制条

### 4.5 Engine（推进）

**目标：** 把 Engine 从 workflow 控制感收口为“作品推进室”。

**路由 / 实现：**

- `apps/web/src/app/workspace/project/[projectId]/engine/page.tsx`
- `apps/web/src/features/engine/components/engine-page.tsx`
- `apps/web/src/features/engine/components/engine-page-shell.tsx`
- `apps/web/src/features/engine/components/engine-detail-panel.tsx`

**文档挂钩：**

- `docs/ui/README.md` 的 UI 主入口
- `docs/design/01-core-workflow.md`
- `docs/design/03-review-and-fix.md`
- `docs/design/08-cost-and-safety.md`
- `docs/design/11-export.md`
- `docs/design/12-streaming-and-interrupt.md`

**重构方向：**

- 页面入口优先表达“推进状态、下一步动作、卡点”
- 复杂的 workflow 细节保留下钻，不做默认主视图
- 让导出、日志、审核、回放都围绕创作推进来组织

### 4.6 Lab（洞察）

**目标：** 把 Lab 固定成围绕作品的研究桌，而不是分析记录后台。

**路由 / 实现：**

- `apps/web/src/app/workspace/project/[projectId]/lab/page.tsx`
- `apps/web/src/features/lab/components/lab-page.tsx`
- `apps/web/src/features/lab/components/lab-sidebar.tsx`
- `apps/web/src/features/lab/components/lab-detail-panel.tsx`
- `apps/web/src/features/lab/components/lab-create-panel.tsx`

**文档挂钩：**

- `docs/ui/README.md` 的 UI 主入口
- `docs/design/07-novel-analysis.md`
- `docs/design/13-ai-preference-learning.md`
- `docs/design/14-foreshadowing-tracking.md`

**重构方向：**

- 左侧筛选、中间详情、右侧创建的结构可以保留
- 重点改标题、说明、结果表达和视觉密度
- 让“对作品有什么帮助”成为第一层信息

### 4.7 Project Settings / Lobby Settings

**目标：** 保留设置闭环，但降到次级区域，不反向污染主创作路径。

**路由 / 实现：**

- `apps/web/src/app/workspace/project/[projectId]/settings/page.tsx`
- `apps/web/src/features/project-settings/components/project-settings-page.tsx`
- `apps/web/src/app/workspace/lobby/settings/page.tsx`
- `apps/web/src/features/lobby/components/settings/lobby-settings-page.tsx`
- `apps/web/src/features/settings/components/**`

**文档挂钩：**

- `docs/ui/README.md` 中的当前 UI 文档入口与边界说明
- `docs/plans/2026-03-28-multi-user-assistant-rules-phase1.md`
- `docs/design/10-user-and-credentials.md`

**重构方向：**

- 设置页继续存在，但不作为主用户路径心智
- 优先收口“我如何继续写”相关入口
- 高级 AI 能力与控制面能力继续放次级区域

### 4.8 Template Library / Recycle Bin / Config Registry

**目标：** 让这些页面成为 Lobby 的辅助空间，而不是产品视觉中心。

**路由 / 实现：**

- `apps/web/src/app/workspace/lobby/templates/page.tsx`
- `apps/web/src/features/lobby/components/templates/template-library-page.tsx`
- `apps/web/src/app/workspace/lobby/recycle-bin/page.tsx`
- `apps/web/src/features/lobby/components/recycle-bin/recycle-bin-page.tsx`
- `apps/web/src/app/workspace/lobby/config-registry/page.tsx`
- `apps/web/src/features/config-registry/components/config-registry-page.tsx`

**文档挂钩：**

- `docs/ui/README.md` 的当前 UI 文档入口与导航边界
- `docs/design/18-data-backup.md`
- `docs/specs/config-format.md`

**重构方向：**

- 模板库和回收站仍然服务作品主链
- Config Registry 继续保留，但彻底退出一线创作路径
- 从视觉和导航上明确它们是辅助空间，不是主舞台

---

## 5. 阶段顺序

### Phase 0: 壳层与公共基线

**目标：** 统一主路径语义、样式真值和共享 UI 外壳。

**重点：**

- `WorkspaceShell`
- `globals.css`
- `tailwind.config.ts`
- `src/components/ui/**`

### Phase 1: 创作入口路径

**目标：** 先让用户从进入系统到开始写作这一段流畅统一。

**重点：**

- `Lobby`
- `Incubator`
- `Template Library`
- `Recycle Bin`

### Phase 2: 创作主舞台

**目标：** 让正文编辑、结构树和 AI 助手真正形成一个创作桌面。

**重点：**

- `Studio`
- `DocumentTree`
- `MarkdownDocumentEditor`
- `AiChatPanel`

### Phase 3: 推进与洞察

**目标：** 让创作后的批量推进和洞察分析保持同一产品语气。

**重点：**

- `Engine`
- `Lab`

### Phase 4: 设置与高级能力收口

**目标：** 保持高级能力可达，但不让它们主导产品心智。

**重点：**

- `Project Settings`
- `Lobby Settings`
- `Config Registry`

---

## 6. 参考清单

### 6.1 UI 设计参考

- `docs/ui/README.md`
- `docs/ui/frontend-page-component-style-map.md`
- `apps/web/UI-V2-README.md`

### 6.2 业务设计参考

- `docs/design/05-content-editor.md`
- `docs/design/06-creative-setup.md`
- `docs/design/07-novel-analysis.md`
- `docs/design/01-core-workflow.md`
- `docs/design/02-context-injection.md`
- `docs/design/03-review-and-fix.md`
- `docs/design/04-chapter-generation.md`
- `docs/design/11-export.md`
- `docs/design/12-streaming-and-interrupt.md`
- `docs/design/18-data-backup.md`
- `docs/design/19-pre-writing-assets.md`

### 6.3 关键源码参考

- `apps/web/src/features/workspace/components/workspace-shell.tsx`
- `apps/web/src/features/lobby/components/projects/lobby-page.tsx`
- `apps/web/src/features/lobby/components/incubator/incubator-page.tsx`
- `apps/web/src/features/studio/components/page/studio-page.tsx`
- `apps/web/src/features/engine/components/engine-page.tsx`
- `apps/web/src/features/lab/components/lab-page.tsx`
- `apps/web/src/features/project-settings/components/project-settings-page.tsx`
- `apps/web/src/features/config-registry/components/config-registry-page.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/tailwind.config.ts`

---

## 7. 完成标准

- 主路径页面都能对上同一套 creator-first 产品语义
- 页面壳层、共享 UI 和样式真值不再分裂成多套口径
- 高级设置与控制面退出主路径中心
- 计划中的每个页面都能找到对应的路由入口、feature 实现文件和设计参考文档
