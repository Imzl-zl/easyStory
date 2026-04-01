# 项目设置页面 UI 改进实施指南

## 快速总结

✅ **好消息**：你的设计文档与源码高度一致，**没有明显走样**！

⚠️ **改进空间**：3 个高优先级问题 + 5 个中低优先级建议

---

## 问题 1：内容卡片宽度未限制 🔴 高优先级

### 问题描述
在超宽屏幕（> 1600px）上，内容卡片会无限扩展，导致：
- 文本行过长，阅读困难
- 表单字段过宽，输入体验差
- 与设计规范中的"800px 限宽"不符

### 当前代码
```css
.contentCard {
  position: relative;
  padding: 1.5rem;
  background: var(--bg-surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-lg);
  /* 没有 max-width */
}
```

### 改进方案
```css
.contentCard {
  position: relative;
  padding: 1.5rem;
  background: var(--bg-surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-lg);
  max-width: 900px;  /* 添加这一行 */
  margin: 0 auto;    /* 添加这一行 */
  width: 100%;       /* 添加这一行 */
}
```

### 为什么是 900px？
- 文本最佳阅读宽度：65-75 个字符 ≈ 600-800px
- 加上表单字段和间距：900px 是合理的上限
- 与设计规范中的建议一致

### 实施步骤
1. 打开 `apps/web/src/features/project-settings/components/project-settings-page.module.css`
2. 在 `.contentCard` 规则中添加上述三行
3. 在各个断点处测试（1024px、768px、640px）

---

## 问题 2：各标签页表单字段间距不统一 🔴 高优先级

### 问题描述
- Skills/MCP 的字段间距与其他标签页不一致
- 导致视觉不统一，用户体验割裂

### 当前情况
```
项目设定：字段间距 ≈ 1rem
规则：字段间距 ≈ 1.5rem
AI偏好：字段间距 ≈ 1rem
Skills：字段间距 ≈ 0.75rem（不一致！）
MCP：字段间距 ≈ 0.75rem（不一致！）
```

### 改进方案

#### 方案 A：建立全局表单字段间距规范
在 `globals.css` 中添加：
```css
:root {
  --form-field-gap: 1rem;      /* 字段间距 */
  --form-section-gap: 1.5rem;  /* 分组间距 */
  --form-group-gap: 0.5rem;    /* 组内间距 */
}
```

#### 方案 B：创建表单字段容器组件
```css
.formFieldGroup {
  display: flex;
  flex-direction: column;
  gap: var(--form-field-gap);
}

.formFieldGroup--section {
  gap: var(--form-section-gap);
  padding-bottom: var(--form-section-gap);
  border-bottom: 1px solid var(--line-soft);
}

.formFieldGroup--section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
```

#### 方案 C：统一各组件的间距
在各个组件中使用统一的间距：
```css
/* AssistantSkillsPanel 中 */
.skillsForm {
  display: flex;
  flex-direction: column;
  gap: var(--form-field-gap);
}

/* AssistantMcpPanel 中 */
.mcpForm {
  display: flex;
  flex-direction: column;
  gap: var(--form-field-gap);
}
```

### 实施步骤
1. 在 `globals.css` 中定义表单间距变量
2. 在各个组件中使用这些变量
3. 进行视觉回归测试

---

## 问题 3：移动端 < 640px 的布局优化 🔴 高优先级

### 问题描述
在手机屏幕上（< 640px）：
- 侧栏占用过多空间
- 内容区域被压缩
- 用户体验不佳

### 当前代码
```css
@media (max-width: 767px) {
  .page {
    gap: 1rem;
    padding: 0.75rem;
  }
  /* 侧栏仍然显示 */
}
```

### 改进方案

#### 方案 A：隐藏侧栏（推荐）
```css
@media (max-width: 640px) {
  .page {
    grid-template-columns: 1fr;
  }
  
  .sidebar {
    display: none;
  }
  
  .content {
    width: 100%;
  }
}
```

#### 方案 B：改为抽屉式侧栏
```css
@media (max-width: 640px) {
  .sidebar {
    position: fixed;
    left: -280px;
    top: 0;
    width: 280px;
    height: 100vh;
    background: var(--bg-surface);
    border-right: 1px solid var(--line-soft);
    transition: left 0.3s ease;
    z-index: 100;
  }
  
  .sidebar.open {
    left: 0;
  }
}
```

#### 方案 C：改为底部标签栏
```css
@media (max-width: 640px) {
  .page {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr auto;
    padding-bottom: 0;
  }
  
  .sidebar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    height: auto;
    border-top: 1px solid var(--line-soft);
    border-radius: 0;
  }
  
  .tabList {
    flex-direction: row;
    overflow-x: auto;
  }
}
```

### 推荐方案
**方案 A（隐藏侧栏）** 最简单，用户可以通过顶部导航返回。

### 实施步骤
1. 在 `project-settings-page.module.css` 中添加 `@media (max-width: 640px)` 规则
2. 选择合适的方案实施
3. 在真实手机上测试

---

## 建议 1：增强字段分组的语义 🟡 中优先级

### 当前问题
项目设定页面的字段是平铺排列的，没有明确的分组：
```
题材、子题材、目标读者、整体语气
主角姓名、主角身份
世界名称、力量体系
目标字数、目标章节
```

### 改进方案

#### 方案 A：使用 fieldset + legend
```html
<fieldset>
  <legend>基础信息</legend>
  <div class="formFieldGroup">
    <input name="theme" />
    <input name="subTheme" />
  </div>
</fieldset>

<fieldset>
  <legend>角色设定</legend>
  <div class="formFieldGroup">
    <input name="characterName" />
    <input name="characterRole" />
  </div>
</fieldset>
```

#### 方案 B：使用卡片分组
```html
<div class="formSection">
  <h3 class="formSectionTitle">📋 基础信息</h3>
  <div class="formFieldGroup">
    <input name="theme" />
    <input name="subTheme" />
  </div>
</div>

<div class="formSection">
  <h3 class="formSectionTitle">🎨 角色设定</h3>
  <div class="formFieldGroup">
    <input name="characterName" />
    <input name="characterRole" />
  </div>
</div>
```

#### 方案 C：使用视觉分隔线
```css
.formFieldGroup--section {
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--line-soft);
}

.formFieldGroup--section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
```

### 推荐方案
**方案 B（卡片分组）** 最直观，用户能清楚看到字段分组。

### 实施步骤
1. 修改 `ProjectSettingEditor` 组件
2. 添加分组标题和样式
3. 进行视觉测试

---

## 建议 2：改进加载态 🟡 中优先级

### 当前代码
```tsx
<div className={styles.loadingText}>
  <div className="flex items-center justify-center gap-2">
    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin opacity-50" />
    <span>正在加载项目设定...</span>
  </div>
</div>
```

### 改进方案

#### 方案 A：添加骨架屏
```tsx
<div className={styles.contentCard}>
  <div className={styles.skeleton}>
    <div className={styles.skeletonLine} />
    <div className={styles.skeletonLine} style={{ width: '80%' }} />
    <div className={styles.skeletonLine} style={{ marginTop: '1rem' }} />
    <div className={styles.skeletonLine} />
  </div>
</div>
```

```css
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.skeletonLine {
  height: 1rem;
  background: linear-gradient(
    90deg,
    var(--bg-muted) 0%,
    var(--bg-surface) 50%,
    var(--bg-muted) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

#### 方案 B：改进加载文本
```tsx
<div className={styles.loadingContainer}>
  <div className={styles.loadingSpinner} />
  <p className={styles.loadingText}>正在加载项目设定...</p>
  <p className={styles.loadingHint}>这通常需要 1-2 秒</p>
</div>
```

### 推荐方案
**方案 A（骨架屏）** 能显著提升感知性能。

---

## 建议 3：增强可访问性 🟡 中优先级

### 当前问题
- 缺少 ARIA 标签
- 键盘导航可能不完善
- 屏幕阅读器支持不足

### 改进方案

#### 添加 ARIA 标签
```html
<!-- 侧栏 -->
<nav className={styles.sidebar} aria-label="项目设置导航">
  <div role="tablist">
    <button role="tab" aria-selected={tab === 'setting'}>
      设置
    </button>
  </div>
</nav>

<!-- 内容区 -->
<main className={styles.content} role="main">
  <div className={styles.contentCard} role="region" aria-label="项目设置内容">
    {/* 内容 */}
  </div>
</main>
```

#### 改进键盘导航
```tsx
const handleKeyDown = (e: React.KeyboardEvent) => {
  if (e.key === 'ArrowDown') {
    // 移动到下一个标签
  } else if (e.key === 'ArrowUp') {
    // 移动到上一个标签
  } else if (e.key === 'Enter' || e.key === ' ') {
    // 激活标签
  }
};
```

---

## 建议 4：优化审计页过滤器 🟡 中优先级

### 当前问题
- 过滤器是文本输入，需要用户知道事件名
- 用户体验不友好

### 改进方案

#### 添加预设过滤项
```tsx
const presetFilters = [
  { label: '项目更新', value: 'project.updated' },
  { label: '设置更新', value: 'project.setting.updated' },
  { label: '规则更新', value: 'project.rules.updated' },
  { label: '所有操作', value: null },
];

<div className={styles.filterPresets}>
  {presetFilters.map(filter => (
    <button
      key={filter.value}
      onClick={() => onEventTypeChange(filter.value)}
      className={filter.value === eventType ? styles.active : ''}
    >
      {filter.label}
    </button>
  ))}
</div>
```

#### 改进空状态
```tsx
<div className={styles.emptyState}>
  <div className={styles.emptyIcon}>📋</div>
  <h3>暂无操作记录</h3>
  <p>项目的所有操作都会在这里显示</p>
</div>
```

---

## 建议 5：添加微交互动画 🟢 低优先级

### 当前代码
```css
.sidebar {
  animation: slideInLeft 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.content {
  animation: fadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
```

### 改进方案

#### 添加标签页切换动画
```css
@keyframes tabSwitch {
  from {
    opacity: 0;
    transform: translateX(12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.contentCard {
  animation: tabSwitch 0.25s ease-out;
}
```

#### 添加按钮悬停效果
```css
.actionButton {
  transition: all var(--transition-fast);
}

.actionButton:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.actionButton:active {
  transform: translateY(0);
}
```

---

## 实施优先级和时间表

### 第一阶段（立即改进）- 1-2 天
- [ ] 问题 1：添加内容卡片宽度限制
- [ ] 问题 2：统一表单字段间距
- [ ] 问题 3：优化移动端 < 640px 布局

### 第二阶段（重要改进）- 3-5 天
- [ ] 建议 1：增强字段分组语义
- [ ] 建议 2：改进加载态
- [ ] 建议 3：增强可访问性

### 第三阶段（体验优化）- 5-7 天
- [ ] 建议 4：优化审计页过滤器
- [ ] 建议 5：添加微交互动画
- [ ] 进行完整的视觉回归测试

---

## 测试清单

### 视觉测试
- [ ] 桌面端（1920px）：内容卡片宽度正确
- [ ] 平板端（1024px）：布局正确
- [ ] 手机端（640px）：侧栏隐藏或改为抽屉式
- [ ] 手机端（375px）：极端宽度测试

### 交互测试
- [ ] 标签页切换：动画流畅
- [ ] 表单输入：焦点状态清晰
- [ ] 按钮悬停：反馈明显
- [ ] 键盘导航：Tab 键可以导航

### 可访问性测试
- [ ] 屏幕阅读器：能正确读出内容
- [ ] 键盘导航：所有功能可用键盘操作
- [ ] 颜色对比：满足 WCAG AA 标准
- [ ] 动画：支持 `prefers-reduced-motion`

---

## 总结

你的设计文档质量很高，与源码高度一致。通过实施这些改进建议，可以进一步提升用户体验和代码质量。

**建议优先级**：
1. 🔴 问题 1-3（必须改进）
2. 🟡 建议 1-3（重要改进）
3. 🟢 建议 4-5（体验优化）

