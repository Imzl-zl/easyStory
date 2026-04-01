# 项目设置页面 UI 改进实施指南

> 本文档经源码核查，已修正问题分级和解决方案。

## 快速总结

✅ **好消息**：你的设计文档与源码高度一致，**没有严重问题**！

🟡 **需澄清**：原文档中部分"问题"实为优化建议，且部分解决方案与当前设计方向冲突。

✅ **真实存在**：审计过滤器偏技术向、移动端体验可优化

---

## 涉及的页面与组件

本文档优化涉及 **1 个页面**的 **4 个组件/区域**：

| 标签页 | 涉及组件/区域 | 优化内容 |
|--------|--------------|---------|
| **项目设定（Setting）** | `project-setting-editor.tsx` | 字段分组语义化 |
| **审计（Audit）** | `ProjectAuditPanel` | 预设过滤项、文案优化 |
| **AI 偏好（Assistant）** | `AssistantPreferencesPanel` | 继承状态可见性 |
| **全局布局** | `project-settings-page.module.css` | 移动端折叠体验 |

---

## 一、需要修正的错误认知

### ❌ 错误认知 1：内容卡片需要添加 900px 限宽

**原文档声称**：
> 在超宽屏幕（> 1600px）上，内容卡片会无限扩展

**源码实际情况**：

`.contentCard`（`project-settings-page.module.css` 第 234-243 行）：
```css
.contentCard {
  position: relative;
  padding: 1.5rem;
  background: var(--bg-surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  /* 确实没有 max-width */
}
```

**但不需要修复**，因为：
1. `SectionCard` 内部已经有 `max-w-4xl`（约 896px）限制
2. 字段网格 `md:grid-cols-2` 自然限制了单行宽度
3. `project-settings-ui-redesign.md` 明确指出"不适合再对外层内容卡施加统一 `800px` 限宽"

**结论**：这不是问题，无需修复。

---

### ❌ 错误认知 2：Skills/MCP 间距与其它标签页不一致

**原文档声称**：
> Skills/MCP 的字段间距约为 0.75rem，不一致

**实际情况**：
- 原文档未提供具体源码位置
- `project-setting-editor.tsx` 中使用 `grid gap-5` (1.25rem)
- Skills/MCP 使用的是 `AssistantSkillsPanel` / `AssistantMcpPanel` 组件，内部结构不同

**结论**：缺少具体证据，问题存在性存疑。

---

## 二、真实存在的问题

### 🟡 问题 1：移动端 < 768px 布局可继续优化

**源码证据**：

当前 `project-settings-page.module.css` 第 297-325 行：
```css
@media (max-width: 767px) {
  .page {
    gap: 1rem;
    padding: 0.75rem;
  }

  .sidebarCard,
  .contentCard {
    padding: 1rem;
  }
  /* 侧栏仍然显示，只是尺寸缩小 */
}
```

**现状**：
- 侧栏不会隐藏，只会在小屏幕下排到内容区上方
- 当前设计方向是"侧栏不隐藏"

**优化建议**（可选，非必须）：

若要进一步优化，可考虑在 `<= 640px` 时将侧栏改为折叠式：
```css
@media (max-width: 640px) {
  .sidebar {
    /* 改为可折叠，而不是隐藏 */
  }
}
```

但这与 `project-settings-ui-redesign.md` 的设计方向可能冲突，实施前需确认。

---

## 三、优化建议（非问题）

以下内容不属于"审查报错"，而是可选的体验提升：

### 🟡 建议 1：增强项目设定字段分组的语义

**现状**（`project-setting-editor.tsx` 第 161-274 行）：
```tsx
<div className="grid gap-5 md:grid-cols-2">
  <ProjectSettingField label="题材">...</ProjectSettingField>
  <ProjectSettingField label="子题材">...</ProjectSettingField>
  {/* 四组字段平铺排列，没有视觉分组 */}
</div>
```

**当前结构**：
- 基本信息：题材、子题材、目标读者、整体语气
- 角色设定：主角姓名、主角身份
- 世界观：世界名称、力量体系
- 规模设定：目标字数、目标章节

**可选改进**：为四组短字段添加视觉分隔或 `fieldset/legend`

```html
<fieldset>
  <legend>基本信息</legend>
  <div className="grid gap-5 md:grid-cols-2">
    <ProjectSettingField label="题材">...</ProjectSettingField>
    {/* ... */}
  </div>
</fieldset>
```

**注意**：这不影响功能，属于语义化增强。

---

### 🟡 建议 2：改进审计页过滤器

**现状**（`ProjectAuditPanel`）：
- 过滤器是文本输入，需要用户知道事件名
- `actor`、`details` 等文案偏内部视角

**优化方向**：

1. 添加预设过滤项（不需要改后端，只改前端）：
```tsx
const presetFilters = [
  { label: '全部', value: null },
  { label: '项目更新', value: 'project.updated' },
  { label: '设置变更', value: 'project.setting' },
];
```

2. 优化字段文案：
```tsx
// 原来
<span>操作者: {actor}</span>

// 改进
<span>操作人: {actor}</span>
```

---

### 🟡 建议 3：AI 偏好的继承状态可见性

**现状**（`AssistantPreferencesPanel`）：
- "留空即继承个人设置"只体现在说明文案里
- 用户很难一眼看出自己是否正在继承默认值

**优化方向**：
- 在字段旁显示"当前值：继承个人偏好"或"当前值：[具体模型名]"
- 这是可见性优化，不需要改数据结构

---

## 四、已有实现，无需重复

### ✅ 动画已存在

源码证据（`project-settings-page.module.css` 第 352-358 行）：
```css
.sidebar {
  animation: slideInLeft 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.content {
  animation: fadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
```

---

### ✅ 加载态已实现

源码证据（`project-settings-content.tsx` 第 46-55 行）：
```tsx
<div className={styles.contentCard}>
  <div className={styles.loadingText}>
    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin opacity-50" />
    <span>正在加载项目设定...</span>
  </div>
</div>
```

---

### ✅ 响应式断点已实现

源码证据（`project-settings-page.module.css`）：
- `<= 1023px`：单列布局
- `<= 767px`：间距收紧

---

## 五、实施优先级

### P1 - 可选优化（非紧急）

- [ ] 为项目设定字段添加分组视觉分隔
- [ ] 审计页添加预设过滤项
- [ ] AI 偏好显示当前继承状态

### P2 - 低优先级

- [ ] 移动端侧栏折叠体验优化（需确认设计方向）
- [ ] 加载态骨架屏（当前 spinner 已可用）

---

## 六、测试清单

### 布局测试
- [ ] 桌面端（1920px）：布局正常
- [ ] 平板端（1024px）：单列布局正确
- [ ] 手机端（375px）：侧栏和内容区比例合适

### 交互测试
- [ ] 标签页切换：动画流畅
- [ ] 保存按钮：loading 状态正常
- [ ] 错误提示：AppNotice 正常显示

### 功能测试
- [ ] 项目设定：保存后完整度更新
- [ ] 规则：启用开关正常
- [ ] Skills/MCP：列表和编辑器正常
- [ ] 审计：过滤功能正常

---

## 七、涉及的文件位置

### 页面骨架文件

| 文件 | 职责 |
|------|------|
| `apps/web/src/app/workspace/project/[projectId]/settings/page.tsx` | 路由入口 |
| `apps/web/src/features/project-settings/components/project-settings-page.tsx` | 主页面、dirty state 管理 |
| `apps/web/src/features/project-settings/components/project-settings-page.module.css` | 页面骨架样式 |
| `apps/web/src/features/project-settings/components/project-settings-content.tsx` | 内容区容器 |
| `apps/web/src/features/project-settings/components/project-settings-sidebar.tsx` | 侧栏导航 |

### 各标签页文件

| 标签页 | 主组件 | 文件位置 |
|--------|--------|--------|
| 项目设定 | `ProjectSettingEditor` | `apps/web/src/features/studio/components/` |
| 规则 | `AssistantRulesEditor` | `apps/web/src/features/settings/components/` |
| AI偏好 | `AssistantPreferencesPanel` | `apps/web/src/features/settings/components/` |
| Skills | `AssistantSkillsPanel` | `apps/web/src/features/settings/components/` |
| MCP | `AssistantMcpPanel` | `apps/web/src/features/settings/components/` |
| 审计 | `ProjectAuditPanel` | `apps/web/src/features/project-settings/components/` |

### 全局共享组件

| 组件 | 文件位置 |
|------|--------|
| `ink-input`, `ink-textarea`, `ink-button` | `apps/web/src/app/globals.css` |
| `SectionCard`, `StatusBadge`, `EmptyState` | `apps/web/src/components/ui/` |
| `AppNotice`, `UnsavedChangesDialog` | `apps/web/src/components/ui/` |

## 八、结论

| 原文档声称 | 实际情况 |
|-----------|---------|
| 内容卡片宽度需限制 | ❌ 误报，设计已通过内部组件限制 |
| 间距不统一 | ❓ 缺少证据，存疑 |
| 移动端需隐藏侧栏 | ⚠️ 与当前设计方向冲突 |
| 加载态需改进 | ❌ 已有 spinner |
| 动画需添加 | ❌ 已有 fadeIn/slideInLeft |
| 字段分组需优化 | 🟡 优化建议，非问题 |
| 审计过滤器需优化 | ✅ 真实有价值建议 |

**总体评估**：页面基础扎实，主要问题在于原文档把优化建议包装成问题，且部分建议与设计方向冲突。
