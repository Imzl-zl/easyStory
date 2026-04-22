# easyStory 前端 UI 审计测试文档

> 审计范围：`apps/web` 全部 14 个页面路由、143 个组件、4 个 Zustand Store
> 技术栈：Next.js 16 (App Router) + React 19 + Arco Design + Tailwind CSS 4
> 设计语言：Ink（自建，基于 CSS 变量体系）
> 账号密码：zhanglu 12345678
> 审计日期：2026-04-12
> 更新日期：2026-04-22（基于源码全面审计，对齐重构后的代码）
---

## 一、设计体系概览

### 1.1 Design Token 体系

| 分组 | 变量前缀 | 层级数 | 示例 |
|------|----------|--------|------|
| 背景 | `--bg-*` | 9 级 | canvas / surface / surface-hover / surface-active / muted / elevated / glass / glass-heavy / code |
| 边框 | `--line-*` | 4 级 | soft / strong / focus / glass |
| 文字 | `--text-*` | 6 级 | primary / secondary / tertiary / placeholder / on-accent / code |
| 强调 | `--accent-*` | 20 个 | primary / primary-hover / primary-soft / primary-muted / primary-dark / secondary / tertiary / success / success-soft / warning / warning-soft / danger / danger-soft / danger-active / purple / pink / ink / info / info-soft / info-muted |
| 阴影 | `--shadow-*` | 9 级 | xs / sm / md / lg / hero / glass / glass-heavy / float / panel-side |
| 圆角 | `--radius-*` | 10 级 | xs ~ 5xl + pill |
| 模糊 | `--blur-*` | 4 级 | sm / md / lg / xl |
| 字体 | `--font-*` | 3 族 | serif / sans / mono |
| 过渡 | `--transition-*` | 5 种 | fast / normal / slow / spring / smooth |
| 层级 | `--z-*` | 7 级 | base / surface / elevated / sticky / overlay / modal / toast |
| 下拉 | `--dropdown-*` | 3 个 | bg / border / shadow |
| 遮罩 | `--overlay-bg` | 1 个 | overlay-bg |
| Callout | `--callout-*` | 8 个 | info-bg / info-border / warning-bg / warning-border / success-bg / success-border / danger-bg / danger-border |
| Toolbar | `--toolbar-*` | 6 个 | bg / bg-hover / bg-active / border / text / text-active |
| Chat | `--chat-*` | 4 个 | user-bubble-bg / assistant-bubble-bg / skill-panel-bg / skill-option-active-bg |
| 渐变 | `--*gradient*` | 7 个 | auth-bg-gradient / workspace-shell-accent-gradient / bg-surface-warm-gradient / bg-panel-warm-gradient / bg-engine-page-gradient / bg-getting-started-gradient / bg-config-file-gradient |

### 1.2 CSS 组件类

| 类名 | 类型 | 语义 |
|------|------|------|
| `panel-shell` | 容器 | 白底卡片面板，hover 阴影增强 |
| `panel-muted` | 容器 | 灰底面板 |
| `panel-glass` | 容器 | 毛玻璃面板，backdrop-blur |
| `hero-card` | 容器 | 英雄卡片，大圆角 + 毛玻璃 + hero 阴影 |
| `section-card` / `__header` / `__copy` / `__body` | 容器 | 分节卡片（含 3 个 BEM 子元素类） |
| `ink-button` | 按钮 | 主按钮，暖棕底白字，pill 圆角，光泽渐变 |
| `ink-button-secondary` | 按钮 | 次按钮，白底 + 边框 + 毛玻璃 |
| `ink-button-danger` | 按钮 | 危险按钮，红边框透明底，hover 红底白字 |
| `ink-button-hero` | 按钮 | 英雄按钮，渐变底 + 更大尺寸 + hover 上浮 |
| `ink-tab` | 按钮/标签 | 标签按钮，`data-active="true"` 激活态 |
| `ink-icon-button` | 按钮 | 图标按钮，32×32 方形 |
| `ink-pill` | 按钮/标签 | 药丸标签，`data-active="true"` 激活态 |
| `ink-link-button` | 按钮 | 链接风格按钮 |
| `ink-toolbar-icon` | 按钮 | 工具栏图标按钮，30×30 |
| `ink-toolbar-chip` | 按钮/标签 | 工具栏 Chip，`data-active="true"` 激活态，`data-compact="true"` 紧凑变体 |
| `ink-toolbar-toggle` | 按钮/标签 | 工具栏 Toggle，`aria-pressed="true"` 激活态，`data-compact="true"` 紧凑变体 |
| `ink-input` | 输入框 | 标准输入框 |
| `ink-input-roomy` | 输入框 | 宽松输入框，更大高度 + 毛玻璃背景 |
| `ink-textarea` | 输入框 | 文本域 |
| `badge` | 徽章 | 通用徽章，`badge--warning/success/danger` 变体 |
| `callout-info` | 横幅 | 信息横幅 |
| `callout-warning` | 横幅 | 警告横幅 |
| `callout-success` | 横幅 | 成功横幅 |
| `callout-danger` | 横幅 | 危险横幅 |
| `divider` | 分隔 | 水平分割线，`divider--vertical` 竖直变体 |
| `mono-block` | 展示 | 等宽代码块，深色背景 |
| `label-text` | 文字 | 表单标签文字 |
| `label-overline` | 文字 | 大写小号标签 |
| `fade-in` | 动画 | 淡入动画 |
| `slide-up` | 动画 | 上滑动画 |
| `scrollbar-hide` | 工具 | 隐藏滚动条 |

### 1.3 Arco Design 覆写范围

通过 `globals.css` 覆写了以下 Arco 组件样式，统一到 Ink 设计语言：

Button、Link、Input、Textarea、Select、Dropdown、Tag、Checkbox、Radio、Notification、Modal、Tabs、Switch、Slider、Tooltip、Popover、Drawer、Table、Card、Message、Picker、Spin、Pagination、Breadcrumb、Divider、Collapse、Steps、Badge、Avatar、Progress

---

## 二、页面路由与流转

### 2.1 完整路由表

| # | 路由路径 | 页面名称 | 页面模式 |
|---|----------|----------|----------|
| 1 | `/` | 首页（重定向） | — |
| 2 | `/auth/login` | 登录 | auth |
| 3 | `/auth/register` | 注册 | auth |
| 4 | `/workspace/lobby` | 书架/项目列表 | lobby |
| 5 | `/workspace/lobby/new` | 新建作品（孵化器） | lobby |
| 6 | `/workspace/lobby/templates` | 模板库 | lobby |
| 7 | `/workspace/lobby/templates/:id` | 模板详情 | lobby |
| 8 | `/workspace/lobby/config-registry` | 配置注册中心 | lobby |
| 9 | `/workspace/lobby/recycle-bin` | 回收站 | lobby |
| 10 | `/workspace/lobby/settings` | 大厅设置 | lobby |
| 11 | `/workspace/project/:id/studio` | 创作工作台 | studio |
| 12 | `/workspace/project/:id/engine` | 作品推进 | project |
| 13 | `/workspace/project/:id/lab` | 作品洞察 | project |
| 14 | `/workspace/project/:id/settings` | 项目设置 | project |

### 2.2 页面流转图

```
/ (重定向)
  └─→ /auth/login
        ├─→ /auth/register（模式切换链接）
        └─→ /workspace/lobby（登录成功）
              ├─→ /workspace/lobby/new（新建作品）
              │     └─→ /workspace/project/:id/studio（创建成功）
              ├─→ /workspace/lobby/templates（模板库）
              ├─→ /workspace/lobby/config-registry（配置注册中心）
              ├─→ /workspace/lobby/recycle-bin（回收站）
              ├─→ /workspace/lobby/settings（大厅设置）
              └─→ /workspace/project/:id/studio（继续创作）
                    ├─→ /workspace/project/:id/engine（作品推进）
                    ├─→ /workspace/project/:id/lab（作品洞察）
                    └─→ /workspace/project/:id/settings（项目设置）
```

### 2.3 导航栏模式

| 模式 | Header 样式 | 内容区布局 | 适用页面 |
|------|-------------|-----------|----------|
| auth | 无导航栏 | 全屏居中 | 登录、注册 |
| lobby | 品牌标识 + 4 项导航 + 用户操作 | 居中滚动，`w-[min(100%-2.5rem,1560px)] mx-auto` | 书架、孵化器、模板库等 |
| studio | 返回书架 + 项目标题 + 3 项导航 + 设置 | 全高固定 `h-[100dvh]`，无滚动 | 创作工作台 |
| project | 返回书架 + 项目标题 + 3 项导航 + 设置 | 居中滚动 | 推进、洞察、项目设置 |

### 2.4 Workspace Layout

所有 `/workspace/*` 页面共享 `app/workspace/layout.tsx` 布局：

| 属性 | 值 |
|------|-----|
| Arco CSS | 导入 `@arco-design/web-react/dist/css/arco.css`（全局 Arco 样式） |
| 外壳 | `<WorkspaceShell>` 包裹 `children` |
| 渲染模式 | Server Component（无 `"use client"`） |

`WorkspaceShell` 提供统一的 Header（品牌标识/返回书架 + 导航 + 用户操作）和页面结构框架。包含跳到主内容链接（`href="#workspace-main"`）无障碍特性。壳层 div 有 `data-page-mode` 属性标记当前模式。

---

## 三、逐页面 UI 审计

### 3.1 登录页 `/auth/login`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | `min-h-screen flex items-center justify-center p-6 lg:p-8`，`[background:var(--auth-bg-gradient)]` |
| 双栏 Grid | `grid gap-6 w-full max-w-[1240px] mx-auto [grid-template-columns:1fr] lg:[grid-template-columns:minmax(0,1.15fr)_minmax(360px,460px)] lg:items-center` |
| 左栏 Hero | `hero-card`，仅大屏可见 `max-lg:hidden`，含品牌区（ES logo + 标语）、创作步骤列表（`CREATION_STEPS`）、产品要点列表（`PRODUCT_PILLARS`）、装饰性圆形 `bg-accent-soft` |
| 右栏表单 | `hero-card`，`max-w-[460px] p-8` |

#### 交互元素

| 元素 | 样式 | 验证点 |
|------|------|--------|
| 用户名输入 | `ink-input ink-input-roomy`，必填，minLength=3，maxLength=100 | 空值/过短/过长提示 |
| 邮箱输入 | `ink-input ink-input-roomy`，仅注册模式，可选 | — |
| 密码输入 | `ink-input ink-input-roomy`，type=password，必填，minLength=8，maxLength=200 | 空值/过短提示 |
| 提交按钮 | `ink-button-hero w-full`，文案"进入书架" | pending 态"处理中..."，disabled |
| 模式切换 | 底部 Link，"还没有账号？创建账号" | 点击跳转 `/auth/register` |

#### 内部组件

| 组件 | 功能 |
|------|------|
| `AuthHero` | 左栏品牌展示区，含 CREATION_STEPS 和 PRODUCT_PILLARS 列表 |
| `AuthPanel` | 右栏表单区 |
| `Field` | 统一输入框组件，`ink-input ink-input-roomy` 样式 |
| `ErrorNotice` | 错误提示组件，`bg-accent-danger/10 text-accent-danger` |
| `AuthLoading` | Suspense fallback，`panel-shell` 样式 |
| `buildAuthCopy` | 根据 mode 返回文案对象，统一管理登录/注册文案 |

#### 状态

| 状态 | 表现 |
|------|------|
| 错误 | ErrorNotice，`bg-accent-danger/10 text-accent-danger` |
| 加载 | 按钮 disabled + 文案"处理中..." |
| Suspense | `<Suspense fallback={<AuthLoading />}>` 包裹 AuthForm |

#### UX 审计项

- [ ] 左栏 Hero 在移动端隐藏，表单是否正常居中
- [ ] 密码输入是否支持显示/隐藏切换
- [ ] 表单提交后 Enter 键是否正常触发
- [ ] 登录成功后是否正确重定向到 `next` 参数或 `/workspace/lobby`
- [ ] 错误信息是否清晰可读，是否有足够的对比度
- [ ] 注册模式切换后表单是否正确重置

---

### 3.2 注册页 `/auth/register`

布局与登录页共享 `AuthForm` 组件，差异点：

| 差异 | 登录模式 | 注册模式 |
|------|----------|----------|
| 邮箱字段 | 隐藏 | 显示，可选 |
| 提交按钮文案 | "进入书架" | "创建并进入" |
| 底部链接 | "还没有账号？创建账号" | "已经有账号？返回登录" |
| autoComplete | username / current-password | username / new-password |
| Suspense 包裹 | 有 `<Suspense>` | **无** `<Suspense>`（与登录页不一致） |

#### UX 审计项

- [ ] 注册成功后是否自动登录并跳转
- [ ] 邮箱字段可选，不填是否可正常提交
- [ ] 注册页是否需要添加 Suspense 包裹（与登录页保持一致）

---

### 3.3 书架页 `/workspace/lobby`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | 双栏 Grid `-mt-4 grid min-h-[calc(100vh-72px)] [grid-template-columns:1fr] lg:[grid-template-columns:240px_minmax(0,1fr)] gap-5 lg:gap-7 items-start` |
| 侧边栏 | `lg:sticky top-[5.5rem] flex flex-col gap-1 p-3 lg:p-4 max-lg:order-2 rounded-2xl border border-line-soft/60 bg-[var(--bg-glass-heavy)] backdrop-blur-sm` |
| 主内容 | `grid gap-5 min-w-0 max-lg:order-1` |

#### 侧边栏

| 元素 | 样式 | 验证点 |
|------|------|--------|
| 导航链接 ×4 | `p-2.5 pl-3`，active 有左侧 `before:` 伪元素竖条 + `bg-accent-soft` | "我的作品"/"我的助手"/"模板库"/"回收站" |
| 导航区 | `flex flex-row lg:flex-col gap-1 overflow-x-auto scrollbar-hide` | 移动端水平滚动 |
| "打开我的助手" | `rounded-2xl border border-dashed border-border`，位于侧栏底部 `max-lg:hidden` | 链接到 settings |
| "新建作品" | `ink-button whitespace-nowrap max-lg:w-full max-lg:text-center` | 链接到 `/workspace/lobby/new` |
| 当前节奏 | 侧栏底部一行小字，有模板时显示 `当前节奏：模板名` | — |

#### 主内容区

| 元素 | 样式 | 验证点 |
|------|------|--------|
| 搜索行 | `flex flex-wrap gap-3 items-center max-lg:flex-col max-lg:stretch` | 搜索框前置为第一个元素 |
| 搜索框 | `ink-input-roomy min-h-12 flex-1 max-lg:w-full text-[0.95rem]` | 实时过滤，使用 `useDeferredValue` |
| 统计文字 | `text-text-tertiary text-[0.84rem]` | 替代了原 MetricCard |
| "新建作品"按钮 | `ink-button whitespace-nowrap max-lg:w-full max-lg:text-center` | 与搜索框同行 |
| 项目卡片网格 | `LobbyProjectShelf` 组件 | 响应式列数 |

#### LobbyProjectCard

| 区域 | 样式 |
|------|------|
| 整体 | `rounded-5xl` 大圆角卡片，含首字母头像 + accent 渐变条 |
| 色调 | `PROJECT_CARD_TONES` 5 色调数组，按 projectId 哈希分配 |
| 顶部 | 项目首字大号 + 题材标签 + 设置齿轮图标 |
| 中部内容 | StatusBadge + 字数标签 + 项目名 + 描述 + 元信息 |
| 底部操作栏 | 更新时间 + "继续创作"(`ink-button`) + "删除"(`ink-button-danger`) |

#### 状态

| 状态 | 表现 |
|------|------|
| 空状态 | `rounded-5xl bg-muted`，文件夹图标 + "还没有作品" |
| 加载 | `py-10 px-4 text-center`，"正在加载项目列表…" |
| 错误 | `callout-danger` |

#### 与旧文档差异

| 项目 | 旧文档 | 当前代码 |
|------|--------|---------|
| `LobbyEntryCard` | 存在 | **已删除**，替换为更丰富的 `LobbyProjectCard` |
| MetricCard 统计区 | 3 个 MetricCard | **已替换**为一行统计文字 |
| 品牌标题区 | "继续创作" + 大标题 | **已删除**，搜索框前置 |
| 侧栏宽度 | 272px | **缩减**为 240px |
| "打开我的助手"位置 | 侧栏中部 | **移入**侧栏底部 |
| 搜索框位置 | 主内容区中部 | **前置**为第一个元素 |
| `RecycleBinDeleteDialog` | 未提及在书架页使用 | 已在 `LobbyProjectCard` 中集成 |

#### UX 审计项

- [ ] 侧边栏在窄屏下是否正常显示或折叠
- [ ] 搜索输入是否实时过滤，是否有防抖（已使用 useDeferredValue）
- [ ] 项目卡片 hover 动画是否流畅
- [ ] "删除"操作是否需要确认（当前无确认弹窗）
- [ ] StatusBadge 各状态颜色是否语义清晰
- [ ] 项目卡片网格在窄屏下是否单列排列
- [ ] 当前节奏提示内容是否与用户行为相关

---

### 3.4 新建作品页 `/workspace/lobby/new`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | `flex h-full min-h-0 flex-col gap-2.5 overflow-y-auto lg:overflow-hidden` |
| Hero | `hero-card`，`px-4 py-3 md:px-5 md:py-3.5 gap-3` |
| StageShell | `hero-card flex min-h-0 flex-1 overflow-hidden`，内层 `bg-glass backdrop-blur-sm p-2.5 md:p-3.5` |

#### 模式切换 ModeSwitch

| 元素 | 样式 |
|------|------|
| 容器 | `role="tablist"`，`rounded-2xl px-3 py-2 text-[12px]` |
| Tab 按钮 | "AI 聊天" / "模板创建"，active 态 `bg-surface shadow-sm` |
| 面板 | `role="tabpanel"` |
| 当前模式标签 | `rounded-pill px-2.5 py-1`，动态切换 accent-soft / muted 样式 |

#### Chat 模式

| 元素 | 样式 |
|------|------|
| 双栏 Grid | `grid lg:grid-cols-[minmax(312px,352px)_minmax(0,1fr)]` |
| 聊天输入 | ArcoDesign `Input.TextArea`，`autoSize minRows=2 maxRows=5` |
| 发送按钮 | `ink-button` |
| 草稿面板 | `IncubatorChatDraftPanel`，右侧 |
| 高级设置面板 | 浮动面板，`preferredWidth: 576`，`maxHeight: 640` |
| 历史面板 | 浮动面板，`preferredWidth: 384`，`maxHeight: 320` |

#### Template 模式

| 元素 | 样式 |
|------|------|
| 双栏 Grid | `grid xl:grid-cols-[0.84fr_1.16fr]` |
| 控制卡 + 问题卡 | 左栏 |
| 预览面板 | 右栏 `IncubatorPreview` |

#### 状态

| 状态 | 表现 |
|------|------|
| 空状态 | EmptyState，"当前没有模板"，带"使用 AI 聊天"按钮 |
| 加载 | "正在准备" pill / "正在加载模板列表…" |
| 错误 | RequestStateCard，带重试按钮；FeedbackBanner danger/info |
| 反馈横幅 | `FeedbackBanner`，`rounded-2xl px-4 py-2.5`，支持 info/danger 两种 tone |

#### 与旧文档差异

| 项目 | 旧文档 | 当前代码 |
|------|--------|---------|
| 子组件名 | `IncubatorChatPanel` | **已重命名**为 `ChatModePanel` |
| `ModeSwitch` | 未提及 | **新增**模式切换组件 |
| `FeedbackBanner` | 未提及 | **新增**全局反馈横幅 |
| `StageShell` | 未提及 | **新增**内容区壳层 |
| 模板模式懒加载 | 未提及 | `hasVisitedTemplateMode` 控制首次切换才渲染 |
| `IncubatorChatDraftPanel` | 未提及 | **新增**聊天模式右侧草稿面板 |

#### UX 审计项

- [ ] 模式切换是否流畅，状态是否正确重置
- [ ] 聊天输入 Enter 发送 / Shift+Enter 换行是否正常
- [ ] IME 输入法兼容：中文输入时是否避免误触发送
- [ ] 聊天记录是否自动滚动到底部
- [ ] 高级设置浮动面板定位是否准确，是否溢出视口
- [ ] 历史面板浮动定位是否准确
- [ ] 模板面板懒渲染，首次切换是否有延迟
- [ ] 创建成功后是否正确跳转到 Studio 页面

---

### 3.5 模板库页 `/workspace/lobby/templates`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | SectionCard 包裹 |
| 三栏 Grid | `grid xl:grid-cols-[260px_minmax(0,1fr)_340px] 2xl:grid-cols-[280px_minmax(0,1fr)_360px]` |
| 大屏全高 | `h-[calc(100vh-3rem)]`，`overflow-hidden` |

#### 侧边栏

| 元素 | 样式 |
|------|------|
| 搜索框 | `ink-input`，placeholder "按名称、描述、题材过滤" |
| VisibilityTabs | `ink-tab`，"全部"/"内置"/"自定义" |
| GenreTabs | `ink-tab`，"全题材" + 动态题材列表 |
| AppSelect | 排序下拉（名称 A-Z / Z-A） |
| 模板卡片 | `panel-muted`，含名称、描述、StatusBadge、题材/步数 |

#### 详情面板

| 元素 | 样式 |
|------|------|
| 容器 | `panel-shell fan-panel` |
| MetaGrid | 6 格元数据网格 `md:grid-cols-2`，每格 `panel-muted p-4` |
| CodeBlock | YAML/JSON 配置展示 |
| 操作按钮 | "创建副本"/"编辑"/"删除模板" |

#### 编辑器面板

| 元素 | 样式 |
|------|------|
| 容器 | `panel-shell` |
| 表单字段 | 模板名称/题材/使用流程 `ink-input`，说明 `ink-textarea rows=4` |
| 引导问题 | `ink-textarea rows=3` + 变量名 `ink-input` |
| 操作按钮 | "保存" `ink-button` / "清空表单" `ink-button-secondary` |

> **模板详情路由说明**：`/workspace/lobby/templates/[templateId]` 是独立动态路由，但渲染的是同一个 `TemplateLibraryPage` 组件（传入 `initialTemplateId`）。选择模板时 URL 通过 `router.push` 同步更新，删除后回退到列表 URL。该路由标记为 `force-dynamic`（不静态缓存）。

#### UX 审计项

- [ ] 模板详情 URL 是否正确同步（选中→URL 更新，直接访问→预选模板）
- [ ] 三栏布局在窄屏下是否合理降级
- [ ] VisibilityTabs 和 GenreTabs 是否支持 toggle（点击已选中则取消）
- [ ] 搜索过滤是否有防抖
- [ ] 模板卡片选中态是否明显
- [ ] 编辑器表单校验错误是否阻止提交
- [ ] 引导问题变量名 blur 时是否自动规范化
- [ ] 删除模板是否有确认机制
- [ ] 保存反馈是否清晰（成功/失败）

---

### 3.6 配置注册中心 `/workspace/lobby/config-registry`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | SectionCard 包裹 |
| 响应式多栏 | `grid xl:grid-cols-[320px_minmax(0,1fr)] min-[1900px]:grid-cols-[320px_minmax(0,1fr)_480px]` |
| 侧边栏 | sticky `top-6` |

#### 侧边栏

| 元素 | 样式 |
|------|------|
| 分类 Tab | `ink-tab`，Skills / Agents / Hooks / MCP / Workflows |
| 搜索框 | `ink-input`，placeholder "搜索名称或编号…" |
| AppSelect | 排序下拉 |
| 标签过滤 Tab | `ink-tab`，动态标签列表，toggle 行为 |
| 状态过滤 Tab | `ink-tab`，"全部"/"已启用"/"已停用" |
| 配置项卡片 | `rounded-3xl bg-muted shadow-sm p-4`，active 态 `border-accent-primary-muted bg-accent-soft ring-1` |

#### 横幅

| 类型 | 样式 |
|------|------|
| info | `callout-info` |
| danger | `bg-accent-danger/10` |
| muted | `panel-muted` |

#### UX 审计项

- [ ] 分类 Tab 切换是否正确过滤列表
- [ ] 标签过滤 toggle 行为是否正确（点击已选中则取消）
- [ ] 状态过滤是否单选行为
- [ ] 搜索是否使用 deferredValue 优化
- [ ] 编辑器面板 dirty 检测是否仅在数据加载后生效
- [ ] UnsavedChangesDialog 是否在切换分类/标签时正确触发
- [ ] GuardedLink 导航守卫是否正常工作
- [ ] 权限错误提示是否友好
- [ ] 反馈横幅 `aria-live` 是否正确设置

---

### 3.7 回收站 `/workspace/lobby/recycle-bin`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | SectionCard 包裹，`space-y-5` |
| 摘要卡 | `RecycleBinSummaryCard`，显示已删除项目数和保留说明 |
| 项目列表 | 复用 LobbyProjectShelf（deletedOnly 模式） |

#### 交互元素

| 元素 | 样式 |
|------|------|
| "返回书架" | `ink-button-secondary` Link |
| "清空回收站" | `ink-button-danger`，项目数为 0 时 disabled |
| 搜索框 | `ink-input`，placeholder "按项目名过滤" |
| "恢复" | `ink-button` |
| "彻底删除" | `ink-button-danger` |

#### 确认对话框

| 对话框 | 触发 | 内容 |
|--------|------|------|
| RecycleBinClearDialog | 点击"清空回收站" | 批量清理警告 + 项目数量 + "确认清空"/"先保留" |
| RecycleBinDeleteDialog | 点击"彻底删除" | 项目名 + 删除时间 + 保留截止 + 关联数据清理说明 + "确认彻底删除"/"先保留" |

#### UX 审计项

- [ ] "清空回收站"按钮在空回收站时是否 disabled
- [ ] 彻底删除弹窗是否明确提示不可恢复
- [ ] 关联数据清理说明是否完整
- [ ] 确认按钮 pending 态文案是否切换（"清空中..."/"删除中..."）
- [ ] 恢复操作是否有成功反馈
- [ ] 搜索过滤是否正常工作

---

### 3.8 大厅设置 `/workspace/lobby/settings`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | 双栏 Grid `grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]` |
| 侧边栏 | SectionCard 包裹，`xl:sticky xl:top-6 xl:self-start`，`bg-glass shadow-glass backdrop-blur-lg` |
| 内容区 | 根据 tab 条件渲染 |

#### 侧边栏导航

| 分组 | Tab 项 | 描述 |
|------|--------|------|
| 主路径 | AI 助手 / Skills / 模型连接 | 核心配置 |
| 高级能力 | Agents / Hooks / MCP | 高级配置 |

导航按钮样式：`rounded-2xl px-4 py-3.5 text-left transition-all duration-fast`，active 态 `bg-accent-soft shadow-sm`，inactive 态 `bg-surface shadow-xs hover:bg-surface-hover`

状态标签：`rounded-pill`，active 显示"当前"，inactive 显示"进入"

底部：`GuardedLink` "返回项目大厅" + 作用域提示面板 `panel-muted`（"这里只管理你自己的默认设置"）

#### 子面板

| 面板 | 功能 |
|------|------|
| LobbyAssistantSettingsPanel | AI 助手偏好和规则，含 Hero 区 + 双栏布局（主编辑区 + 辅助说明） |
| AssistantSkillsPanel | Skills 管理 |
| CredentialCenter | 模型凭证管理（含 ScopeTabs: 全局/当前项目；ModeTabs: 列表/审计日志） |
| AssistantAgentsPanel | Agents 管理 |
| AssistantHooksPanel | Hooks 管理（含 GuidedEditor/RawEditor/ModeEditors 三种模式） |
| AssistantMcpPanel | MCP 管理 |

#### Assistant 子面板详细组件

| 组件 | 功能 | 关键 UI 元素 |
|------|------|-------------|
| AssistantDocumentModeToggle | 编辑方式切换 | `ink-tab` 按钮组（可视化编辑/按文件编辑）+ 文件标签 pill |
| AssistantGettingStartedPanel | 入门引导 | 3 步 StepCard（规则/Skills/模型连接）+ 高阶能力标签组（Agents/Hooks/MCP pill） |
| AssistantConfigFileMapPanel | 配置文件映射 | 文件列表展示 |
| AssistantEditorPrimitives | 编辑器原语 | 通用编辑器 UI 基础组件 |
| AssistantPreferencesForm | 偏好表单 | Switch/Checkbox/Select 等表单控件 |
| AssistantRulesEditor | 规则编辑器 | 文本编辑区 |
| AssistantSkillEditor | Skill 编辑器 | 表单字段编辑 |
| AssistantAgentEditor | Agent 编辑器 | 含 GuidedEditor/RawEditor/ModeEditors 三种模式 |
| AssistantAgentHelperCards | Agent 辅助卡片 | 帮助信息卡片 |
| AssistantHookEditor | Hook 编辑器 | 含 GuidedEditor（含 GuidedSidebar）/RawEditor |

#### HookGuidedFormPanel — Hook 引导表单字段

| 属性 | 值 |
|------|-----|
| 根容器 | `space-y-4` |
| 信息横幅 | `rounded-2xl bg-[rgba(58,124,165,0.07)]`，提示性文案 |
| 通用字段 | 名称（maxLength 80）、描述（maxLength 240）、启用开关、事件选择、动作类型选择 |
| Agent 条件字段 | Agent 选择 + JSON input mapping（`validateAssistantHookStringMap` 校验） |
| MCP 条件字段 | MCP 选择 + 工具名称（maxLength 120）+ JSON arguments + JSON input mapping |
| 错误处理 | Agent/MCP 选择错误时显示 error tone |

#### CredentialDeleteConfirmDialog — 凭证删除确认

| 属性 | 值 |
|------|-----|
| 外壳 | `DialogShell`，标题 "确认删除{scopeLabel}"，描述 "删除后无法恢复，请确认影响范围。" |
| 布局 | 双栏 Grid `grid gap-4 xl:grid-cols-[0.96fr_1.04fr]` |
| 左面板 | `panel-muted space-y-4 p-5`：danger 警告 + 凭证信息卡 |
| Danger 警告 | `rounded-2xl border border-accent-danger/15 bg-accent-danger/10` |
| 凭证信息卡 | `rounded-2xl bg-glass shadow-glass`，显示 display_name/provider/api_dialect/is_active/masked_key |
| 右面板 | `panel-muted space-y-4 p-5`：删除影响项列表 |
| 影响项 | `article rounded-2xl bg-glass shadow-glass px-4 py-3` |
| 按钮 | "确认删除" `ink-button-danger` + "先保留" `ink-button-secondary` |

#### CredentialScopeTabs / CredentialModeTabs — 凭证中心标签

| 组件 | Tabs | 样式 | 行为 |
|------|------|------|------|
| CredentialScopeTabs | "全局连接"/"当前项目连接" | `ink-tab` + `data-active` | 单选，项目 Tab 无项目时 disabled |
| CredentialModeTabs | "连接列表"/"审计日志" | `ink-tab` + `data-active` | 单选 |
| AssistantMcpEditor | MCP 编辑器 | 含 RawEditor |

#### CredentialCenter 详细组件

| 组件 | 功能 | 关键 UI 元素 |
|------|------|-------------|
| CredentialCenterContent | 内容区容器 | 根据 Scope/Mode 切换内容 |
| CredentialCenterList | 凭证列表 | 凭证卡片列表 + 新增按钮 |
| CredentialCenterForm | 凭证表单 | 表单字段 + 保存/重置按钮 |
| CredentialCenterFormFields | 表单字段 | 通用字段（名称/类型/API 地址等） |
| CredentialCenterClientIdentityFields | 客户端身份字段 | Client ID/Secret 输入 |
| CredentialCenterTokenFields | Token 字段 | Token/Key 输入 |
| CredentialCenterCompatibilityPanel | 兼容性面板 | 模型兼容性检测 |
| CredentialAuditPanel | 审计面板 | 操作日志列表 |

#### UX 审计项

- [ ] 6 个 Tab 切换是否通过 URL search params 驱动
- [ ] 每个 Tab 独立 dirty 状态跟踪是否正确
- [ ] UnsavedChangesDialog 是否在切换 Tab 时正确触发
- [ ] GuardedLink "返回项目大厅" 是否带未保存变更守卫
- [ ] 侧边栏作用域提示 "这里只管理你自己的默认设置" 是否显示
- [ ] CredentialCenter 双层 Tab（Scope + Mode）是否正确联动
- [ ] Hook RawEditor YAML 校验是否正确

---

### 3.9 创作工作台 `/workspace/project/:id/studio`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | CSS Grid，全高 `h-full min-h-0`，无页面滚动 |
| 无聊天 | `grid [grid-template-columns:1fr] lg:[grid-template-columns:236px_minmax(0,1fr)] [grid-template-rows:auto_minmax(0,1fr)]` |
| 有聊天 | `grid [grid-template-columns:1fr] lg:[grid-template-columns:236px_minmax(0,1fr)_minmax(392px,0.72fr)] xl:[grid-template-columns:244px_minmax(0,1fr)_minmax(408px,0.76fr)] [grid-template-rows:auto_minmax(0,1fr)]` |
| 顶栏 | `bg-glass-heavy backdrop-blur-xl border-b border-line-soft`，底部渐变分隔线 `bg-gradient-to-r from-transparent via-accent-primary to-transparent opacity-20` |
| 左侧边栏 | 文稿目录树，`bg-glass-heavy backdrop-blur-md shadow-panel-side`，入场动画 `slideFromLeft` |
| 中间主内容 | 文稿编辑器，`bg-surface shadow-lg`，入场动画 `inkFadeIn` |
| 右侧边栏 | AI 聊天面板（条件渲染），`bg-glass-heavy backdrop-blur-md border-l border-line-soft shadow-panel-side`，入场动画 `slideFromRight` |
| 背景装饰 | `fixed -top-1/2 -right-[20%]` 径向渐变 |

#### 交互元素

| 元素 | 样式 | 说明 |
|------|------|------|
| 保存按钮 | `ink-button h-9 px-4 text-[13px] shadow-md`（有未保存）/ `ink-button-secondary`（已保存） | 动态文案（保存XX/XX已保存/保存中/载入中） |
| 收起/展开助手 | `ink-button-secondary h-9 px-4 text-[13px]` | 控制聊天面板显隐 |
| "作品推进" | `ink-button-secondary h-9 px-4 text-[13px]` | 导航到 Engine，带未保存变更守卫 |
| Stale 徽章 | `rounded-pill border border-accent-primary-muted bg-accent-soft text-[0.72rem] font-semibold tracking-[0.16em] uppercase text-accent-primary` | 显示待更新章节数 |
| 聊天面板宽度调整 | `role="separator"` | Pointer 拖拽 + 键盘方向键 |
| 目录树节点 | 点击选中/展开 | — |
| 右键菜单 | Arco Dropdown | 新建/重命名/删除 |

#### 浮动面板

| 面板 | 宽度 | 高度 | 定位 |
|------|------|------|------|
| Skill 面板 | `min(320, max(248, ...))` | `max(240, min(520, ...))` | 聊天侧栏内触发按钮下方 |
| 历史面板 | `minWidth: 300` | — | 触发按钮下方 |
| 模型选择器 | `preferredWidth: 352` | `maxHeight: 480` | align:right, side:top |
| 上下文选择器 | `preferredWidth: 352` | `maxHeight: 320` | align:left, side:top |

#### 对话框

| 对话框 | 触发 | 内容 |
|--------|------|------|
| UnsavedChangesDialog | 导航守卫 | "继续编辑" + "确认离开" |
| StudioDocumentTreeDialog | 新建/重命名/删除文稿 | Arco Modal + Input + 确认按钮 |

#### 文档编辑器子组件

Studio 中间主内容区根据文稿类型渲染不同编辑器：

| 编辑器 | 文稿类型 | 说明 |
|--------|----------|------|
| MarkdownDocumentEditor | Markdown 文档 | 支持编辑/分栏/预览三种视图，噪点纹理背景，渐变 header/footer，Ctrl/Cmd+S 保存 |
| JsonDocumentEditor | JSON 文档 | 支持编辑/分栏/预览，图预览模式读取同目录下人物/势力/关系 JSON 组合关系图 |
| StudioDocumentEditor | 总入口 | 根据 `isJsonStudioDocument` 分发到上述编辑器 |

#### ChapterImpactPanel — 章节影响面板

| 属性 | 值 |
|------|-----|
| 容器 | `panel-muted space-y-4 rounded-3xl p-4` |
| 状态标记 | StatusBadge，`stale` 或 `ready`，取决于 `has_impact` |
| 影响项卡片 | `article rounded-2xl bg-muted shadow-sm p-4`，显示目标标签 + 失效计数 + 影响说明 |
| 目标标签 | `{ chapter: "后续已确认章节" }` |
| 条件渲染 | `has_impact=true` 时才显示影响项列表 |

#### StoryAssetImpactPanel — 故事资产影响面板

| 属性 | 值 |
|------|-----|
| 容器 | 与 ChapterImpactPanel 相同结构 |
| 资产类型 | `outline` 或 `opening_plan` |
| 目标标签 | `{ opening_plan: "开篇设计", chapter: "已确认章节", chapter_tasks: "章节任务" }` |
| 描述文案 | 使用 `getStoryAssetLabel(assetType)` 生成 |

#### StudioChatComposer — 聊天输入组件

| 属性 | 值 |
|------|-----|
| Props | 26 个属性，涵盖文本、附件、凭证、模型选择、上下文等 |
| 布局模式 | `"default"` / `"compact"` / `"icon"`，compact 布局在非 default 模式下激活 |
| 模型选择器 | 浮动面板，含渠道下拉 + 模型名输入 + 推理控制区 + 回复显示方式 Radio.Group |
| 上下文选择器 | 浮动面板，align left，maxHeight 320，width 352 |
| 文件上传 | 隐藏 `<input type="file">`，通过 ref 触发，附件显示为可移除 chip |
| 发送触发 | Enter（非 Shift、非 IME composing）发送 |
| 点击外部关闭 | 监听外部点击关闭浮动面板（忽略 `.arco-trigger-popup`） |
| Reasoning 控制 | 三种模式：`gemini_budget` / `openai`（reasoningEffort）/ `anthropic` / `none` |
| 发送按钮 | `!canChat \|\| isResponding` 时 disabled |
| ARIA | `aria-expanded`（Provider 按钮）、`aria-label`（工具栏按钮）、`aria-pressed`（toggle）、`aria-label="回复显示方式"`（Radio.Group） |

内部子组件：

| 子组件 | 功能 |
|--------|------|
| ReasoningChipButton | Thinking budget 选项 toggle chip |
| ToolbarIconButton | `ink-toolbar-icon`，30×30px 图标按钮 |
| ToolbarChipButton | `ink-toolbar-chip`，Chip 样式 toggle，可选 badge 计数 |
| ToolbarToggleButton | `ink-toolbar-toggle`，Toggle 按钮，`aria-pressed` 状态 |
| ComposerIcon / SVG 图标组 | JumpLinkIcon、PaperclipIcon、ContextIcon、SparkIcon、WriteIcon，均 `aria-hidden` |

#### JsonRelationGraph — 关系图谱可视化

| 属性 | 值 |
|------|-----|
| 渲染引擎 | ECharts 力导向图，Canvas 渲染 |
| 节点类型 | character（圆形，青绿色 `#2f7d6d`）、faction（圆角矩形，琥珀色 `#b67d2d`） |
| 连线类型 | 人物关系（金色虚线）、势力关系（紫色虚线）、隶属（绿色实线） |
| 选中态 | 边框 3px + 阴影 16px + symbolSize 放大；非关联元素 opacity 0.35/0.18 |
| 交互 | 缩放 + 平移（roam）、点击选中/取消、悬停高亮相邻；不支持拖拽节点 |
| Tooltip | ECharts 原生，节点显示名称+类型标签，连线显示标签+起终点 |
| Inspector 面板 | 右上角浮动 `w-[min(360px,calc(100%-2rem))]`，渐变头+kind pill+标题+facts 网格+可折叠原始字段 |
| Hint 提示 | 底部居中浮动，毛玻璃背景，"点击节点或连线查看详情" |
| 统计芯片 | 圆角 pill，"人物 N"/"势力 N"/"人物关系 N" |

#### ChapterStaleNotice — 章节失效通知

| 属性 | 值 |
|------|-----|
| 容器 | `rounded-3xl`，琥珀色系边框 `rgba(183,121,31,0.24)` + 背景 `rgba(183,121,31,0.08)` |
| 内容 | 标题行 + StatusBadge(stale,"待复核") + 说明文字 + 跳转 Engine 按钮 |
| 按钮 | `ink-button-secondary`，动态文案，加载态"正在解析 workflow..." |

#### StudioStaleChapterPanel — 失效章节总览

| 属性 | 值 |
|------|-----|
| 容器 | `panel-muted rounded-3xl`，`space-y-4` |
| 内容 | 说明文字 + StatusBadge("N 章待复核") + "优先处理第 N 章"按钮 + Engine 跳转按钮 |

#### StudioChatMessageBubble — 聊天消息气泡

| 属性 | 值 |
|------|-----|
| 助手消息 | `mr-8 bg-accent-soft rounded-2xl`，fadeIn 动画 |
| 用户消息 | `ml-8 bg-glass rounded-2xl` |
| 错误消息 | 额外 `ring-1 ring-inset ring-accent-danger/10` |
| 角色标签 | 顶部小字 0.66rem，大写字母间距 |
| ToolProgress 卡片 | 竖向排列，标签+状态 badge+详情，4 种 tone（default/success/muted/danger） |
| Markdown 渲染 | 自定义轻量渲染器，支持 h1-h3/blockquote/加粗/斜体/行内代码/图片/链接/列表/代码块 |
| Markdown 文档识别 | 整段文档自动提取为独立卡片，头部"Markdown 文档"标签+复制按钮 |
| 附件 pill | 圆角 pill，灰色半透明背景，文件名+大小 |
| 操作按钮 | hover 时显示：复制/追加到文档/新建文档 |

#### UX 审计项

- [ ] 三栏布局在窄屏下是否合理降级
- [ ] 聊天面板拖拽调整宽度是否流畅
- [ ] 拖拽宽度是否持久化到 workspaceStore
- [ ] 键盘方向键调整宽度是否正常（ArrowLeft/Right/Home/End）
- [ ] 目录树右键菜单是否正确显示
- [ ] 新建/重命名/删除文稿弹窗是否正常工作
- [ ] 保存按钮文案是否根据状态正确切换
- [ ] 未保存变更守卫是否在导航时正确触发
- [ ] 聊天输入 IME 兼容性
- [ ] 浮动面板是否溢出视口
- [ ] Stale Badge 是否正确显示待整理章节数
- [ ] 无文稿选中时编辑器区域是否正确显示空态提示
- [ ] 目标文稿不存在时是否显示 warning toast
- [ ] JsonRelationGraph 缩放/平移是否流畅
- [ ] JsonRelationGraph 选中淡化效果是否正确
- [ ] JsonRelationGraph Inspector 面板定位是否正确
- [ ] JsonRelationGraph Tooltip 是否正确显示节点/连线信息
- [ ] ChapterStaleNotice 琥珀色警告是否与全局 accent-warning 色系协调
- [ ] StudioStaleChapterPanel "优先处理"按钮是否正确跳转到第一个 stale 章节
- [ ] 聊天消息气泡 hover 操作按钮是否在移动端可用
- [ ] Markdown 文档自动识别是否准确
- [ ] ToolProgress 卡片 4 种 tone 颜色是否语义清晰

---

### 3.10 作品推进 `/workspace/project/:id/engine`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | 单页滚动，`[background:var(--bg-engine-page-gradient)]` |
| Hero 区域 | `hero-card p-9`，装饰性绝对定位圆形 `bg-accent-soft` |
| Banner | 条件渲染，`flex flex-col gap-2 mt-4` |
| 双栏 Grid | `grid gap-6 max-w-[1240px] min-h-[calc(100vh-64px)] mx-auto mt-6 [grid-template-columns:minmax(0,1.15fr)_minmax(360px,460px)]` |

#### Hero 区域交互

| 元素 | 样式 |
|------|------|
| 批次 ID 输入 | `ink-input`，placeholder "粘贴执行批次 ID" |
| 主操作按钮 | `ink-button-hero`，动态文案（启动推进/继续推进/处理中...） |
| "载入批次" | `ink-button-secondary` |
| "导出成稿" | `ink-button-secondary`，条件启用 |
| "返回创作" | `ink-button-secondary` Link |

#### EnginePageShell — 页面外壳

| 属性 | 值 |
|------|-----|
| 背景 | CSS 变量 `--bg-engine-page-gradient` |
| Hero 区域 | `hero-card p-9`，标题区含装饰性圆形 `bg-accent-soft` |
| 左列 | 有 workflow：StatusCallout + SummaryCard + DebugPanel；无 workflow：PreparationStatusPanel + EmptyState |
| 右列 | `hero-card` 容器，标题"按视角查看这一轮推进" + 详情面板 |
| 危险操作按钮 | `border border-accent-danger/25 rounded-4 bg-accent-danger/5 text-accent-danger` |
| 禁用原因提示 | `text-text-tertiary text-xs` 文案 |

#### EngineTaskFormPanels — 任务表单面板

| 子组件 | 内容 |
|--------|------|
| EngineTaskEditorSection | 任务编辑器：StatusBadge 组 + 禁用原因提示 + 标题/摘要/角色/事件字段 + 保存/重置按钮 |
| EngineTaskRegenerateSection | 重建章节：载入/新建/追加按钮 + DraftRowEditor 卡片列表（每行含章节号+标题+摘要+角色+事件） |
| TaskField | 通用表单字段组件：`label-text` + `ink-input`/`ink-textarea` |

#### EngineContextStyleReferenceHelper — 风格参考辅助

| 属性 | 值 |
|------|-----|
| 容器 | `rounded-2xl bg-muted shadow-sm p-4` |
| 标题 | `<h3 className="font-serif text-lg font-semibold">` |
| 筛选 Grid | `grid gap-3 md:grid-cols-2`，`ink-input` + `label-text` |
| 数据查询 | `useQuery`，key `["engine-context-style-analyses", projectId, deferredGeneratedSkillKey]` |
| 自动选择 | 列表加载/变化时自动选中第一条 |
| 写入按钮 | `ink-button-secondary`，调用 `upsertStyleReferenceExtraInject` |
| 反馈 | 成功/失败 toast via `showAppNotice` |
| 空状态 | `EmptyState`，无分析结果时显示 |
| 内部子组件 | `SelectedAnalysisCard`（StatusBadge + skill key）、`FeedbackMessage`（danger 色错误提示） |

#### PreparationStatusPanel — 创作准备状态面板

| 属性 | 值 |
|------|-----|
| 容器 | InfoPanel `rounded-3xl`，标题"创作准备" |
| SummaryCard | InfoPanel tone="accent"，左侧"下一步"+描述，右侧 StatusBadge |
| PreparationRows | 竖向 InfoPanel 列表，每行左侧标签名，右侧 StatusBadge |
| 交互 | 纯展示，无交互元素 |

#### 详情面板

| 元素 | 样式 |
|------|------|
| Tab 按钮 ×7 | `ink-tab`，概览/章节任务/审核/账单/日志/上下文/回放 |
| 面板内容 | `p-6` |

#### 导出面板（DialogShell 模态）

| 元素 | 样式 |
|------|------|
| 格式选择 | `ink-tab` 样式 toggle 按钮，`aria-pressed` |
| 预检区 | 阻断项/警示项/备注分组 |
| "创建导出文件" | `ink-button`，带 pending 态 |
| "下载导出文件" | `ink-button-secondary`，带 pending 态 |
| 导出历史 | 导出文件卡片列表 |

#### UX 审计项

- [ ] 主操作按钮 disabled + tooltip 是否正常
- [ ] SSE 实时流是否自动刷新日志
- [ ] URL 参数 `workflow`/`execution`/`tab`/`export` 是否正确驱动状态
- [ ] "记住上次工作流"是否持久化
- [ ] 无效 execution 参数是否自动清理
- [ ] 导出面板预检机制：阻断项存在时是否禁止导出
- [ ] 导出格式 toggle 是否正确切换
- [ ] 导出历史是否正确加载
- [ ] 空状态文案是否语义清晰
- [ ] Banner 横幅 danger/warning 色调是否区分
- [ ] EnginePageShell 三层渐变背景是否在低端设备性能可接受
- [ ] EngineTaskFormPanels DraftRowEditor 动态增删是否流畅
- [ ] EngineTaskRegenerateSection "检查并确认"按钮是否正确弹出确认对话框
- [ ] PreparationStatusPanel StatusBadge 各状态是否语义清晰

---

### 3.11 作品洞察 `/workspace/project/:id/lab`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | `flex flex-col gap-5` |
| Hero | `hero-card`，`p-6`，3 列统计卡片 Grid |
| 三栏 Grid | `hero-card grid gap-4.5 p-4.5 [grid-template-columns: minmax(260px,320px) minmax(0,1fr) minmax(300px,360px)]` |

#### 交互元素

| 元素 | 样式 |
|------|------|
| 分析类型筛选 | AppSelect，含"全部类型"选项 |
| 正文片段筛选 | `ink-input`，placeholder "可选，输入某段正文的内容 ID" |
| 来源 Skill 筛选 | `ink-input`，placeholder "可选，例如 skill.style.river" |
| 洞察列表项 | `ink-tab` 样式按钮，`data-active` 标记选中 |
| "删除洞察" | `ink-button-danger`，带 pending 态 |
| 创建表单 | 洞察类型 AppSelect + 来源标题 `ink-input` + 来源 Skill `ink-input` + 正文 JSON `ink-textarea min-h-40` + 后续建议 `ink-textarea min-h-32` |
| "保存洞察" | `ink-button w-full`，带 pending 态 |

#### 对话框

| 对话框 | 触发 | 内容 |
|--------|------|------|
| LabDeleteConfirmDialog | 点击"删除洞察" | StatusBadge + 分析信息 + "确认删除"/"先保留" |

#### UX 审计项

- [ ] 三栏布局在窄屏下是否合理降级
- [ ] 筛选输入是否使用 deferredValue 优化
- [ ] 列表选择模式是否直观
- [ ] 删除后是否自动选择下一条记录
- [ ] 创建洞察乐观更新是否正确
- [ ] CodeBlock 展示 JSON 是否正确格式化
- [ ] 空状态各场景文案是否语义清晰（5 种空状态）
- [ ] 删除确认弹窗 pending 态是否正确

---

### 3.12 项目设置 `/workspace/project/:id/settings`

#### 布局

| 区域 | 样式 |
|------|------|
| 整体 | 双栏 Grid `grid gap-gap-lg grid-cols-[280px_1fr]`，`min-h-[calc(100vh-4rem)]`，`max-w-[1600px] mx-auto` |
| 侧边栏 | 280px 固定宽度，`sticky top-6 h-fit`，`rounded-3xl border bg-glass shadow-glass backdrop-blur-lg p-4` |
| 内容区 | `max-w-3xl mx-auto`，`rounded-2xl border bg-surface p-6 shadow-sm` |

#### 侧边栏

| 元素 | 样式 |
|------|------|
| 标题区 | `rounded-2xl bg-accent-soft px-4 py-3` |
| 项目信息区 | `rounded-2xl bg-surface-hover px-4 py-3`，含 StatusBadge |
| Tab 按钮 ×6 | `role="tab"`，`px-3.5 py-3`，选中态左侧 3px accent-primary 竖条 + `bg-accent-soft` |
| 脏标记 | 橙色小圆点 `bg-accent-warning`，`aria-label="有未保存的更改"` |
| 快捷链接 | GuardedLink ×3（编辑器/执行器/凭证） |
| PreparationStatusPanel | 项目准备状态 |

#### Tab 列表

| Tab | 面板 |
|-----|------|
| setting | ProjectSettingSummaryPanel |
| rules | AssistantRulesEditor |
| assistant | AssistantPreferencesPanel |
| skills | AssistantSkillsPanel |
| mcp | AssistantMcpPanel |
| audit | ProjectAuditPanel |

#### ProjectSettings 详细组件

| 组件 | 功能 | 关键 UI 元素 |
|------|------|-------------|
| ProjectSettingsContent | 内容区容器 | 根据 tab 条件渲染对应面板 |
| ProjectSettingsTabButton | Tab 按钮 | `role="tab"` + 图标 + 标签 + 描述 + 脏标记圆点 |
| ProjectSettingsIcons | 图标组件 | 各 Tab 对应的 SVG 图标 |
| ProjectSettingSummaryPanel | 摘要面板 | 项目摘要展示 |
| ProjectSettingSummaryEditor | 摘要编辑器 | 摘要字段编辑表单 |
| ProjectSettingSummaryPreview | 摘要预览 | 编辑结果预览 |
| ProjectAuditPanel | 审计面板 | 操作日志列表 |

#### UX 审计项

- [ ] 6 个 Tab 切换是否通过 URL `tab` 参数驱动
- [ ] 每个 Tab 独立 dirty 状态是否正确
- [ ] 脏标记橙色圆点是否在对应 Tab 显示
- [ ] 切换 Tab 时 UnsavedChangesDialog 是否正确触发
- [ ] GuardedLink 快捷链接是否带未保存变更守卫
- [ ] 无效 Tab 参数是否自动重定向
- [ ] 项目摘要加载 spinner 是否居中显示
- [ ] Escape 键拦截是否正常

---

## 四、共享组件审计

### 4.1 DialogShell

| 属性 | 值 |
|------|-----|
| 定位 | `fixed inset-0 z-50 flex items-end justify-center bg-[var(--overlay-bg)] backdrop-blur-[2px] p-4 md:items-center animate-overlay-in` |
| 面板 | `bg-glass-heavy rounded-2xl shadow-float backdrop-blur-xl max-h-[88vh] w-full max-w-6xl overflow-hidden animate-modal-in` |
| 移动端 | 面板底部对齐 |
| 桌面端 | 面板居中 |
| 关闭方式 | 遮罩点击 / 关闭按钮 / Escape |
| 焦点管理 | 自实现焦点陷阱（Tab 循环）+ 关闭后恢复焦点到 `restoreFocusRef` 或之前聚焦元素 |
| 滚动锁定 | 打开时锁定 body 滚动（`overflow: hidden`） |

**Props：**

| 属性 | 类型 | 必需 |
|------|------|------|
| children | `React.ReactNode` | 是 |
| description | `string` | 否 |
| onClose | `() => void` | 是 |
| restoreFocusRef | `RefObject<HTMLElement \| null>` | 否 |
| title | `string` | 是 |

#### 审计项

- [ ] 遮罩点击是否关闭
- [ ] Escape 键是否关闭
- [ ] Tab 键是否在对话框内循环
- [ ] 关闭后焦点是否恢复到触发元素
- [ ] 打开时页面背景是否不可滚动
- [ ] 移动端面板是否底部对齐
- [ ] 长内容是否可滚动（max-h-[88vh]）

### 4.2 UnsavedChangesDialog

| 属性 | 值 |
|------|-----|
| 标题 | "未保存更改" |
| 描述 | "离开当前编辑上下文后，未保存内容会丢失。" |
| 按钮 | "继续编辑"(`ink-button-secondary`) + "确认离开"(`ink-button-danger`) |
| pending 态 | 按钮禁用 |
| message | 可自定义，默认"有未保存的更改，确定要离开吗？" |

**Props：**

| 属性 | 类型 | 必需 | 默认值 |
|------|------|------|--------|
| isOpen | `boolean` | 是 | — |
| isPending | `boolean` | 是 | — |
| message | `string` | 否 | "有未保存的更改，确定要离开吗？" |
| onClose | `() => void` | 是 | — |
| onConfirm | `() => void` | 是 | — |

#### 审计项

- [ ] isDirty=true 时导航是否被拦截
- [ ] 浏览器后退是否被拦截
- [ ] beforeunload 是否触发浏览器原生提示
- [ ] 确认离开后是否执行挂起的导航
- [ ] 继续编辑后是否恢复原状态

### 4.3 AppSelect

| 属性 | 值 |
|------|-----|
| 基于 | Arco Design Select |
| 密度变体 | default / roomy |
| 空状态文案 | "暂无可选项" |
| 无效值 | 自动生成带 `callout-warning border-dashed` 样式的选项 |
| 弹出层 | `p-[0.28rem] border border-[var(--dropdown-border)] rounded-4 bg-[var(--dropdown-bg)] shadow-[var(--dropdown-shadow)] backdrop-blur-xl` |

#### 审计项

- [ ] 下拉弹出层样式是否与设计系统统一
- [ ] 选项含 description 时是否正确显示
- [ ] 无效值提示是否醒目
- [ ] disabled 态是否视觉区分
- [ ] roomy 密度是否增大高度和内边距

### 4.4 AppCard

| 变体 | CSS 类 | 说明 |
|------|--------|------|
| solid | panel-shell | 白底卡片 |
| muted | panel-muted | 灰底面板 |
| glass | panel-glass | 毛玻璃面板 |

#### 审计项

- [ ] 三种变体视觉差异是否明显
- [ ] header/body/footer 三段式布局是否正确
- [ ] as 属性是否正确渲染对应 HTML 元素

### 4.5 EmptyState

| 属性 | 值 |
|------|-----|
| 必需 | title + description |
| 可选 | action（操作按钮区域） |
| 容器 | `panel-glass flex min-h-48 flex-col items-start justify-center gap-3 p-6`（**左对齐**，非居中） |
| 标题 | `font-serif text-lg font-semibold text-text-primary` |
| 描述 | `max-w-2xl text-sm leading-6 text-text-secondary` |

#### 审计项

- [ ] 左对齐布局是否正确（非居中）
- [ ] 有 action 时按钮是否可点击
- [ ] 文案是否清晰

### 4.6 StatusBadge

支持 25 种状态映射，每种状态有对应颜色和中文标签。

#### 审计项

- [ ] 各状态颜色是否语义一致（success=绿, warning=橙, danger=红）
- [ ] 自定义 label 是否覆盖默认映射
- [ ] 未知状态是否有兜底样式

### 4.7 SectionCard

| 属性 | 值 |
|------|-----|
| 必需 | title + children |
| 可选 | action / description / className / bodyClassName / headerClassName |

**CSS 类：** `section-card panel-shell`，含 BEM 子元素 `section-card__header` / `section-card__copy` / `section-card__body`

#### 审计项

- [ ] header 区域标题和操作按钮是否对齐
- [ ] description 是否正确显示
- [ ] body 区域是否有合适的内边距

### 4.8 GuardedLink

| 属性 | 值 |
|------|-----|
| 必需 | href + isDirty + onNavigate + children |

#### 审计项

- [ ] isDirty=false 时是否正常导航
- [ ] isDirty=true 时是否触发 onNavigate 回调
- [ ] 回调中是否正确打开确认对话框

### 4.9 InfoPanel

| 属性 | 值 |
|------|-----|
| 根元素 | `<section>` |
| 必需 | children |
| 可选 | title / description / className / tone |
| tone 变体 | `"default"` / `"accent"` / `"warning"` / `"danger"` |

#### tone → 样式映射

| tone | 边框 | 背景 |
|------|------|------|
| default | `border-transparent` | `bg-muted` |
| accent | `border-accent-primary-muted` | `bg-accent-primary-soft` |
| warning | `border-accent-warning/30` | `bg-accent-warning/8` |
| danger | `border-accent-danger/30` | `bg-accent-danger/8` |

#### 审计项

- [ ] 4 种 tone 视觉差异是否明显且语义清晰
- [ ] 有 title 时 `<h3>` 是否使用 serif 字体
- [ ] 无 title/description 时是否只渲染 children
- [ ] `shadow-sm` 是否与设计系统统一

### 4.10 MetricCard

| 属性 | 值 |
|------|-----|
| 必需 | label + value |
| 可选 | detail / className |
| 容器 | `grid min-w-[118px] gap-1.5 rounded-2xl bg-muted px-4 py-3.5 shadow-sm` |
| 标签 | `text-text-tertiary text-[0.68rem] font-semibold tracking-[0.14em] uppercase` |
| 数值 | `text-text-primary text-[1.3rem] font-semibold font-variant-numeric:tabular-nums tracking-[-0.03em]` |
| 详情 | `text-text-secondary text-[0.82rem] leading-relaxed`（可选） |

#### 审计项

- [ ] 数值是否使用 tabular-nums 保证数字对齐
- [ ] 多个 MetricCard 并排时是否视觉统一
- [ ] detail 为空时是否不占空间

### 4.11 CodeBlock

| 属性 | 值 |
|------|-----|
| 必需 | value（unknown 类型） |
| 根元素 | `<pre>` + `mono-block` CSS 类 |
| 渲染 | `JSON.stringify(value, null, 2)` 格式化输出 |

#### 审计项

- [ ] 大 JSON 是否可滚动（不溢出容器）
- [ ] 等宽字体是否与 `--font-mono` 一致
- [ ] 深色背景对比度是否满足 WCAG AA

### 4.12 PageHeaderShell

| 属性 | 值 |
|------|-----|
| 必需 | eyebrow + title + description |
| 可选 | actions / footer / titleBadges |
| 容器 | `panel-shell`，响应式内边距 `px-4 py-4 md:px-5 xl:px-6 xl:py-5` |
| 眉毛文字 | `text-[0.68rem] tracking-[0.14em] text-accent-primary uppercase font-semibold` |
| 标题 | `<h1>`，`text-[1.35rem] md:text-[1.6rem]` |
| 描述 | `max-w-4xl text-[13px] leading-6 text-text-secondary` |
| 操作区 | `flex flex-wrap items-center gap-2` |
| 底部分隔 | `mt-4 border-t border-line-soft pt-4 md:mt-5 md:pt-[1.125rem]`（条件渲染） |

#### 审计项

- [ ] 标题 `<h1>` 是否每页只出现一次
- [ ] 响应式内边距变化是否流畅
- [ ] actions 区域过长时 flex-wrap 是否合理
- [ ] footer 分隔线样式是否与设计系统统一

### 4.13 FloatingPanelSupport

| 属性 | 值 |
|------|-----|
| 类型 | 工具模块（非组件），提供 Hook 和纯函数 |
| 导出 | `useFloatingPanelStyle` / `resolveFloatingPanelStyle` / `renderFloatingPanel` / `observeFloatingPanelLayoutChanges` |

#### 常量

| 常量 | 值 |
|------|-----|
| FLOATING_PANEL_VIEWPORT_MARGIN | 16px |
| FLOATING_PANEL_GAP | 8px |
| FLOATING_PANEL_MIN_HEIGHT | 160px |

#### useFloatingPanelStyle Hook

| 参数 | 类型 | 说明 |
|------|------|------|
| open | `boolean` | 面板是否打开 |
| anchorRef | `RefObject<HTMLElement>` | 锚点元素 |
| options | `FloatingPanelOptions` | align / maxHeight / preferredWidth / side / zIndex |

返回 `CSSProperties | undefined`，计算 `position:fixed` 的精确位置。

#### 行为

- 监听锚点 + 父级 + 祖先 `aside/section/main` 的 `ResizeObserver`
- 监听 window `resize` 和 `scroll`（capture phase）
- `renderFloatingPanel` 通过 `createPortal` 渲染到 `document.body`
- SSR 安全：`renderFloatingPanel` 返回 `null`

#### 审计项

- [ ] 浮动面板是否在视口边缘正确翻转（side top/bottom）
- [ ] 滚动时面板是否实时跟随锚点
- [ ] 多个浮动面板同时打开时 zIndex 是否正确
- [ ] SSR 环境下是否不报错

---

## 五、按钮样式体系审计

| 样式类 | 语义 | 视觉 | 出现页面 |
|--------|------|------|----------|
| `ink-button-hero` | 主 CTA | 渐变底，更大尺寸，hover 上浮 | 登录/注册提交 |
| `ink-button` | 主要操作 | 绿底白字，pill 圆角，光泽渐变 | 新建/保存/恢复/创建 |
| `ink-button-secondary` | 次要操作 | 透明底 + 边框 + 毛玻璃 | 返回/重试/清空/收起 |
| `ink-button-danger` | 危险操作 | 红边框透明底，hover 红底白字 | 删除/彻底删除/清空/确认离开 |
| `ink-tab` | Tab 切换 | `data-active` 控制高亮 | 分类/过滤/模式切换 |
| `ink-icon-button` | 图标操作 | 32×32 方形 | 工具栏图标按钮 |
| `ink-pill` | 标签选择 | `data-active` 控制高亮 | 状态标签/模式指示 |
| `ink-link-button` | 链接操作 | 链接风格 | 文字链接按钮 |

### 审计项

- [ ] 所有按钮 hover 态是否有视觉反馈
- [ ] 所有按钮 disabled 态是否视觉区分
- [ ] ink-button-hero hover 上浮动画是否流畅
- [ ] ink-button-danger hover 变色是否正确
- [ ] ink-tab active 态是否明显
- [ ] 按钮文案是否统一使用中文
- [ ] 按钮间距是否一致（gap-2 / gap-2.5）
- [ ] 按钮高度是否统一（h-9 为主）
- [ ] pending 态按钮是否禁用 + 文案切换

---

## 六、输入框样式体系审计

| 样式类 | 语义 | 视觉 |
|--------|------|------|
| `ink-input` | 标准输入 | 统一边框 + 圆角 |
| `ink-input-roomy` | 宽松输入 | 更大高度 + 毛玻璃背景 |
| `ink-textarea` | 文本域 | 统一边框 + 圆角 |

### 审计项

- [ ] 输入框 focus 态是否有明显边框变化
- [ ] placeholder 文案是否统一中文
- [ ] 必填字段是否有视觉标识
- [ ] 输入框错误态是否有红色边框
- [ ] ink-input-roomy 与 ink-input 视觉差异是否合理
- [ ] Textarea 自动高度是否正常
- [ ] maxLength 限制是否有字数提示

---

## 七、面板/卡片样式体系审计

| 样式类 | 语义 | 视觉 |
|--------|------|------|
| `panel-shell` | 标准面板 | 白底，hover 阴影增强 |
| `panel-muted` | 柔和面板 | 灰底 |
| `panel-glass` | 毛玻璃面板 | backdrop-blur |
| `hero-card` | 英雄卡片 | 大圆角 + 毛玻璃 + hero 阴影 |
| `section-card` | 分节卡片 | header + body 结构 |

### 审计项

- [ ] panel-shell hover 阴影增强是否流畅
- [ ] panel-glass 毛玻璃效果是否在所有浏览器正常
- [ ] hero-card 大圆角是否视觉统一
- [ ] 面板内边距是否一致（p-4 / p-5 / p-6）
- [ ] 面板间距是否一致（gap-4 / gap-5 / gap-6）

---

## 八、间距体系审计

### 8.1 Tailwind 自定义间距

| Token | 值 | 用途 |
|-------|-----|------|
| card-sm / md / lg / xl | — | 卡片内边距 |
| gap-sm / md / lg | — | 间距 |
| section-sm / md / lg | — | 区块间距 |

### 8.2 常用间距模式

| 场景 | 间距 |
|------|------|
| 页面外边距 | `p-6 lg:p-8` / `p-card-xl` |
| 卡片内边距 | `p-4` / `p-5` / `p-6` / `p-9` |
| 元素间距 | `gap-2` / `gap-4` / `gap-5` / `gap-6` / `gap-7` |
| 表单字段间距 | `space-y-4` |
| 标签与输入间距 | `space-y-2` / `grid gap-2` |
| 按钮间距 | `gap-2` / `gap-2.5` |
| 按钮内边距 | `px-4 h-9` / `px-3.5 py-3` |

### 审计项

- [ ] 同层级卡片内边距是否一致
- [ ] 页面级间距是否统一
- [ ] 表单字段间距是否统一
- [ ] 按钮组间距是否统一
- [ ] 响应式间距变化是否合理（lg: 前缀）

---

## 九、动画与过渡审计

### 9.1 Tailwind 自定义动画

| 动画名 | 效果 |
|--------|------|
| fade-in | 淡入 |
| slide-up | 上滑 |
| slide-in-left | 左滑入 |
| slide-from-left | 从左滑入 |
| slide-from-right | 从右滑入 |
| ink-fade-in | Ink 风格淡入 |
| typing-pulse | 打字脉冲 |
| modal-in | 模态框进入 |
| modal-out | 模态框退出 |
| overlay-in | 遮罩进入 |
| segment-slide | 段落滑动 |

### 9.2 过渡曲线

| Token | 用途 |
|-------|------|
| `--transition-fast` | 快速反馈 |
| `--transition-normal` | 常规过渡 |
| `--transition-slow` | 慢速过渡 |
| `--transition-spring` | 弹性效果 |
| `--transition-smooth` | 平滑效果 |

### 审计项

- [ ] 页面切换是否有过渡动画
- [ ] 模态框进入/退出动画是否流畅
- [ ] 项目卡片 hover 动画是否流畅
- [ ] 浮动面板出现/消失是否有过渡
- [ ] Tab 切换是否有过渡效果
- [ ] 动画是否尊重 prefers-reduced-motion

---

## 十、响应式审计

### 10.1 断点使用

| 断点 | 宽度 | 主要用途 |
|------|------|----------|
| sm | 640px | — |
| md | 768px | Grid 列数变化 |
| lg | 1024px | 双栏/三栏布局激活 |
| xl | 1280px | 侧边栏宽度调整 |
| 2xl | 1536px | 三栏布局优化 |
| 1900px | — | 配置注册中心三栏 |

### 10.2 关键响应式变化

| 页面 | 变化点 |
|------|--------|
| 登录/注册 | lg: 双栏布局，<lg: 单栏表单 |
| 书架 | 项目卡片网格 auto-fill minmax(320px,1fr) |
| 孵化器 | lg: 双栏聊天布局 |
| 模板库 | xl: 三栏布局 |
| 配置注册 | xl: 双栏，1900px: 三栏 |
| 大厅设置 | xl: 双栏 |
| Studio | lg/xl: 列宽变化 |

### 审计项

- [ ] 375px 宽度（iPhone SE）下所有页面是否可用
- [ ] 768px 宽度（iPad）下布局是否合理
- [ ] 1440px 宽度下布局是否舒适
- [ ] 1920px 宽度下内容是否过度拉伸
- [ ] 触摸设备上按钮是否足够大（最小 44×44px）
- [ ] 横屏模式下是否正常

---

## 十一、无障碍审计

### 11.1 ARIA 使用

| 组件 | ARIA 属性 |
|------|-----------|
| Tab 导航 | `role="tablist"` + `role="tab"` + `aria-selected` |
| Tab 面板 | `role="tabpanel"` |
| 导航链接 | `aria-disabled="true"`（禁用态） |
| 拖拽分隔栏 | `role="separator"` |
| 脏标记 | `aria-label="有未保存的更改"` |
| 格式选择 | `aria-pressed` |
| 跳转链接 | `sr-only`，focus-visible 时显示 |
| 反馈横幅 | `aria-live` |

### 审计项

- [ ] 所有 Tab 组件是否有正确的 ARIA role
- [ ] 禁用导航链接是否有 aria-disabled
- [ ] 模态框是否有焦点陷阱
- [ ] 关闭模态框后焦点是否恢复
- [ ] 跳转链接是否可用
- [ ] 颜色对比度是否满足 WCAG AA 标准
- [ ] 所有交互元素是否可键盘操作
- [ ] 屏幕阅读器是否可正确朗读页面结构

---

## 十二、确认对话框统一审计

| 对话框 | 页面 | 确认按钮 | 取消按钮 | pending 态 |
|--------|------|----------|----------|------------|
| UnsavedChangesDialog | Studio/Settings/ConfigRegistry | "确认离开" danger | "继续编辑" secondary | 按钮禁用 |
| CredentialDeleteConfirmDialog | 大厅设置-凭证中心 | "确认删除" danger | "先保留" secondary | — |
| CredentialDeleteConfirmDialog | 大厅设置-凭证 | "确认删除" danger | "先保留" secondary | — |
| LabDeleteConfirmDialog | 作品洞察 | "确认删除" danger | "先保留" secondary | "删除中..." |
| RecycleBinDeleteDialog | 回收站 | "确认彻底删除" danger | "先保留" secondary | "删除中..." |
| RecycleBinClearDialog | 回收站 | "确认清空" danger | "先保留" secondary | "清空中..." |
| EngineTaskRegenerateDialog | 作品推进 | "确认重建" danger | "再检查一下" secondary | — |
| StudioDocumentTreeDialog | 创作工作台 | "确定" (Arco Modal) | "取消" | confirmLoading |

### 审计项

- [ ] 所有危险操作确认按钮是否使用 danger 样式
- [ ] 取消按钮文案是否统一（"先保留"/"继续编辑"/"再检查一下"）
- [ ] pending 态是否禁用按钮 + 切换文案
- [ ] 遮罩点击是否关闭（StudioDocumentTreeDialog 使用 Arco Modal，行为可能不同）
- [ ] Escape 键是否关闭
- [ ] 焦点管理是否正确

---

## 十三、Tab 组件统一审计

| Tab 组 | 页面 | 样式 | 行为 |
|--------|------|------|------|
| EngineDetailPanel | 作品推进 | ink-tab | 单选，URL 驱动 |
| CredentialScopeTabs | 大厅设置-凭证 | ink-tab | 单选 |
| CredentialModeTabs | 大厅设置-凭证 | ink-tab | 单选 |
| ConfigRegistrySidebar | 配置注册 | ink-tab | 单选 |
| IncubatorModeSwitch | 新建作品 | role=tab | 单选 |
| TemplateVisibility | 模板库 | ink-tab | 单选 |
| TemplateGenre | 模板库 | ink-tab | toggle（可取消选中） |
| LobbySettingsSidebar | 大厅设置 | 导航按钮 | 单选，URL 驱动 |
| ProjectSettingsSidebar | 项目设置 | role=tab | 单选，URL 驱动，脏标记 |

### 审计项

- [ ] 所有 Tab 切换是否有视觉反馈
- [ ] URL 驱动的 Tab 刷新后是否保持状态
- [ ] TemplateGenre toggle 行为是否正确
- [ ] ProjectSettings 脏标记是否正确显示
- [ ] Tab 切换时面板内容是否正确渲染

---

## 十四、页面流转测试用例

### TC-01: 认证流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 访问 `/` | 重定向到 `/auth/login` |
| 2 | 点击"还没有账号？创建账号" | 跳转到 `/auth/register` |
| 3 | 填写注册表单并提交 | 注册成功，自动登录，跳转到 `/workspace/lobby` |
| 4 | 退出登录 | 跳转到 `/auth/login` |
| 5 | 填写登录表单并提交 | 登录成功，跳转到 `/workspace/lobby` |

### TC-02: 书架导航流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在书架页点击"新建作品" | 跳转到 `/workspace/lobby/new` |
| 2 | 创建作品成功 | 跳转到 `/workspace/project/:id/studio` |
| 3 | 在书架页点击项目卡片"继续创作" | 跳转到对应项目 Studio |
| 4 | 在书架页点击"模板库"导航 | 跳转到 `/workspace/lobby/templates` |
| 5 | 在书架页点击"回收站"导航 | 跳转到 `/workspace/lobby/recycle-bin` |
| 6 | 在书架页点击"我的助手"导航 | 跳转到 `/workspace/lobby/settings` |

### TC-03: 项目内导航流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在 Studio 页点击"作品推进" | 跳转到 Engine 页 |
| 2 | 在 Header 点击"洞察" | 跳转到 Lab 页 |
| 3 | 在 Header 点击"项目设置" | 跳转到 ProjectSettings 页 |
| 4 | 在 Header 点击"← 返回书架" | 跳转到 `/workspace/lobby` |
| 5 | 有未保存更改时点击导航 | 弹出 UnsavedChangesDialog |

### TC-04: 回收站流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 在书架页删除项目 | 项目移入回收站（无确认弹窗） |
| 2 | 进入回收站 | 显示已删除项目列表 |
| 3 | 点击"恢复" | 项目恢复到书架 |
| 4 | 点击"彻底删除" | 弹出 RecycleBinDeleteDialog |
| 5 | 确认彻底删除 | 项目永久删除 |
| 6 | 点击"清空回收站" | 弹出 RecycleBinClearDialog |
| 7 | 确认清空 | 所有回收站项目永久删除 |

### TC-05: 配置注册中心流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 点击分类 Tab 切换 | 列表过滤对应类型 |
| 2 | 输入搜索关键词 | 列表实时过滤 |
| 3 | 点击标签过滤 Tab | 列表按标签过滤 |
| 4 | 点击状态过滤 Tab | 列表按状态过滤 |
| 5 | 编辑配置项 | 编辑器面板打开 |
| 6 | 修改后点击其他分类 | 弹出 UnsavedChangesDialog |
| 7 | 确认离开 | 丢弃更改，切换分类 |

### TC-06: Studio 编辑流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 点击目录树文件节点 | 编辑器加载对应文稿 |
| 2 | 编辑内容 | 保存按钮变为"保存"状态 |
| 3 | 点击保存 | 文稿保存，按钮变为"XX已保存" |
| 4 | 右键目录树节点 | 显示上下文菜单 |
| 5 | 点击"新建文档" | 弹出 StudioDocumentTreeDialog |
| 6 | 输入名称并确认 | 新文档创建到目录树 |
| 7 | 点击"收起/展开助手" | 聊天面板显隐切换 |
| 8 | 拖拽聊天面板分隔栏 | 面板宽度调整 |
| 9 | 有未保存更改时点击导航 | 弹出 UnsavedChangesDialog |

### TC-07: Engine 推进流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 点击"启动推进" | 工作流开始执行 |
| 2 | 切换详情面板 Tab | 显示对应面板内容 |
| 3 | 点击"导出成稿" | 弹出导出面板 |
| 4 | 选择导出格式 | 格式 toggle 切换 |
| 5 | 点击"创建导出文件" | 开始导出 |
| 6 | 导出完成后点击"下载" | 下载导出文件 |

### TC-08: Lab 洞察流程

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 填写创建表单并保存 | 新洞察创建，列表更新 |
| 2 | 点击列表项 | 详情面板显示对应洞察 |
| 3 | 使用筛选器过滤 | 列表实时过滤 |
| 4 | 点击"删除洞察" | 弹出 LabDeleteConfirmDialog |
| 5 | 确认删除 | 洞察删除，自动选择下一条 |

---

## 十五、全局 UX 审计清单

### 15.1 加载状态

- [ ] 所有页面首次加载是否有 loading 指示
- [ ] 按钮操作 pending 态是否禁用 + 文案切换
- [ ] 列表加载是否有骨架屏或文字提示
- [ ] 长时间操作是否有进度指示

### 15.2 错误处理

- [ ] 网络错误是否有友好提示
- [ ] 表单校验错误是否即时反馈
- [ ] 401 错误是否自动跳转登录
- [ ] 权限错误是否有友好提示
- [ ] 错误提示是否可关闭

### 15.3 表单体验

- [ ] 必填字段是否有标识
- [ ] 输入校验是否即时
- [ ] 表单提交失败是否保留已填数据
- [ ] 长表单是否有分组
- [ ] 日期/时间输入是否便捷

### 15.4 导航体验

- [ ] 当前页面在导航栏是否有高亮
- [ ] 面包屑是否正确
- [ ] 浏览器前进/后退是否正常
- [ ] 刷新页面是否保持状态（URL 参数驱动）
- [ ] 深层链接是否可直接访问

### 15.5 一致性

- [ ] 相同功能在不同页面的按钮样式是否一致
- [ ] 相同操作的确认弹窗模式是否一致
- [ ] 空状态文案风格是否统一
- [ ] 加载文案风格是否统一（"正在加载XX…"）
- [ ] 错误文案风格是否统一
- [ ] 间距体系是否一致

### 15.6 性能感知

- [ ] 页面切换是否流畅
- [ ] 列表滚动是否流畅
- [ ] 搜索过滤是否有防抖/deferredValue
- [ ] 大列表是否有虚拟滚动
- [ ] 图片/资源加载是否有占位

---

## 十六、状态管理层审计

### 16.1 Zustand Stores

#### useAuthStore — 认证状态

| 属性 | 值 |
|------|-----|
| 存储位置 | `lib/stores/auth-store.ts` |
| 持久化 Key | `"easystory-auth"`，localStorage |
| SSR 安全 | `typeof window === "undefined"` 时使用 `noopStorage` |

**State：**

| 字段 | 类型 | 默认值 |
|------|------|--------|
| token | `string \| null` | `null` |
| user | `{ userId: string; username: string } \| null` | `null` |
| hasHydrated | `boolean` | `false` |

**Actions：**

| Action | 行为 |
|--------|------|
| setSession | 设置 token + user |
| clearSession | 跨 store 调用 `useWorkspaceStore.getState().clearProjectContext()` → 清空 token + user |
| markHydrated | 标记 hydration 完成 |

**工具函数：** `getAuthToken()` — 直接从 store 读取 token（不触发重渲染）

#### useWorkspaceStore — 工作区偏好

| 属性 | 值 |
|------|-----|
| 存储位置 | `lib/stores/workspace-store.ts` |
| 持久化 Key | `"easystory-workspace"`，localStorage |
| 持久化字段 | `lastProjectId` / `lastWorkflowByProject` / `sidebarPreference` / `studioChatWidthByProject` |

**State：**

| 字段 | 类型 | 默认值 |
|------|------|--------|
| lastProjectId | `string \| null` | `null` |
| lastWorkflowByProject | `Record<string, string>` | `{}` |
| sidebarPreference | `"expanded" \| "collapsed"` | `"expanded"` |
| studioChatWidthByProject | `Record<string, number>` | `{}` |
| hasHydrated | `boolean` | `false` |

**Actions：**

| Action | 行为 |
|--------|------|
| setLastProjectId | 记录最近访问的项目 |
| setLastWorkflow | 记录项目对应的最近 workflow |
| setSidebarPreference | 展开/折叠侧边栏偏好 |
| setStudioChatWidth | 按项目记录聊天面板宽度（null 时删除） |
| clearProjectContext | 清空 lastProjectId + lastWorkflowByProject |

#### incubator-chat-store — 孵化器聊天状态

| 属性 | 值 |
|------|-----|
| 存储位置 | `features/lobby/components/incubator/incubator-chat-store.ts` |
| 持久化 | 无（内存态，页面关闭即清空） |

#### studio-chat-store — Studio 聊天状态

| 属性 | 值 |
|------|-----|
| 存储位置 | `features/studio/components/chat/studio-chat-store.ts` |
| 持久化 | 无（内存态，页面关闭即清空） |

### 16.2 Providers

#### AppProviders — 全局 Provider 栈

| 属性 | 值 |
|------|-----|
| 存储位置 | `lib/providers/app-providers.tsx` |
| React 19 兼容 | 导入 `@arco-design/web-react/es/_util/react-19-adapter` |

**Provider 栈（外→内）：**

| 层级 | Provider | 配置 |
|------|----------|------|
| 1 | Arco `ConfigProvider` | `autoInsertSpaceInButton={false}`，`locale={zhCN}` |
| 2 | TanStack `QueryClientProvider` | `retry: false`，`refetchOnWindowFocus: false` |

### 16.3 Custom Hooks

#### useUnsavedChangesGuard — 未保存变更守卫

| 属性 | 值 |
|------|-----|
| 存储位置 | `lib/hooks/use-unsaved-changes-guard.ts` |
| 参数 | `currentUrl` / `isDirty` / `router` |

**返回值：**

| 返回 | 类型 | 说明 |
|------|------|------|
| isConfirmOpen | `boolean` | 确认对话框是否可见 |
| attemptNavigation | `(onConfirm, onCancel?) => void` | 编程式导航守卫 |
| handleDialogClose | `() => void` | 关闭对话框 + 取消导航 + 调用 onCancel |
| handleDialogConfirm | `() => void` | 关闭对话框 + 执行挂起的导航 |

**拦截行为：**

| 场景 | 机制 |
|------|------|
| `<a>` 同源链接点击 | `event.preventDefault()` + 打开确认框；确认后 `router.push` |
| 浏览器前进/后退 | `popstate` 监听 + `history.pushState` 回推 + 打开确认框 |
| 关闭标签页/窗口 | `beforeunload` + `event.returnValue = ""` |
| 排除条件 | `_blank` target / `download` 属性 / 修饰键 / 相同路径 |

### 审计项

- [ ] Auth Store：token 过期后是否正确清理并跳转登录
- [ ] Auth Store：SSR hydration 是否不闪烁（hasHydrated 门控）
- [ ] Auth Store：clearSession 是否清理关联的 workspaceStore 数据
- [ ] Workspace Store：studioChatWidth 持久化是否按项目隔离
- [ ] Workspace Store：sidebarPreference 切换是否即时生效
- [ ] Workspace Store：项目数增多时 lastWorkflowByProject 是否有清理策略
- [ ] TanStack Query：retry=false 是否导致偶发网络错误直接失败
- [ ] TanStack Query：缓存时间是否合理（默认 5min）
- [ ] useUnsavedChangesGuard：IME 输入中是否误触发
- [ ] useUnsavedChangesGuard：多组件同时使用时 pendingNavigation 是否冲突
- [ ] useUnsavedChangesGuard：确认后导航是否在 `startTransition` 内执行

---

## 附录 A：Arco Design 组件使用清单

| Arco 组件 | 使用位置 | 是否覆写样式 |
|-----------|----------|-------------|
| Button | 孵化器聊天发送 | 是 |
| Input / Input.TextArea | 孵化器聊天输入 | 是 |
| Select | AppSelect 封装 | 是 |
| Modal | StudioDocumentTreeDialog | 是 |
| Dropdown + Menu | 目录树右键菜单 | 是 |
| Avatar | Header 用户头像 | 是 |
| Notification | AppNotice 封装 | 是 |
| Message | Studio/Engine toast | 是 |
| Switch | 孵化器/配置注册/偏好表单 | 是 |
| Checkbox | 上下文选择器/聊天设置/表单字段 | 是 |
| Radio | 配置注册表单字段 | 是 |
| Progress | Studio 聊天消息气泡 ToolProgress | 是 |
| ConfigProvider | AppProviders | — |

## 附录 B：自定义组件 vs Arco 组件对照

| 功能 | 自定义实现 | Arco 原生 |
|------|-----------|-----------|
| 对话框 | DialogShell（焦点陷阱、Escape、遮罩） | 仅 StudioDocumentTreeDialog 使用 Arco Modal |
| Tab | ink-tab 按钮 + data-active | 不使用 Arco Tabs |
| 通知 | AppNotice（封装 Arco Notification） | — |
| Toast | Arco Message | — |
| 选择器 | AppSelect（封装 Arco Select） | — |
| 浮动面板 | FloatingPanelSupport | 不使用 Arco Popover/Trigger |
| 导航守卫 | useUnsavedChangesGuard + GuardedLink | — |

---

## 附录 C：表单控件审计

### C.1 Switch 使用

| 使用位置 | 功能 |
|----------|------|
| 孵化器页面 | 模式切换 |
| 孵化器聊天设置 | 各项开关 |
| 配置注册 Skill/Agent 表单 | 启用/停用 |
| 配置注册 Hook/MCP 表单 | 启用/停用 |
| 配置注册编辑器面板 | 编辑模式切换 |
| 孵化器面板 | 能力开关 |

### C.2 Checkbox 使用

| 使用位置 | 功能 |
|----------|------|
| Studio 聊天上下文选择器 | 文档多选 |
| 孵化器聊天设置 | 多选项 |
| 配置注册表单字段 | 多选列表 |

### C.3 Radio 使用

| 使用位置 | 功能 |
|----------|------|
| 配置注册表单字段 | 单选组 |

### 审计项

- [ ] Switch 样式是否与 Ink 设计语言统一（Arco 覆写是否生效）
- [ ] Checkbox 选中态颜色是否为 accent-primary
- [ ] Radio 选中态颜色是否为 accent-primary
- [ ] 所有 Switch 是否有对应的标签说明
- [ ] 禁用态是否视觉区分

---

## 附录 D：ConfigRegistry 详细组件

| 组件 | 功能 | 关键 UI 元素 |
|------|------|-------------|
| ConfigRegistryPagePrimitives | 页面原语 | Banner、FeedbackBanner 等基础 UI |
| ConfigRegistrySkillAgentForm | Skill/Agent 表单 | 通用字段 + 模型配置区段 |
| ConfigRegistryHookMcpForm | Hook/MCP 表单 | JSON 字段 + Switch + 撤销修改按钮 |
| ConfigRegistryFormFields | 通用表单字段 | TextField / TextAreaField / SelectField / RadioGroupField / CheckboxListField / StaticField / FormSection / FormNotice |
| ConfigRegistryJsonField | JSON 字段编辑器 | JSON 输入 + 校验 |
| ConfigRegistryModelConfigSection | 模型配置区段 | 模型选择 + 参数配置 |
| ConfigRegistryStructuredEditor | 结构化编辑器 | 可视化编辑器 |
| ConfigRegistrySkillReader | Skill 读取器 | Skill 配置只读展示 |

---

## 附录 E：ECharts 使用审计

| 使用位置 | 图表类型 | 交互 |
|----------|----------|------|
| JsonRelationGraph | 力导向图（force layout） | 缩放/平移/点击选中/悬停高亮/Tooltip |

### 审计项

- [ ] ECharts Canvas 渲染器在低端设备是否流畅
- [ ] 图谱节点数量较多时（50+）是否需要懒加载或虚拟化
- [ ] Tooltip 样式是否与 Ink 设计语言统一
- [ ] 图谱颜色是否与全局色彩体系协调
- [ ] 图谱在窄屏下是否可用

---

## 附录 F：Next.js 特殊路由缺失

| 文件 | 状态 | 影响 |
|------|------|------|
| `loading.tsx`（根级） | **缺失** | 根布局级无 loading 指示 |
| `error.tsx`（根级） | **缺失** | 根布局级无统一错误边界 |
| `not-found.tsx`（根级） | **缺失** | 无自定义 404 页面 |
| `global-error.tsx`（根级） | **缺失** | 根布局级错误无兜底页面 |
| `workspace/loading.tsx` | **缺失** | workspace 布局级无 loading 指示 |
| `workspace/error.tsx` | **缺失** | workspace 布局级无错误边界（如无效项目 ID 无统一提示） |
| `workspace/not-found.tsx` | **缺失** | workspace 下无效路由无自定义提示 |

### 审计项

- [ ] 是否需要添加 `loading.tsx` 提供路由级加载指示
- [ ] 是否需要添加 `error.tsx` 提供路由级错误边界
- [ ] 是否需要添加 `not-found.tsx` 提供自定义 404 页面
- [ ] 访问不存在的路由时用户体验如何（当前应显示 Next.js 默认 404）

---

## 附录 G2：残留目录

| 目录 | 路径 | 状态 |
|------|------|------|
| demo | `src/app/demo/` | **已清理** |
| test-v2 | `src/app/test-v2/` | **已清理** |
| v2-demo | `src/app/v2-demo/` | **已清理** |

### 审计项

- [ ] 空目录是否需要清理（影响构建产物或目录结构清晰度）
- [ ] 是否有引用指向这些目录

---

## 附录 G3：测试覆盖概览

测试文件（`.test.ts`）与组件同目录放置，共计 72 个：

| 模块 | 测试文件数 | 覆盖重点 |
|------|-----------|----------|
| studio | 15 | 聊天状态/发送守卫/模型/Composer/技能/上下文/写入效果、文档支持/反馈/同步、目录树、页面支持 |
| engine | 11 | 格式化、流处理、任务支持、工作流状态/摘要、导出/回放/日志/详情面板 |
| settings/credential | 8 | 凭证表单/兼容性/反馈/覆盖/用户代理/删除确认 |
| settings/assistant | 7 | Skills/Rules/Preferences/MCP/Hooks/Agents/Markdown 文档支持 |
| lobby/incubator | 7 | 聊天状态/模型/设置/草稿/提交/流客户端/请求支持 |
| shared/assistant | 6 | 流默认值/推理/凭证/输出 token/技能选项/Markdown 文档支持 |
| config-registry | 5 | 状态管理/表单逻辑/通知/Skill Reader/引用支持 |
| project-settings | 3 | 审计面板/设置支持/摘要编辑 |
| workspace | 2 | Shell 支持/Store 支持 |
| project | 2 | 准备状态/摘要支持 |
| lobby/projects | 1 | 项目模型支持 |
| lobby/settings | 1 | 设置路由支持 |
| lobby/templates | 1 | 模板库支持 |
| lab | 1 | 基础支持逻辑 |
| observability | 1 | 时间格式化 |
| components/ui | 1 | 浮动面板支持 |

### 审计项

- [ ] 所有 `.test.ts` 文件是否在 CI 中被执行
- [ ] 测试覆盖率是否有最低门槛
- [ ] 组件渲染测试（`.tsx` 测试）是否缺失
- [ ] E2E 测试是否存在（当前仅单元测试）

---

## 附录 G：完整组件清单统计

| 模块 | .tsx 组件数 | 关键子组件 |
|------|------------|-----------|
| studio/components | 19 | 文档编辑器×3（Markdown/JSON/总入口）、关系图谱、影响面板×2、聊天面板×6（含 Composer）、目录树×2、页面×2 |
| engine/components | 18 | 页面壳、详情面板×7、导出面板、任务表单×2、状态卡片×3、风格参考辅助 |
| lab/components | 5 | 页面、侧边栏、详情面板、创建面板、删除确认 |
| settings/components | 36 | 凭证中心×12（含删除确认+标签+审计面板）、助手面板×24（含 AgentModeEditors、HookGuidedFields、EditorPrimitives） |
| config-registry/components | 12 | 页面、侧边栏、详情/编辑面板、表单×5、原语、SkillReader |
| lobby/components | 26 | 项目列表×3、孵化器×13、模板库×4、设置×3、回收站×2、通用×1 |
| project-settings/components | 9 | 页面、侧边栏、内容区、摘要×3、审计、图标、Tab按钮（未使用） |
| project/components | 1 | 准备状态面板 |
| workspace/components | 2 | 工作区壳、图标 |
| auth/components | 2 | 认证表单、认证守卫 |
| components/ui | 13 | 共享 UI 基础组件 |
| **合计** | **~143** | — |

### 与上次审计（2026-04-12）的差异汇总

| 维度 | 旧值 | 新值 | 说明 |
|------|------|------|------|
| .tsx 组件总数 | ~151 | **143** | 减少 8 个，组件合并/重构 |
| 测试文件总数 | ~50 | **72** | 增长 44% |
| Design Token 分组 | 10 | **16** | 新增下拉/遮罩/Callout/Toolbar/Chat/渐变 |
| accent 变量数 | 12 | **20** | 新增 primary-hover/primary-soft/primary-muted/primary-dark/danger-active/info/info-soft/info-muted/warning-soft/success-soft/danger-soft |
| shadow 层级 | 7 | **9** | 新增 glass-heavy/panel-side，xl→hero |
| z-index 命名 | base/dropdown/sticky/overlay/modal/popover/toast | **base/surface/elevated/sticky/overlay/modal/toast** | dropdown→surface，popover 移除，新增 elevated |
| CSS 组件类 | 22 | **39** | 新增 ink-toolbar-*、callout-*、badge 变体、scrollbar-hide、section-card BEM 子元素 |
| Arco 覆写组件 | 29 | **30** | 新增 Link |
| StatusBadge 状态 | 20+ | **25** | 新增 setting/outline/opening_plan/chapter_tasks/workflow/chapter |
| 残留目录 | 3 个未清理 | **已清理** | demo/test-v2/v2-demo |
| 书架页 | LobbyEntryCard + MetricCard | **LobbyProjectCard + 统计文字** | 完成布局重设计 |
| 孵化器 | IncubatorChatPanel | **ChatModePanel + ModeSwitch** | 双模式架构 |
| Studio 编辑器 | ChapterEditor + StoryAssetEditor | **MarkdownDocumentEditor + JsonDocumentEditor** | 双编辑器+关系图预览 |
| Engine 背景 | 硬编码渐变 | **CSS 变量** `--bg-engine-page-gradient` | 样式统一 |
| EmptyState | items-center（居中） | **items-start**（左对齐） | 布局修正 |
| DialogShell | 无 restoreFocusRef | **新增** restoreFocusRef | 焦点恢复控制 |
| Lobby 内容区宽度 | max-w-[1560px] | **w-[min(100%-2.5rem,1560px)]** | 响应式优化 |
