# 项目设置页面 - 完整组件映射表

## 📍 页面路由

| 路由 | 页面名称 | 文件位置 |
|------|--------|--------|
| `/workspace/project/[projectId]/settings` | 项目设置页 | `apps/web/src/app/workspace/project/[projectId]/settings/page.tsx` |

---

## 🏗️ 页面骨架组件

### 主容器
| 组件 | 文件位置 | 职责 | 样式文件 |
|------|--------|------|--------|
| `ProjectSettingsPage` | `apps/web/src/features/project-settings/components/project-settings-page.tsx` | 页面入口、路由管理、dirty state 管理、未保存保护 | `project-settings-page.module.css` |
| `ProjectSettingsSidebar` | `apps/web/src/features/project-settings/components/project-settings-sidebar.tsx` | 左侧导航栏、项目信息、标签页按钮 | `project-settings-page.module.css` |
| `ProjectSettingsContent` | `apps/web/src/features/project-settings/components/project-settings-content.tsx` | 内容区容器、tab 路由分发 | `project-settings-page.module.css` |

### 辅助组件
| 组件 | 文件位置 | 职责 |
|------|--------|------|
| `ProjectSettingsTabButton` | `apps/web/src/features/project-settings/components/project-settings-tab-button.tsx` | 单个标签页按钮 |
| `ProjectSettingsIcons` | `apps/web/src/features/project-settings/components/project-settings-icons.tsx` | 图标集合 |
| `UnsavedChangesDialog` | `apps/web/src/components/ui/unsaved-changes-dialog.tsx` | 未保存提示对话框 |

---

## 📑 各标签页内容组件详细映射

**说明**：以下 6 个标签页都在同一个项目设置页面内，通过 `?tab=xxx` 参数切换。

### 1️⃣ 项目设定（Setting Tab）

#### 页面结构
```
ProjectSettingsPage
  └─ ProjectSettingsContent
      └─ contentCard (CSS 容器)
          └─ ProjectSettingEditor
```

#### 组件详情

| 组件 | 文件位置 | 职责 | 依赖组件 |
|------|--------|------|--------|
| `ProjectSettingEditor` | `apps/web/src/features/studio/components/project-setting-editor.tsx` | 项目设定编辑表单 | `ProjectSettingField`, `SectionCard`, `ProjectSettingImpactPanel` |
| `ProjectSettingField` | `apps/web/src/features/studio/components/project-setting-field.tsx` | 单个设定字段 | `ink-input`, `ink-textarea`, `ink-select` |
| `ProjectSettingImpactPanel` | `apps/web/src/features/studio/components/project-setting-impact-panel.tsx` | 保存成功后的影响提示 | - |
| `SectionCard` | `apps/web/src/components/ui/section-card.tsx` | 卡片容器（全局共享） | - |

#### 字段结构
```
ProjectSettingEditor
  ├─ 完整度摘要卡
  │  ├─ StatusBadge
  │  └─ 完整度百分比
  ├─ 基础信息分组
  │  ├─ 题材 (ProjectSettingField)
  │  ├─ 子题材 (ProjectSettingField)
  │  ├─ 目标读者 (ProjectSettingField)
  │  └─ 整体语气 (ProjectSettingField)
  ├─ 角色设定分组
  │  ├─ 主角姓名 (ProjectSettingField)
  │  └─ 主角身份 (ProjectSettingField)
  ├─ 世界观分组
  │  ├─ 世界名称 (ProjectSettingField)
  │  └─ 力量体系 (ProjectSettingField)
  ├─ 规模分组
  │  ├─ 目标字数 (ProjectSettingField)
  │  └─ 目标章节 (ProjectSettingField)
  ├─ 核心冲突 (全宽文本域)
  ├─ 剧情走向 (全宽文本域)
  ├─ 特殊要求 (全宽文本域)
  └─ 操作按钮
     ├─ 完整度检查
     └─ 保存设定
```

#### 样式文件
- `apps/web/src/features/studio/components/project-setting-editor.module.css`
- `apps/web/src/features/studio/components/project-setting-field.module.css`

#### 关键 CSS 类
- `.editor` - 编辑器容器
- `.fieldGrid` - 字段网格（md:grid-cols-2）
- `.fieldFull` - 全宽字段
- `.completenessCard` - 完整度卡片

---

### 2️⃣ 规则（Rules Tab）

#### 页面结构
```
ProjectSettingsPage
  └─ ProjectSettingsContent
      └─ contentCard (CSS 容器)
          └─ AssistantRulesEditor
```

#### 组件详情

| 组件 | 文件位置 | 职责 | 依赖组件 |
|------|--------|------|--------|
| `AssistantRulesEditor` | `apps/web/src/features/settings/components/assistant-rules-editor.tsx` | 规则编辑器 | `ink-textarea`, `ink-button`, `ink-toggle` |

#### 字段结构
```
AssistantRulesEditor
  ├─ 标题: "项目长期规则"
  ├─ 描述文案
  ├─ 启用开关 (ink-toggle)
  ├─ 规则内容 (ink-textarea)
  │  └─ 占满整行，min-height: 200px
  ├─ 字符统计 (可选)
  └─ 操作按钮
     ├─ 保存规则
     └─ 还原
```

#### 样式文件
- `apps/web/src/features/settings/components/assistant-rules-editor.module.css`

#### 关键 CSS 类
- `.editor` - 编辑器容器
- `.textarea` - 文本域
- `.actions` - 操作按钮组

#### Props
```typescript
{
  scope: "project",           // 项目层规则
  title: "项目长期规则",
  description: "只影响这个项目里的聊天和创作建议...",
  onDirtyChange: (isDirty) => void,
  projectId: string
}
```

---

### 3️⃣ AI 偏好（Assistant Tab）

#### 页面结构
```
ProjectSettingsPage
  └─ ProjectSettingsContent
      └─ contentCard (CSS 容器)
          └─ AssistantPreferencesPanel
              └─ AssistantPreferencesForm
```

#### 组件详情

| 组件 | 文件位置 | 职责 | 依赖组件 |
|------|--------|------|--------|
| `AssistantPreferencesPanel` | `apps/web/src/features/settings/components/assistant-preferences-panel.tsx` | AI 偏好面板容器 | `AssistantPreferencesForm` |
| `AssistantPreferencesForm` | `apps/web/src/features/settings/components/assistant-preferences-form.tsx` | AI 偏好表单 | `ink-select`, `ink-input`, `ink-button` |

#### 字段结构
```
AssistantPreferencesPanel
  ├─ 标题: "项目 AI 偏好"
  ├─ 描述文案
  └─ AssistantPreferencesForm
      ├─ 默认连接 (ink-select)
      │  └─ 选项来自项目凭证 + 用户凭证
      ├─ 默认模型 (ink-input)
      │  └─ 例如: gpt-4.1-mini
      ├─ 默认单次回复上限 (ink-input)
      │  └─ 数字输入
      └─ 操作按钮
         ├─ 保存设置
         └─ 还原
```

#### 样式文件
- `apps/web/src/features/settings/components/assistant-preferences-panel.module.css`
- `apps/web/src/features/settings/components/assistant-preferences-form.module.css`

#### 关键 CSS 类
- `.panel` - 面板容器
- `.form` - 表单容器（xl:grid-cols-3）
- `.field` - 字段容器
- `.actions` - 操作按钮组

#### Props
```typescript
{
  scope: "project",           // 项目层偏好
  onDirtyChange: (isDirty) => void,
  projectId: string
}
```

#### 特殊逻辑
- 字段留空 = 继承个人设置
- 项目凭证优先级 > 用户凭证
- 需要同时加载两层凭证

---

### 4️⃣ Skills（Skills Tab）

#### 页面结构
```
ProjectSettingsPage
  └─ ProjectSettingsContent
      └─ contentCard (CSS 容器)
          └─ AssistantSkillsPanel
              ├─ SkillsList (左侧)
              └─ SkillsEditor (右侧)
```

#### 组件详情

| 组件 | 文件位置 | 职责 | 依赖组件 |
|------|--------|------|--------|
| `AssistantSkillsPanel` | `apps/web/src/features/settings/components/assistant-skills-panel.tsx` | Skills 面板容器 | `SkillsList`, `SkillsEditor` |
| `SkillsList` | `apps/web/src/features/settings/components/skills-list.tsx` | Skills 列表（左侧） | `SkillsListItem` |
| `SkillsListItem` | `apps/web/src/features/settings/components/skills-list-item.tsx` | 单个 Skill 项 | - |
| `SkillsEditor` | `apps/web/src/features/settings/components/skills-editor.tsx` | Skills 编辑器（右侧） | `ink-input`, `ink-textarea`, `ink-toggle` |

#### 布局结构
```
AssistantSkillsPanel
  ├─ 标题: "项目 Skills"
  ├─ 描述文案
  ├─ 统计信息: "已启用 0 个，共 0 个"
  ├─ 新建按钮
  └─ 两栏布局 (xl:grid-cols-[280px_1fr])
      ├─ 左侧 (sticky, xl:sticky)
      │  └─ SkillsList
      │      ├─ SkillsListItem (可选中)
      │      ├─ SkillsListItem
      │      └─ ...
      └─ 右侧
          └─ SkillsEditor
              ├─ 编辑方式选择 (SKILL.md / 可视化)
              ├─ 名称 (ink-input)
              ├─ 一句说明 (ink-textarea)
              ├─ 启用开关 (ink-toggle)
              ├─ 保存的文件显示
              └─ 操作按钮
                 ├─ 保存设置
                 └─ 还原
```

#### 样式文件
- `apps/web/src/features/settings/components/assistant-skills-panel.module.css`
- `apps/web/src/features/settings/components/skills-list.module.css`
- `apps/web/src/features/settings/components/skills-editor.module.css`

#### 关键 CSS 类
- `.panel` - 面板容器
- `.layout` - 两栏布局
- `.sidebar` - 左侧列表（xl:sticky）
- `.editor` - 右侧编辑器
- `.listItem` - 列表项
- `.listItemActive` - 激活状态

#### Props
```typescript
{
  scope: "project",           // 项目层 Skills
  onDirtyChange: (isDirty) => void,
  projectId: string
}
```

#### 特殊逻辑
- 内部维护自己的 dirty state
- 左侧列表在 xl 下 sticky
- 支持新建、编辑、删除
- 编辑方式可切换（SKILL.md / 可视化）

---

### 5️⃣ MCP（MCP Tab）

#### 页面结构
```
ProjectSettingsPage
  └─ ProjectSettingsContent
      └─ contentCard (CSS 容器)
          └─ AssistantMcpPanel
              ├─ McpList (左侧)
              └─ McpEditor (右侧)
```

#### 组件详情

| 组件 | 文件位置 | 职责 | 依赖组件 |
|------|--------|------|--------|
| `AssistantMcpPanel` | `apps/web/src/features/settings/components/assistant-mcp-panel.tsx` | MCP 面板容器 | `McpList`, `McpEditor` |
| `McpList` | `apps/web/src/features/settings/components/mcp-list.tsx` | MCP 列表（左侧） | `McpListItem` |
| `McpListItem` | `apps/web/src/features/settings/components/mcp-list-item.tsx` | 单个 MCP 项 | - |
| `McpEditor` | `apps/web/src/features/settings/components/mcp-editor.tsx` | MCP 编辑器（右侧） | `ink-input`, `ink-textarea`, `ink-toggle` |

#### 布局结构
```
AssistantMcpPanel
  ├─ 标题: "项目 MCP"
  ├─ 描述文案
  ├─ 统计信息: "已启用 0 个，共 0 个"
  ├─ 新建按钮
  └─ 两栏布局 (xl:grid-cols-[280px_1fr])
      ├─ 左侧 (sticky, xl:sticky)
      │  └─ McpList
      │      ├─ McpListItem (可选中)
      │      ├─ McpListItem
      │      └─ ...
      └─ 右侧
          └─ McpEditor
              ├─ 编辑方式选择 (MCPyaml / 可视化)
              ├─ 名称 (ink-input)
              ├─ 一句说明 (ink-textarea)
              ├─ 启用开关 (ink-toggle)
              ├─ 地址 (ink-input)
              ├─ 超时 (ink-input)
              └─ 操作按钮
                 ├─ 保存设置
                 └─ 还原
```

#### 样式文件
- `apps/web/src/features/settings/components/assistant-mcp-panel.module.css`
- `apps/web/src/features/settings/components/mcp-list.module.css`
- `apps/web/src/features/settings/components/mcp-editor.module.css`

#### 关键 CSS 类
- `.panel` - 面板容器
- `.layout` - 两栏布局
- `.sidebar` - 左侧列表（xl:sticky）
- `.editor` - 右侧编辑器
- `.listItem` - 列表项
- `.listItemActive` - 激活状态

#### Props
```typescript
{
  scope: "project",           // 项目层 MCP
  onDirtyChange: (isDirty) => void,
  projectId: string
}
```

#### 特殊逻辑
- 结构与 Skills 基本一致
- 内部维护自己的 dirty state
- 左侧列表在 xl 下 sticky
- 支持新建、编辑、删除

---

### 6️⃣ 审计（Audit Tab）

#### 页面结构
```
ProjectSettingsPage
  └─ ProjectSettingsContent
      └─ contentCard (CSS 容器)
          └─ ProjectAuditPanel
              ├─ 过滤器
              └─ 审计记录列表
```

#### 组件详情

| 组件 | 文件位置 | 职责 | 依赖组件 |
|------|--------|------|--------|
| `ProjectAuditPanel` | `apps/web/src/features/project-settings/components/project-audit-panel.tsx` | 审计面板 | `AuditEventList`, `AuditEventDetail` |
| `AuditEventList` | `apps/web/src/features/project-settings/components/audit-event-list.tsx` | 审计事件列表 | `AuditEventItem` |
| `AuditEventItem` | `apps/web/src/features/project-settings/components/audit-event-item.tsx` | 单个审计事件 | - |
| `AuditEventDetail` | `apps/web/src/features/project-settings/components/audit-event-detail.tsx` | 审计事件详情 | `CodeBlock` |

#### 布局结构
```
ProjectAuditPanel
  ├─ 标题: "操作记录"
  ├─ 描述文案
  ├─ 过滤器
  │  ├─ 事件类型输入框 (ink-input)
  │  ├─ 应用过滤按钮
  │  └─ 清空按钮
  ├─ 加载态 / 错误态 / 空状态
  └─ 审计记录列表
      ├─ AuditEventItem (卡片)
      │  ├─ 时间
      │  ├─ 操作类型
      │  ├─ 操作者
      │  └─ 展开按钮
      ├─ AuditEventItem
      └─ ...
      
  展开后显示:
  └─ AuditEventDetail
      ├─ 完整操作信息
      └─ CodeBlock (JSON 详情)
```

#### 样式文件
- `apps/web/src/features/project-settings/components/project-audit-panel.module.css`
- `apps/web/src/features/project-settings/components/audit-event-list.module.css`
- `apps/web/src/features/project-settings/components/audit-event-item.module.css`

#### 关键 CSS 类
- `.panel` - 面板容器
- `.filter` - 过滤器容器
- `.list` - 列表容器
- `.item` - 列表项
- `.itemExpanded` - 展开状态
- `.detail` - 详情容器

#### Props
```typescript
{
  projectId: string,
  eventType: string | null,
  onEventTypeChange: (eventType: string | null) => void
}
```

#### 特殊逻辑
- 无编辑态，不参与 dirty state
- 支持事件类型过滤
- 支持展开/收起详情
- 详情通过 CodeBlock 展示 JSON

---

## 🎨 全局共享组件

### 输入组件
| 组件 | 文件位置 | 用途 |
|------|--------|------|
| `ink-input` | `apps/web/src/components/ui/ink-input.tsx` | 文本输入框 |
| `ink-textarea` | `apps/web/src/components/ui/ink-textarea.tsx` | 文本域 |
| `ink-select` / `AppSelect` | `apps/web/src/components/ui/app-select.tsx` | 下拉选择 |
| `ink-toggle` | `apps/web/src/components/ui/ink-toggle.tsx` | 开关 |
| `ink-button` | `apps/web/src/components/ui/ink-button.tsx` | 主按钮 |
| `ink-button-secondary` | `apps/web/src/components/ui/ink-button-secondary.tsx` | 次按钮 |

### 容器组件
| 组件 | 文件位置 | 用途 |
|------|--------|------|
| `SectionCard` | `apps/web/src/components/ui/section-card.tsx` | 卡片容器 |
| `panel-shell` | `apps/web/src/components/ui/panel-shell.tsx` | 面板壳层 |
| `panel-muted` | `apps/web/src/components/ui/panel-muted.tsx` | 静音面板 |

### 状态组件
| 组件 | 文件位置 | 用途 |
|------|--------|------|
| `StatusBadge` | `apps/web/src/components/ui/status-badge.tsx` | 状态徽章 |
| `EmptyState` | `apps/web/src/components/ui/empty-state.tsx` | 空状态 |
| `AppNotice` | `apps/web/src/components/ui/app-notice.tsx` | 通知提示 |

### 其他组件
| 组件 | 文件位置 | 用途 |
|------|--------|------|
| `CodeBlock` | `apps/web/src/components/ui/code-block.tsx` | 代码块展示 |
| `UnsavedChangesDialog` | `apps/web/src/components/ui/unsaved-changes-dialog.tsx` | 未保存提示 |

---

## 📊 样式文件总览

### 页面级样式
```
apps/web/src/features/project-settings/components/
├─ project-settings-page.module.css          # 页面骨架、侧栏、内容区
├─ project-settings-sidebar.module.css       # 侧栏样式（可能合并到上面）
└─ project-settings-content.module.css       # 内容区样式（可能合并到上面）
```

### 标签页组件样式
```
apps/web/src/features/studio/components/
├─ project-setting-editor.module.css
└─ project-setting-field.module.css

apps/web/src/features/settings/components/
├─ assistant-rules-editor.module.css
├─ assistant-preferences-panel.module.css
├─ assistant-preferences-form.module.css
├─ assistant-skills-panel.module.css
├─ skills-list.module.css
├─ skills-editor.module.css
├─ assistant-mcp-panel.module.css
├─ mcp-list.module.css
└─ mcp-editor.module.css

apps/web/src/features/project-settings/components/
├─ project-audit-panel.module.css
├─ audit-event-list.module.css
└─ audit-event-item.module.css
```

### 全局样式
```
apps/web/src/app/
└─ globals.css                               # 全局 CSS 变量、设计 token
```

---

## 🔄 数据流向

### 状态管理
```
ProjectSettingsPage (主状态管理)
├─ projectSettingDirty (setting tab)
├─ projectRulesDirty (rules tab)
├─ projectPreferencesDirty (assistant tab)
├─ projectSkillsDirty (skills tab)
├─ projectMcpDirty (mcp tab)
└─ 各子组件通过 onDirtyChange 回调更新

各子组件 (内部状态)
├─ ProjectSettingEditor (内部 dirty state)
├─ AssistantRulesEditor (内部 dirty state)
├─ AssistantSkillsPanel (内部 dirty state)
├─ AssistantMcpPanel (内部 dirty state)
└─ ProjectAuditPanel (无编辑态)
```

### 路由参数
```
URL: /workspace/project/[projectId]/settings?tab=setting&event=null

Query 参数:
├─ tab: setting | rules | assistant | skills | mcp | audit
└─ event: 审计事件类型（仅 audit tab 使用）
```

---

## 🎯 改进建议映射

| 改进项 | 涉及组件 | 涉及文件 |
|--------|--------|--------|
| 内容卡片宽度限制 | `ProjectSettingsContent` | `project-settings-page.module.css` |
| 表单字段间距统一 | 所有表单组件 | 各组件 `.module.css` |
| 移动端 < 640px 优化 | `ProjectSettingsPage` | `project-settings-page.module.css` |
| 字段分组语义化 | `ProjectSettingEditor` | `project-setting-editor.module.css` |
| 加载态改进 | `ProjectSettingsContent` | `project-settings-page.module.css` |
| 可访问性增强 | 所有组件 | 各组件 `.tsx` |
| 审计过滤优化 | `ProjectAuditPanel` | `project-audit-panel.module.css` |
| 微交互动画 | `ProjectSettingsPage` | `project-settings-page.module.css` |

---

## 📝 组件清单

## 📊 完整的组件清单

### 总计
- **页面**：1 个（ProjectSettingsPage）
- **骨架组件**：3 个（侧栏、内容区、标签页按钮）
- **标签页**：6 个
- **标签页内容组件**：18 个
- **全局共享组件**：15+ 个
- **样式文件**：20+ 个

### 按类型分类
- **页面容器组件**：1 个（ProjectSettingsPage）
- **骨架组件**：3 个（侧栏、内容区、标签页按钮）
- **标签页内容组件**：6 个标签页，共 18 个子组件
- **全局共享组件**：15+ 个
- **样式文件**：20+ 个

