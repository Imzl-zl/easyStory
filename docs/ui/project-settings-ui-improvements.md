# 项目设置页面 UI 改进实施指南

> 本文档经源码核查，已修正问题分级和解决方案。

## 快速总结

✅ **好消息**：你的设计文档与源码高度一致，**没有严重问题**！

🟡 **需澄清**：原文档中部分"问题"实为优化建议，且部分解决方案与当前设计方向冲突。

✅ **真实存在**：审计过滤器偏技术向、移动端体验可优化

---

## 涉及的页面与组件

本文档优化涉及 **1 个页面**的 **4 个组件/区域**：

| 标签页 | 涉及组件/区域 | 优化内容 | 优先级 |
|--------|--------------|---------|--------|
| **审计（Audit）** | `project-audit-panel.tsx` | 预设过滤标签 + 文案优化 | ⭐⭐⭐ 最优先 |
| **项目设定（Setting）** | `project-setting-editor.tsx` | 字段分组语义化 | 🟡 可选 |
| **AI 偏好（Assistant）** | `AssistantPreferencesPanel` | 继承状态可见性 | 🟡 可选 |
| **全局布局** | `project-settings-page.module.css` | 移动端折叠体验 | ⚠️ 需确认方向 |

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

### 🟡 建议 2：改进审计页过滤器（最实用）

**现状**（`project-audit-panel.tsx` 第 95-100 行）：
```tsx
<input
  className="ink-input"
  placeholder="如 project.updated / project.setting.updated"
  value={draftEventType}
/>
```

第 183 行显示：`actor: {item.actor_user_id} · details: {summarize...}`

**问题**：
1. 过滤器是纯文本输入，`placeholder` 里写着技术术语，普通用户看不懂
2. `actor`、`details` 等术语对用户不友好

**优化方案**：

1. **添加预设过滤标签**（改动最小）：
```tsx
// 在输入框上方添加预设标签
<div className="flex flex-wrap gap-2">
  {[
    { label: '项目更新', value: 'project.updated' },
    { label: '设置变更', value: 'project.setting.updated' },
    { label: '成员变动', value: 'project.member' },
  ].map(preset => (
    <button
      key={preset.value}
      className="ink-tab"
      onClick={() => onChange(preset.value)}
    >
      {preset.label}
    </button>
  ))}
</div>
```

2. **优化文案**：
```tsx
// 原来（第183行）
<p className="text-sm text-[var(--text-secondary)]">
  actor: {item.actor_user_id ?? "system"} · details: {summarizeProjectAuditDetails(item.details)}
</p>

// 改进
<p className="text-sm text-[var(--text-secondary)]">
  操作人: {item.actor_user_id ?? "系统"} · 详情: {summarizeProjectAuditDetails(item.details)}
</p>
```

**影响范围**：
- 仅涉及 `project-audit-panel.tsx` 一个文件
- 不需要改后端接口
- 预设标签可后续扩展

---

### 🟡 建议 3：AI 偏好的"幽灵占位符"（最实用）

**现状**（`AssistantPreferencesPanel`）：
- "留空即继承个人设置"只体现在说明文案里
- 用户很难一眼看出自己是否正在继承默认值

**优化方案**：动态 placeholder 显示继承值

```tsx
// 原来（固定 placeholder）
<input
  className="ink-input"
  placeholder="输入模型名称，如 gpt-4o"
/>

// 改进（幽灵占位符）
<input
  className="ink-input"
  placeholder={inheritedValue ? `当前继承：${inheritedValue}` : "输入模型名称"}
  value={inputValue}
  onChange={e => setInputValue(e.target.value)}
/>
```

**效果**：用户看到 "当前继承：GPT-4o" 会有安全感；开始输入后 placeholder 消失，进入自定义模式。

---

### 🟡 建议 4：Dirty Tab 未保存圆点（最实用）

**现状**：
- dirty state 按 tab 维护，但侧栏 tab 没有视觉提示
- 用户必须点进去或触发拦截弹窗才知道有未保存内容

**优化方案**：在侧栏 tab 旁显示微小圆点

```tsx
// project-settings-sidebar.tsx
{tabs.map(tab => (
  <button
    key={tab.id}
    className={cn("tab-button", { active: tab.id === currentTab })}
  >
    {tab.label}
    {dirtyState[tab.id] && (
      <span className="dirty-dot" aria-label="有未保存的更改" />
    )}
  </button>
))}
```

```css
/* project-settings-page.module.css */
.dirty-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--accent-warning);
  margin-left: 4px;
  vertical-align: middle;
}
```

**影响范围**：`project-settings-sidebar.tsx` + 样式文件

---

### 🟡 建议 5：编辑器文本容器 65ch 限宽

**现状**（Skills/MCP 编辑器）：
- 右侧编辑器内容过少时，文本行过长，阅读困难

**优化方案**：为编辑器文本容器设置 max-width

```css
/* skills-editor.module.css / mcp-editor.module.css */
.editor-content {
  max-width: 65ch; /* 约 80-100 个字符 */
  margin-left: auto;
  margin-right: auto;
}
```

**效果**：保持卡片宽度灵活，但文本阅读宽度固定在舒适范围。

---

### 🟡 建议 6：全宽文本域聚焦 glow 效果

**现状**：
- 项目设定的 3 个全宽文本域（核心冲突、剧情走向、特殊要求）是"重度思考"项
- 聚焦时没有视觉引导

**优化方案**：聚焦时给外层 SectionCard 微弱的 glow

```css
/* project-setting-editor.module.css */
.section-card {
  transition: box-shadow 0.2s ease;
}

.section-card:focus-within {
  box-shadow: 0 0 0 3px rgba(90, 122, 107, 0.15);
}
```

**效果**：帮助用户进入沉浸式写作状态。

---

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

## 六、实施优先级

### ⭐ 最优先（可立即实施）

- [ ] **审计页预设过滤标签**：在输入框上方添加"项目更新"、"设置变更"、"成员变动"等预设标签
- [ ] **审计页文案优化**：`actor` → `操作人`，`details` → `详情`，`system` → `系统`
- [ ] **幽灵占位符**：AI 偏好 input 动态显示 "当前继承：xxx"
- [ ] **Dirty Tab 圆点**：侧栏 tab 旁显示未保存橙色圆点

### P1 - 可选优化

- [ ] 项目设定字段分组语义化（fieldset/legend）
- [ ] 编辑器 65ch 限宽（Skills/MCP）
- [ ] 全宽文本域聚焦 glow 效果

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
