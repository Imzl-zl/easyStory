# 项目设置页面 UI/UX 设计规范

| 字段 | 内容 |
|---|---|
| 文档类型 | 页面级 UI/UX 校准稿 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-31 |
| 最后更新 | 2026-04-01 |
| 适用范围 | `/workspace/project/[projectId]/settings` |

---

## 1. 文档定位

本文只定义“项目设置页”这一页面的结构、交互边界和后续优化方向，不再复制全局样式 token，也不替代运行时源码真值。

真值边界如下：

- 产品语义与一级页面原则：`docs/ui/ui-design.md`
- 全局 design token、`SectionCard`、`.ink-*`、`.label-text`：`apps/web/src/app/globals.css`
- 路由入口：`apps/web/src/app/workspace/project/[projectId]/settings/page.tsx`
- 页面骨架与 query 规则：`apps/web/src/features/project-settings/components/project-settings-page.tsx`
- 页面壳层样式：`apps/web/src/features/project-settings/components/project-settings-page.module.css`
- 项目设定编辑器：`apps/web/src/features/studio/components/project-setting-editor.tsx`
- 项目规则 / AI 偏好 / Skills / MCP：`apps/web/src/features/settings/components/*`
- 项目审计：`apps/web/src/features/project-settings/components/project-audit-panel.tsx`

本文不再维护第二套颜色、间距、按钮状态表。若全局样式发生变化，以 `apps/web/src/app/globals.css` 为准。

---

## 2. 页面真值

### 2.1 路由与 Query

- 页面路由：`/workspace/project/[projectId]/settings`
- `tab` 允许值：`setting | rules | assistant | skills | mcp | audit`
- 未传 `tab` 时默认进入 `setting`
- `event` 只用于 `audit` 页的审计事件过滤
- 非法 `tab` 和未规范化的 `event` 会在页面加载后自动纠正

### 2.2 页面骨架

- 桌面端采用 `280px + 1fr` 双列布局，页面最大宽度 `1600px`
- 左侧为 sticky 侧栏，负责：
  - 项目标题与状态
  - 标签页导航
  - 跳转到 Studio / Engine / 项目凭证
  - `PreparationStatusPanel`
- 右侧为内容区，每个 tab 外层统一包一层 `contentCard`
- 页面只在壳层层面控制布局；tab 内部结构由各自面板决定

### 2.3 交互保护

- 当前 dirty state 按 tab 粒度维护：
  - `setting`
  - `rules`
  - `assistant`
  - `skills`
  - `mcp`
- `audit` 当前无编辑态，不参与 dirty 判断
- 未保存保护覆盖：
  - 切换 tab
  - 点击侧栏跳转链接
  - 浏览器刷新 / 关闭
  - 浏览器后退 / 前进
- 页面存在未保存修改时，`Escape` 会被拦截，避免误触关闭类交互

---

## 3. 共享视觉基线

项目设置页应复用全局视觉原件，不单独再定义一套页面 token。

### 3.1 必须复用的共享原件

- `SectionCard`
- `panel-shell`
- `panel-muted`
- `ink-input`
- `ink-textarea`
- `ink-button`
- `ink-button-secondary`
- `label-text`
- `StatusBadge`
- `EmptyState`
- `AppNotice`

### 3.2 当前真实尺寸与样式口径

- `SectionCard` 头部 / 内容区默认内边距为 `20px 24px`
- `SectionCard` 在小屏幕下收缩为 `14px 16px`
- `ink-input` 当前 `min-height` 为 `36px`
- `ink-textarea` 当前不设统一固定高度，由各场景通过 `min-h-*` 控制
- 主要按钮高度当前为 `32px`
- `AppSelect` 有独立皮肤，当前 `min-height` 约为 `2.5rem`

### 3.3 页面级样式边界

页面自身的 CSS 只负责：

- 外层网格布局
- 侧栏 sticky 与滚动条
- 侧栏 tab 激活态
- 页面级动画与响应式收口
- `contentCard` / `errorCard` 等壳层容器

不要在本页再复制一套输入框、按钮、卡片状态样式。

---

## 4. 各标签页校准

### 4.1 项目设定（Setting）

**当前真实结构**

- 使用 `SectionCard`
- 头部带两个动作按钮：`完整度检查`、`保存设定`
- 顶部有完整度摘要卡 + `StatusBadge`
- 中间为 `md:grid-cols-2` 的短字段网格：
  - 题材、子题材、目标读者、整体语气
  - 主角姓名、主角身份
  - 世界名称、力量体系
  - 目标字数、目标章节
- 下方为 3 个全宽文本域：
  - 核心冲突
  - 剧情走向
  - 特殊要求
- 保存成功后可显示 `ProjectSettingImpactPanel`

**当前问题**

- 字段虽然已有两列网格，但“基本信息 / 角色 / 世界观 / 规模”仍是平铺排列
- DOM 语义上还没有 `fieldset / legend`
- 完整度卡已经存在，但视觉权重仍可略增强

**后续建议**

- 保留“两列短字段 + 全宽文本域”的基本结构
- 为四组短字段补上语义化分组
- 不要把全文强制改成单列长表单
- 不新增第二套表单原件，继续复用 `ProjectSettingField`

### 4.2 规则（Rules）

**当前真实结构**

- 复用共享组件 `AssistantRulesEditor`
- 当前是“启用开关 + 普通 textarea + 保存/还原”
- 文本编辑器是普通文本域，不是 Markdown 编辑器
- 通过 `scope="project"` 进入项目层规则

**当前问题**

- 启用开关与正文编辑区的层级关系还比较平
- 规则长度、状态和作用范围主要依赖说明文案传达

**后续建议**

- 可以增强“当前项目专属规则”的作用域提示
- 可以加字符统计，但不是必须项
- 保持共享组件复用，不要把项目版单独拆成另一套表单

### 4.3 AI 偏好（Assistant）

**当前真实结构**

- 复用 `AssistantPreferencesPanel` + `AssistantPreferencesForm`
- 当前字段只有 3 个：
  - 默认连接
  - 默认模型
  - 默认单次回复上限
- 项目页会同时加载项目凭证和用户凭证，构造连接选项
- “跟随个人 AI 偏好”当前不是独立开关，而是通过字段留空实现
- 表单在 `xl` 下使用三列布局

**当前问题**

- “留空即继承个人设置”的规则只体现在说明文案里
- 用户能配置覆盖，但很难一眼看出自己当前是否正在继承上层默认值

**后续建议**

- 不要凭空添加“跟随个人 AI 偏好”开关，除非后端字段模型一起变更
- 若要强化可见性，优先补“当前来源/覆盖状态”提示，而不是改数据结构
- 继续保持与用户侧 AI 偏好共用一套组件

### 4.4 Skills

**当前真实结构**

- 复用 `AssistantSkillsPanel`
- 内部是“左侧列表 + 右侧编辑器”的两栏结构
- 左栏在 `xl` 下 sticky，宽度约 `280px`
- 右侧负责新建 / 编辑 / 删除
- 面板内部已有自己的 dirty 防切换提示

**当前问题**

- 不适合再对外层内容卡施加统一 `800px` 限宽
- 小屏幕下左栏和编辑区的纵向切换仍有继续优化空间

**后续建议**

- 保留内部两栏结构
- 页面级规范不得要求它退化成单列长表单
- 若继续优化，优先做移动端和列表信息密度收口

### 4.5 MCP

**当前真实结构**

- 复用 `AssistantMcpPanel`
- 结构与 `Skills` 基本一致，也是“左侧列表 + 右侧编辑器”
- 面板内部同样维护自己的 dirty 防切换提示

**当前问题**

- 与 `Skills` 一样，不适合套用统一窄卡布局

**后续建议**

- 和 `Skills` 维持一致的结构与交互口径
- 后续优化优先级也应与 `Skills` 保持一致

### 4.6 审计（Audit）

**当前真实结构**

- 使用 `ProjectAuditPanel`
- 已有事件过滤输入框
- 已有空状态、加载态、错误态
- 当前是“卡片列表 + 展开详情”，不是表格
- 详情通过 `CodeBlock` 展示

**当前问题**

- 过滤方式仍偏技术向，需要用户知道事件名
- `actor`、`details` 等文案还偏内部视角

**后续建议**

- 可以增加预设过滤项或更友好的筛选器
- 不要把当前页面描述成“表格待补齐”，因为它现在本来就不是表格设计

---

## 5. 响应式口径

- `<= 1023px`：
  - 页面改为单列
  - 侧栏从 sticky 改为普通流式块
  - 侧栏不会隐藏，只会排到内容区上方
- `<= 767px`：
  - 页面间距、卡片内边距、侧栏按钮尺寸一起收紧
  - `SectionCard` 全局内边距同步切到移动端尺寸
- `Skills / MCP` 等复杂面板的内部响应式，由各自组件负责，不在页面壳层强行覆盖

---

## 6. 后续实现约束

- 保留项目设置页现有 query 契约，不随意改 `tab` / `event` 语义
- 保留当前 tab 粒度 dirty state，不要退化成整页共享一个粗粒度标记
- 保留 `useUnsavedChangesGuard` 对链接、浏览器返回和刷新关闭的覆盖
- 项目页继续复用共享 assistant 组件，通过 `scope="project"` 表达项目层
- 若后续需要统一 select 与 input 的高度，应在共享原件层处理，而不是只在项目页局部打补丁
- 若变更全局 token、`SectionCard` 或 `.ink-*`，应更新源码真值和相关总文档，不在本文手工维护镜像表

---

## 7. 本轮校准结论

本页当前已经具备：

- 完整的 tab 路由结构
- 页面壳层布局与响应式收口
- 未保存离开保护
- 项目设定 / 规则 / AI 偏好 / Skills / MCP / 审计 六个子页闭环

后续优化重点不应再放在“重写一套 token”或“把所有 tab 压成同一种窄表单”，而应聚焦：

- 项目设定分组语义化
- AI 偏好的继承状态可见性
- Skills / MCP 的移动端体验
- 审计过滤的人性化表达
