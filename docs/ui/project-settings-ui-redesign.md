# 项目设置页面 UI/UX 设计规范

## 1. 概述

### 1.1 现状问题

| 问题 | 表现 | 根因 |
|------|------|------|
| **信息层级不清晰** | 标题、描述、表单字段混在一起 | 缺少分组容器 |
| **表单字段排列混乱** | 字段宽度不一致，排列无规则 | 没有网格系统约束 |
| **空间利用不合理** | 左侧导航占用过多空间 | 固定 280px 宽度 |
| **表单组件样式不统一** | 输入框、文本域、下拉框高度不一致 | ink-input 36px，textarea 无固定高度 |
| **内容分组不明显** | 相关字段没有用卡片组织 | 缺少视觉分隔 |

### 1.2 设计目标

- ✅ 清晰的视觉层级和信息分组
- ✅ 统一的表单组件样式和间距
- ✅ 高效的空间利用
- ✅ 一致的交互体验
- ✅ 易于维护和扩展的代码结构
- ✅ 完整的状态反馈和错误处理

### 1.3 适用范围

- 项目设置页面所有标签页（设置、规则、AI偏好、Skills、MCP、审计）
- 所有表单组件和布局
- 新建/编辑表单通用组件

---

## 2. 设计 Token

### 2.1 颜色系统

```css
:root {
  /* 背景色 */
  --bg-canvas: #f8f6f1;           /* 画布背景 */
  --bg-surface: #ffffff;           /* 卡片/面板背景 */
  --bg-surface-hover: rgba(61, 61, 61, 0.04);
  --bg-surface-active: rgba(61, 61, 61, 0.08);
  --bg-muted: #f3f0e8;            /* 次级背景 */

  /* 边框色 */
  --line-soft: rgba(61, 61, 61, 0.09);
  --line-strong: rgba(61, 61, 61, 0.16);
  --line-focus: rgba(90, 122, 107, 0.4);

  /* 文本色 */
  --text-primary: #3d3d3d;         /* 主文本 */
  --text-secondary: #6b6b6b;       /* 次级文本 */
  --text-tertiary: #9b9a97;        /* 辅助文本 */
  --text-placeholder: #b4b4b4;     /* 占位符 */

  /* 品牌色 */
  --accent-primary: #5a7a6b;       /* 主色调 */
  --accent-primary-hover: #4a6a5b;
  --accent-secondary: #8b7355;
  --accent-tertiary: #c4a77d;

  /* 状态色 */
  --accent-success: #5a8a6b;      /* 成功 */
  --accent-warning: #c4883d;       /* 警告 */
  --accent-danger: #c45a5a;       /* 危险 */
  --accent-purple: #9065b0;       /* 辅助-紫 */
  --accent-pink: #d44c8f;          /* 辅助-粉 */
  --accent-ink: #5a9aaa;           /* 辅助-墨 */

  /* 阴影 */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.03);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.04), 0 4px 6px -2px rgba(0, 0, 0, 0.02);

  /* 圆角 */
  --radius-xs: 3px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  /* 字体 */
  --font-serif: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", serif;
  --font-sans: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, "SF Mono", "Cascadia Code", "Fira Code", monospace;

  /* 过渡 */
  --transition-fast: 120ms ease;
  --transition-normal: 200ms ease;
  --transition-slow: 300ms ease;
  --transition-spring: 300ms cubic-bezier(0.34, 1.56, 0.64, 1);
  --transition-smooth: 250ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

### 2.2 间距系统

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
}
```

### 2.3 组件尺寸

```css
:root {
  /* 输入组件统一高度 */
  --input-height-sm: 28px;
  --input-height-md: 36px;
  --input-height-lg: 44px;

  /* 按钮高度 */
  --button-height-sm: 28px;
  --button-height-md: 32px;
  --button-height-lg: 40px;

  /* 侧边栏宽度 */
  --sidebar-width: 240px;
  --sidebar-width-max: 280px;

  /* 内容区最大宽度 */
  --content-max-width: 800px;
  --page-max-width: 1600px;
}
```

---

## 3. 布局架构

### 3.1 整体布局结构

```
┌─────────────────────────────────────────────────────────┐
│ 顶部导航栏                                               │
├──────────────┬──────────────────────────────────────────┤
│ 左侧导航     │ 主内容区域                                │
│ (240px)     │ (flex: 1)                                │
│              │                                          │
│ • 设置       │ ┌────────────────────────────────────┐  │
│ • 规则       │ │ 页面标题 + 描述                     │  │
│ • AI偏好     │ ├────────────────────────────────────┤  │
│ • Skills     │ │ 内容卡片                            │  │
│ • MCP        │ │ ┌──────────────────────────────┐  │  │
│ • 审计       │ │ │ 分组标题                     │  │  │
│              │ │ │ 表单字段...                  │  │  │
│              │ │ └──────────────────────────────┘  │  │
│              │ │                                    │  │
│              │ │ 内容卡片 2                         │  │
│              │ │ ...                                │  │
│              │ │                                    │  │
│              │ │ [保存] [取消]                      │  │
│              │ └────────────────────────────────────┘  │
└──────────────┴──────────────────────────────────────────┘
```

### 3.2 主内容区域尺寸

- **最大宽度**：1600px
- **内边距**：24px（顶部）、24px（左右）、24px（底部）
- **内容卡片最大宽度**：800px
- **侧边栏宽度**：240px（最大 280px）
- **响应式断点**：
  - 小屏幕 < 768px：单列、全宽
  - 中屏幕 768px - 1023px：单列，侧边栏收起
  - 大屏幕 ≥ 1024px：双列网格

---

## 4. 组件状态规范

### 4.1 输入组件状态

#### Default（默认）
```
边框：1px solid var(--line-soft)
背景：var(--bg-surface)
```

#### Hover（悬停）
```
边框：1px solid var(--line-strong)
```

#### Focus（聚焦）
```
边框：1px solid var(--accent-primary)
阴影：0 0 0 3px var(--line-focus)
```

#### Disabled（禁用）
```
背景：var(--bg-muted)
颜色：var(--text-placeholder)
光标：not-allowed
透明度：1（不降低透明度，通过颜色表达）
```

#### Error（错误）
```
边框：1px solid var(--accent-danger)
阴影：0 0 0 3px rgba(196, 90, 90, 0.1)
```

#### Success（成功）
```
边框：1px solid var(--accent-success)
阴影：0 0 0 3px rgba(90, 138, 107, 0.1)
```

### 4.2 按钮状态

#### Primary（主按钮）
| 状态 | 样式 |
|------|------|
| Default | 背景 var(--accent-primary)，文字白色 |
| Hover | 背景 var(--accent-primary-hover)，阴影 0 2px 8px rgba(90, 122, 107, 0.2) |
| Active | transform: scale(0.97) |
| Disabled | opacity: 0.5，光标 not-allowed |

#### Secondary（次按钮）
| 状态 | 样式 |
|------|------|
| Default | 背景 var(--bg-surface)，边框 var(--line-soft) |
| Hover | 背景 var(--bg-surface-hover)，边框 var(--line-strong) |
| Active | 背景 var(--bg-surface-active) |
| Disabled | opacity: 0.5 |

#### Danger（危险按钮）
| 状态 | 样式 |
|------|------|
| Default | 背景透明，边框 var(--accent-danger)，文字 var(--accent-danger) |
| Hover | 背景 var(--accent-danger)，文字白色 |
| Disabled | opacity: 0.5 |

### 4.3 卡片状态

#### Default
```
背景：var(--bg-surface)
边框：1px solid var(--line-soft)
阴影：var(--shadow-sm)
圆角：var(--radius-lg)
```

#### Hover
```
边框：1px solid var(--line-strong)
阴影：var(--shadow-md)
```

### 4.4 表单反馈状态

#### Loading（加载中）
- 保存按钮显示加载状态（禁止重复点击）
- 使用 `aria-busy="true"` 标记
- 按钮文字改为"保存中..."

#### Success（保存成功）
- 显示成功提示（AppNotice）
- 自动消失的 toast，3秒后淡出
- 成功提示内容：`"项目设定已保存"`

#### Error（保存失败）
- 显示危险提示（AppNotice）
- 不自动消失，需要手动关闭
- 显示具体错误信息

---

## 5. 表单字段规范

### 5.1 字段容器
```css
.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-field--full {
  grid-column: 1 / -1;
}

.form-field--half {
  grid-column: span 1;
}
```

### 5.2 字段标签
```css
.form-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-label--required::after {
  content: "*";
  color: var(--accent-danger);
  font-weight: 600;
}

.form-label--optional {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-tertiary);
}
```

### 5.3 输入组件（已定义在 globals.css）

```css
/* ink-input */
.ink-input {
  min-height: var(--input-height-md); /* 36px */
  padding: 8px 12px;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-md);
  font-size: 14px;
}

/* ink-textarea */
.ink-textarea {
  min-height: 120px;
  padding: 10px 12px;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-md);
  font-size: 14px;
  resize: vertical;
}
```

### 5.4 帮助文本和错误提示
```css
.form-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.4;
}

.form-error {
  font-size: 12px;
  color: var(--accent-danger);
  display: flex;
  align-items: center;
  gap: 4px;
}

.form-success {
  font-size: 12px;
  color: var(--accent-success);
}
```

---

## 6. 内容分组卡片规范

### 6.1 SectionCard 组件

```css
.section-card {
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.section-card__header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--line-soft);
}

.section-card__title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-serif);
}

.section-card__description {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: var(--space-1);
  line-height: 1.5;
}

.section-card__body {
  padding: var(--space-5) var(--space-6);
}
```

### 6.2 表单网格布局
```css
.form-grid {
  display: grid;
  gap: var(--space-5);
}

.form-grid--2col {
  grid-template-columns: 1fr 1fr;
}

@media (max-width: 768px) {
  .form-grid--2col {
    grid-template-columns: 1fr;
  }
}
```

---

## 7. 按钮和操作规范

### 7.1 操作栏布局
```css
.form-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: flex-end;
  padding-top: var(--space-5);
  margin-top: var(--space-5);
  border-top: 1px solid var(--line-soft);
}

.form-actions--sticky {
  position: sticky;
  bottom: 0;
  background: var(--bg-surface);
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--line-soft);
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  z-index: 10;
}
```

---

## 8. 微交互规范

### 8.1 页面过渡动画
```css
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.sidebar {
  animation: slideInLeft 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.content {
  animation: fadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
```

### 8.2 按钮点击反馈
```css
.ink-button:active {
  transform: scale(0.97);
  transition: transform 80ms ease;
}
```

### 8.3 减少动画（无障碍）
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 9. 无障碍规范

### 9.1 焦点管理
- 所有可交互元素必须有可见焦点指示器
- 焦点样式：`outline: 2px solid var(--accent-primary); outline-offset: 2px;`
- 表单提交时，焦点应保持或移动到相应位置

### 9.2 ARIA 属性
```html
<!-- 必填字段 -->
<input aria-required="true" />

<!-- 错误提示 -->
<input aria-invalid="true" aria-describedby="error-id" />
<span id="error-id" role="alert">错误信息</span>

<!-- 加载状态 -->
<div aria-busy="true">
  <button disabled>保存中...</button>
</div>

<!-- 标签关联 -->
<label for="input-id">字段名</label>
<input id="input-id" />
```

### 9.3 键盘导航
| 按键 | 行为 |
|------|------|
| Tab | 移动到下一个可交互元素 |
| Shift + Tab | 移动到上一个可交互元素 |
| Enter | 激活按钮/提交表单 |
| Escape | 关闭对话框/取消编辑 |

---

## 10. 各标签页细化方案

### 10.1 项目设定（Settings）

**当前状态**：使用 `SectionCard` + `ProjectSettingField` 组件，字段以 2 列网格排列

**字段分组**：
| 分组 | 字段 |
|------|------|
| 基本信息 | 题材、子题材、目标读者、整体语气 |
| 角色设定 | 主角姓名、主角身份 |
| 世界观 | 世界名称、力量体系 |
| 规模设定 | 目标字数、目标章节 |
| 剧情内容 | 核心冲突、剧情走向、特殊要求 |

**当前代码位置**：`apps/web/src/features/studio/components/project-setting-editor.tsx`

**改进建议**：
1. 将字段分组用 `fieldset` + `legend` 语义化标记
2. 每个分组用卡片或分隔线视觉区分
3. "核心冲突"、"剧情走向"等文本域应保持独立分组
4. 完整度提示应更突出显示

### 10.2 规则（Rules）

**当前状态**：`AssistantRulesEditor` 组件

**布局**：
```
┌─ 项目长期规则 ─────────────────────────────┐
│ 说明文本（通过 props 传入）                  │
├────────────────────────────────────────────┤
│ ☑ 在每次聊天中自动上传规则                   │
│                                            │
│ 规则内容:                                   │
│ ┌──────────────────────────────────────┐  │
│ │ 文本域（markdown 编辑器）             │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ [保存规则] [还原]                           │
└────────────────────────────────────────────┘
```

**改进点**：
- 复选框和标签对齐
- 文本域宽度限制在 800px
- 增加字符计数器（可选）

### 10.3 AI 偏好（Assistant）

**当前状态**：`AssistantPreferencesPanel` 组件

**布局**：
```
┌─ 项目 AI 偏好 ──────────────────────────────┐
│ 说明文本                                     │
├────────────────────────────────────────────┤
│ 🤖 AI 连接                                  │
│ ┌──────────────────────────────────────┐  │
│ │ 跟随个人AI偏好: [下拉框]              │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ 🔧 AI 模型                                  │
│ ┌──────────────────────────────────────┐  │
│ │ 模型名称: [输入框]                    │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ 📊 单次回复上限                             │
│ ┌──────────────────────────────────────┐  │
│ │ [输入框]                             │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ [保存设置] [还原]                          │
└────────────────────────────────────────────┘
```

**改进点**：
- 所有输入组件统一高度（36px）
- 下拉框和输入框对齐
- 增加图标标识不同分组

### 10.4 Skills

**当前状态**：`AssistantSkillsPanel` 组件

**改进点**：
- 卡片宽度限制在 800px
- 按钮使用 sticky 定位
- 字段间距统一

### 10.5 MCP

**当前状态**：`AssistantMcpPanel` 组件

**改进点**：
- 同 Skills

### 10.6 审计（Audit）

**当前状态**：`ProjectAuditPanel` 组件

**改进点**：
- 添加表格样式（交替行背景色）
- 增加过滤功能
- 优化空状态显示

---

## 11. 响应式设计

### 11.1 断点定义

```css
/* 中屏幕 */
@media (max-width: 1023px) {
  .page {
    grid-template-columns: 1fr;
    padding: var(--space-4);
  }

  .sidebar {
    position: relative;
    top: 0;
    max-height: none;
  }
}

/* 小屏幕 */
@media (max-width: 767px) {
  .page {
    gap: var(--space-4);
    padding: var(--space-3);
  }

  .section-card__header,
  .section-card__body {
    padding: var(--space-4);
  }

  .form-grid--2col {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .btn {
    width: 100%;
  }
}
```

---

## 12. 实现优先级

### P0（立即改进）
- [x] 统一表单字段高度（已在 globals.css 定义为 36px）
- [x] 实现卡片分组布局（SectionCard 组件）
- [x] 固定按钮位置（form-actions）
- [x] 统一间距规范（使用 CSS 变量）

### P1（重要改进）
- [ ] 实现 2 列网格布局（form-grid--2col）
- [ ] 优化字段标签和帮助文本样式
- [ ] 添加焦点和错误状态样式
- [ ] 为"项目设定"标签页添加分组分隔

### P2（体验优化）
- [ ] 添加字段验证反馈
- [ ] 实现表单保存状态提示
- [ ] 响应式布局优化
- [ ] 添加加载和过渡动画（已有）

---

## 13. 代码示例

### 13.1 HTML 结构示例

```html
<article class="section-card">
  <header class="section-card__header">
    <div class="section-card__copy">
      <h2 class="section-card__title">项目设定</h2>
      <p class="section-card__description">设定故事的基本信息与创作方向。</p>
    </div>
    <div class="flex gap-2">
      <button class="ink-button-secondary">完整度检查</button>
      <button class="ink-button">保存设定</button>
    </div>
  </header>

  <div class="section-card__body">
    <div class="form-grid form-grid--2col">
      <div class="form-field">
        <label class="form-label" for="genre">题材</label>
        <input
          id="genre"
          class="ink-input"
          type="text"
          placeholder="输入题材"
          aria-required="true"
        />
        <span class="form-hint">如：都市、玄幻、科幻</span>
      </div>

      <div class="form-field">
        <label class="form-label" for="sub-genre">子题材</label>
        <input
          id="sub-genre"
          class="ink-input"
          type="text"
          placeholder="输入子题材"
        />
      </div>
    </div>

    <div class="form-field form-field--full">
      <label class="form-label" for="core-conflict">核心冲突</label>
      <textarea
        id="core-conflict"
        class="ink-textarea"
        placeholder="描述故事的核心冲突"
        aria-describedby="conflict-hint"
      ></textarea>
      <span id="conflict-hint" class="form-hint">
        核心冲突是推动故事发展的主要矛盾
      </span>
    </div>

    <div class="form-actions">
      <button class="ink-button-secondary">取消</button>
      <button class="ink-button">保存设定</button>
    </div>
  </div>
</article>
```

---

## 14. 维护和更新

- 定期审查设计规范的有效性
- 收集用户反馈并迭代改进
- 保持代码和设计文档同步
- 建立组件库以提高开发效率
- 颜色/间距等 token 变更时，同步更新 globals.css 和本文档
