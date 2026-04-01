# 项目设置页面 - 快速参考指南

## 🎯 一句话总结

项目设置页面是**1 个页面**，包含**6 个标签页**（通过 `?tab=xxx` 切换），共有 **20+ 个子组件**，采用 **280px 侧栏 + 1fr 内容区** 的双列布局。

---

## 📍 快速导航

### 我要找...

#### 页面入口
- **路由**：`/workspace/project/[projectId]/settings`
- **文件**：`apps/web/src/app/workspace/project/[projectId]/settings/page.tsx`
- **主组件**：`ProjectSettingsPage`

#### 页面骨架
- **侧栏**：`ProjectSettingsSidebar` → `project-settings-page.module.css`
- **内容区**：`ProjectSettingsContent` → `project-settings-page.module.css`
- **样式**：`project-settings-page.module.css`

#### 各标签页

| 标签页 | 主组件 | 文件位置 | 样式文件 |
|--------|--------|--------|--------|
| 项目设定 | `ProjectSettingEditor` | `apps/web/src/features/studio/components/` | `project-setting-editor.module.css` |
| 规则 | `AssistantRulesEditor` | `apps/web/src/features/settings/components/` | `assistant-rules-editor.module.css` |
| AI偏好 | `AssistantPreferencesPanel` | `apps/web/src/features/settings/components/` | `assistant-preferences-panel.module.css` |
| Skills | `AssistantSkillsPanel` | `apps/web/src/features/settings/components/` | `assistant-skills-panel.module.css` |
| MCP | `AssistantMcpPanel` | `apps/web/src/features/settings/components/` | `assistant-mcp-panel.module.css` |
| 审计 | `ProjectAuditPanel` | `apps/web/src/features/project-settings/components/` | `project-audit-panel.module.css` |

---

## 🔧 常见改进任务

### 任务 1：修改页面布局（宽度、间距、响应式）
**涉及文件**：
```
apps/web/src/features/project-settings/components/project-settings-page.module.css
```

**关键 CSS 类**：
- `.page` - 页面容器（grid 布局）
- `.sidebar` - 侧栏（sticky）
- `.content` - 内容区
- `.contentCard` - 内容卡片

**改进示例**：
```css
/* 添加内容卡片宽度限制 */
.contentCard {
  max-width: 900px;
  margin: 0 auto;
}

/* 优化移动端 */
@media (max-width: 640px) {
  .sidebar { display: none; }
}
```

---

### 任务 2：修改项目设定表单（字段、分组、验证）
**涉及文件**：
```
apps/web/src/features/studio/components/project-setting-editor.tsx
apps/web/src/features/studio/components/project-setting-editor.module.css
apps/web/src/features/studio/components/project-setting-field.tsx
```

**关键组件**：
- `ProjectSettingEditor` - 主编辑器
- `ProjectSettingField` - 单个字段
- `SectionCard` - 卡片容器

**改进示例**：
```tsx
// 添加字段分组
<fieldset>
  <legend>基础信息</legend>
  <div className={styles.fieldGroup}>
    <ProjectSettingField name="theme" />
    <ProjectSettingField name="subTheme" />
  </div>
</fieldset>
```

---

### 任务 3：修改规则编辑器（启用开关、文本域、字符统计）
**涉及文件**：
```
apps/web/src/features/settings/components/assistant-rules-editor.tsx
apps/web/src/features/settings/components/assistant-rules-editor.module.css
```

**关键组件**：
- `AssistantRulesEditor` - 规则编辑器

**改进示例**：
```tsx
// 添加字符统计
<div className={styles.charCount}>
  {content.length} / 5000 字符
</div>
```

---

### 任务 4：修改 AI 偏好表单（字段、继承状态提示）
**涉及文件**：
```
apps/web/src/features/settings/components/assistant-preferences-panel.tsx
apps/web/src/features/settings/components/assistant-preferences-form.tsx
apps/web/src/features/settings/components/assistant-preferences-form.module.css
```

**关键组件**：
- `AssistantPreferencesPanel` - 面板容器
- `AssistantPreferencesForm` - 表单

**改进示例**：
```tsx
// 添加继承状态提示
{!value && (
  <div className={styles.inheritanceHint}>
    ℹ️ 当前继承个人设置
  </div>
)}
```

---

### 任务 5：修改 Skills 面板（列表、编辑器、响应式）
**涉及文件**：
```
apps/web/src/features/settings/components/assistant-skills-panel.tsx
apps/web/src/features/settings/components/skills-list.tsx
apps/web/src/features/settings/components/skills-editor.tsx
apps/web/src/features/settings/components/assistant-skills-panel.module.css
```

**关键组件**：
- `AssistantSkillsPanel` - 面板容器
- `SkillsList` - 左侧列表
- `SkillsEditor` - 右侧编辑器

**改进示例**：
```css
/* 优化移动端 */
@media (max-width: 768px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    display: none;
  }
}
```

---

### 任务 6：修改 MCP 面板（与 Skills 类似）
**涉及文件**：
```
apps/web/src/features/settings/components/assistant-mcp-panel.tsx
apps/web/src/features/settings/components/mcp-list.tsx
apps/web/src/features/settings/components/mcp-editor.tsx
apps/web/src/features/settings/components/assistant-mcp-panel.module.css
```

**关键组件**：
- `AssistantMcpPanel` - 面板容器
- `McpList` - 左侧列表
- `McpEditor` - 右侧编辑器

---

### 任务 7：修改审计面板（过滤器、列表、详情）
**涉及文件**：
```
apps/web/src/features/project-settings/components/project-audit-panel.tsx
apps/web/src/features/project-settings/components/audit-event-list.tsx
apps/web/src/features/project-settings/components/audit-event-item.tsx
apps/web/src/features/project-settings/components/project-audit-panel.module.css
```

**关键组件**：
- `ProjectAuditPanel` - 面板容器
- `AuditEventList` - 事件列表
- `AuditEventItem` - 单个事件

**改进示例**：
```tsx
// 添加预设过滤项
const presets = [
  { label: '项目更新', value: 'project.updated' },
  { label: '所有操作', value: null },
];
```

---

## 🎨 全局共享组件速查

### 输入组件
```tsx
import { InkInput } from '@/components/ui/ink-input';
import { InkTextarea } from '@/components/ui/ink-textarea';
import { AppSelect } from '@/components/ui/app-select';
import { InkToggle } from '@/components/ui/ink-toggle';
import { InkButton } from '@/components/ui/ink-button';
```

### 容器组件
```tsx
import { SectionCard } from '@/components/ui/section-card';
import { PanelShell } from '@/components/ui/panel-shell';
```

### 状态组件
```tsx
import { StatusBadge } from '@/components/ui/status-badge';
import { EmptyState } from '@/components/ui/empty-state';
import { AppNotice } from '@/components/ui/app-notice';
```

---

## 📊 文件结构速查

### 项目设置页面文件树
```
apps/web/src/
├─ app/
│  ├─ workspace/project/[projectId]/settings/
│  │  └─ page.tsx                          # 路由入口
│  └─ globals.css                          # 全局样式
├─ features/
│  ├─ project-settings/
│  │  └─ components/
│  │     ├─ project-settings-page.tsx      # 主页面
│  │     ├─ project-settings-page.module.css
│  │     ├─ project-settings-sidebar.tsx
│  │     ├─ project-settings-content.tsx
│  │     ├─ project-settings-tab-button.tsx
│  │     ├─ project-settings-icons.tsx
│  │     ├─ project-audit-panel.tsx        # 审计面板
│  │     ├─ project-audit-panel.module.css
│  │     ├─ audit-event-list.tsx
│  │     ├─ audit-event-item.tsx
│  │     └─ ...
│  ├─ studio/
│  │  └─ components/
│  │     ├─ project-setting-editor.tsx     # 项目设定
│  │     ├─ project-setting-editor.module.css
│  │     ├─ project-setting-field.tsx
│  │     ├─ project-setting-impact-panel.tsx
│  │     └─ ...
│  └─ settings/
│     └─ components/
│        ├─ assistant-rules-editor.tsx     # 规则
│        ├─ assistant-rules-editor.module.css
│        ├─ assistant-preferences-panel.tsx # AI偏好
│        ├─ assistant-preferences-form.tsx
│        ├─ assistant-preferences-form.module.css
│        ├─ assistant-skills-panel.tsx     # Skills
│        ├─ skills-list.tsx
│        ├─ skills-editor.tsx
│        ├─ assistant-skills-panel.module.css
│        ├─ assistant-mcp-panel.tsx        # MCP
│        ├─ mcp-list.tsx
│        ├─ mcp-editor.tsx
│        ├─ assistant-mcp-panel.module.css
│        └─ ...
└─ components/
   └─ ui/
      ├─ ink-input.tsx
      ├─ ink-textarea.tsx
      ├─ app-select.tsx
      ├─ ink-toggle.tsx
      ├─ ink-button.tsx
      ├─ section-card.tsx
      ├─ status-badge.tsx
      ├─ empty-state.tsx
      ├─ code-block.tsx
      ├─ unsaved-changes-dialog.tsx
      └─ ...
```

---

## 🔄 常见工作流

### 工作流 1：修改页面布局
1. 打开 `project-settings-page.module.css`
2. 修改 `.page`、`.sidebar`、`.content`、`.contentCard` 的样式
3. 在各个断点测试（1920px、1024px、768px、640px）
4. 刷新浏览器查看效果

### 工作流 2：修改表单字段
1. 打开对应的组件文件（如 `project-setting-editor.tsx`）
2. 修改字段结构或样式
3. 打开对应的样式文件（如 `project-setting-editor.module.css`）
4. 调整 CSS 类
5. 在浏览器中测试

### 工作流 3：修改全局样式
1. 打开 `apps/web/src/app/globals.css`
2. 修改 CSS 变量（如 `--accent-primary`、`--text-primary`）
3. 所有使用这些变量的组件会自动更新
4. 刷新浏览器查看效果

### 工作流 4：添加新功能
1. 确定功能属于哪个标签页
2. 在对应的组件文件中添加代码
3. 在对应的样式文件中添加 CSS
4. 如果需要新的全局组件，在 `apps/web/src/components/ui/` 中创建
5. 测试各个断点的响应式效果

---

## 🐛 常见问题排查

### 问题 1：修改后样式没有生效
**可能原因**：
- CSS 模块没有被正确导入
- 类名拼写错误
- 浏览器缓存

**解决方案**：
1. 检查 `import styles from './xxx.module.css'`
2. 检查 `className={styles.xxx}` 的拼写
3. 清除浏览器缓存或使用 Ctrl+Shift+R 强制刷新

### 问题 2：响应式布局在某个断点不工作
**可能原因**：
- 媒体查询的断点值不对
- CSS 优先级问题
- 父容器的约束

**解决方案**：
1. 检查媒体查询的断点值（1024px、768px、640px）
2. 使用浏览器开发者工具检查实际应用的样式
3. 检查是否有其他 CSS 规则覆盖了你的修改

### 问题 3：表单字段高度不一致
**可能原因**：
- 不同的输入组件有不同的默认高度
- 没有使用统一的间距规范

**解决方案**：
1. 检查 `ink-input`、`ink-textarea`、`AppSelect` 的高度定义
2. 在全局样式中定义统一的高度变量
3. 在各个组件中使用这些变量

### 问题 4：移动端布局显示不正确
**可能原因**：
- 没有添加移动端媒体查询
- 移动端的间距或字体大小不合适

**解决方案**：
1. 在 `project-settings-page.module.css` 中添加 `@media (max-width: 640px)` 规则
2. 调整移动端的间距、字体大小、按钮尺寸
3. 在真实手机上测试

---

## 📚 相关文档

- **设计规范**：`docs/ui/project-settings-ui-redesign.md`
- **布局分析**：`docs/ui/project-settings-ui-analysis.md`
- **改进指南**：`docs/ui/project-settings-ui-improvements.md`
- **组件映射**：`docs/ui/project-settings-component-map.md`（本文件）
- **全局设计**：`docs/ui/ui-design.md`

---

## 🎯 下一步

1. **立即改进**（1-2 天）
   - [ ] 添加内容卡片宽度限制
   - [ ] 统一表单字段间距
   - [ ] 优化移动端 < 640px 布局

2. **重要改进**（3-5 天）
   - [ ] 增强字段分组语义
   - [ ] 改进加载态
   - [ ] 增强可访问性

3. **体验优化**（5-7 天）
   - [ ] 优化审计页过滤器
   - [ ] 添加微交互动画
   - [ ] 完整的视觉回归测试

