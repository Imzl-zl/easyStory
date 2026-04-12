# easyStory 前端样式统一重构设计

> 日期: 2026-04-12
> 范围: CSS Token + 组件样式统一，不涉及暗色模式（后续迭代）
> 目标: 统一主题色、消灭硬编码颜色、归一按钮体系和圆角、修复 Studio 共创助手对比度

---

## 一、问题诊断

### 1.1 主题色问题

`--accent-primary: #7a9a85` 饱和度约 18%，灰到看不出色相。无法引导视觉焦点，也不符合"温暖文学"创作工具定位。

### 1.2 按钮隐形问题

- `ink-button-secondary` 边框 `--line-strong: rgba(90,75,50,0.12)` 在浅色面板上几乎不可见
- Studio Composer 工具栏按钮用 `bg-surface-hover` 和底栏背景几乎同色
- 聊天面板"新对话"按钮 `bg-surface` 在白/玻璃背景上无视觉边界

### 1.3 按钮体系分裂

Studio 页面混用三套按钮系统:
1. ink-button 系列（CSS 类）
2. Arco `<Button>` 组件（约 12 处，分布在 studio 和 incubator 模块）
3. 自定义 Tailwind `<button>`（最多，约 20+ 处）

### 1.4 圆角不统一

Studio 区域同时存在 7 种圆角值（6px~9999px），同类 chip 按钮有 3 种不同圆角。

### 1.5 硬编码颜色泛滥

60+ 处 `bg-[rgba(...)]` / `border-[rgba(...)]` 直接写在组件中:
- 信息蓝 `rgba(58,124,165,...)` 约 5 处
- 警告橙 `rgba(183,121,31,...)` 约 8 处
- 成功绿 `rgba(47,107,69,...)` 约 2 处
- 危险红 `rgba(196,90,90,...)` 约 3 处
- 各种 `#ffffff`、`#f3ede3`、`#ebeef3`、`#b0bac8` 约 6 处
- AuthForm 渐变背景 1 处（多个硬编码 hex/rgba）
- Studio 聊天面板硬编码约 8 处

---

## 二、主题色重建

### 2.1 色系方向

暖调低饱和，介于暖棕和墨绿之间，"羊皮纸上的墨"气质。

### 2.2 Token 变更

| Token | 当前值 | 新值 | 理由 |
|-------|--------|------|------|
| `--accent-primary` | `#7a9a85` (灰绿 18%饱和) | `#7c6e5d` (暖棕) | 温暖文学气质，对比度更高 |
| `--accent-primary-hover` | `#6a8a75` | `#6d604f` | 同色系加深 |
| `--accent-primary-dark` | `#5a7a68` | `#5b5040` | 英雄按钮渐变终点 |
| `--accent-primary-soft` | `rgba(122,154,133,0.08)` | `rgba(124,110,93,0.12)` | 跟随主色 + tab active 态更明显 |
| `--accent-primary-muted` | `rgba(122,154,133,0.14)` | `rgba(124,110,93,0.14)` | 跟随主色 |
| `--accent-info` | 未定义 | `#5a8faa` (钢蓝) | 组件已大量使用 `bg-accent-info` 但缺失 token |
| `--accent-info-soft` | 未定义 | `rgba(90,143,170,0.10)` | 信息色浅底 |
| `--accent-info-muted` | 未定义 | `rgba(90,143,170,0.18)` | 信息色边框 |
| `--bg-elevated` | `#fdfcf9` (与 surface 同值) | `#ffffff` | 拉开和 surface 的差距，修复 secondary 按钮对比度 |
| `--accent-success` | `#7a9a85` (同 primary) | `#6b8f71` (墨绿) | 和 primary 区分开，真正的"成功"色 |
| `--accent-warning` | `#c4a050` | `#b8944a` | 和暖棕更协调 |
| `--accent-danger` | `#c47070` | `#b85c5c` | 更沉稳 |
| `--line-strong` | `rgba(90,75,50,0.12)` | `rgba(124,110,93,0.20)` | 跟随新主色，边框更明显 |
| `--line-focus` | `rgba(122,154,133,0.28)` | `rgba(124,110,93,0.28)` | 跟随新主色 |

### 2.3 Arco 主题色同步

`--arco-color-primary-6` 等系列值同步更新到新 `--accent-primary` 及衍生色。

### 2.4 整体色调感受

暖棕主色 + 米白背景 + 墨绿成功色 = "古籍书房"氛围。

---

## 三、补充语义 Token

### 3.1 新增 Token

```css
/* Callout 语义色 — 替代所有散落的 rgba */
--callout-info-bg: rgba(58, 124, 165, 0.07);
--callout-info-border: rgba(58, 124, 165, 0.16);
--callout-warning-bg: rgba(183, 121, 31, 0.08);
--callout-warning-border: rgba(183, 121, 31, 0.20);
--callout-success-bg: rgba(47, 107, 69, 0.08);
--callout-success-border: rgba(47, 107, 69, 0.18);
--callout-danger-bg: rgba(184, 92, 92, 0.08);
--callout-danger-border: rgba(184, 92, 92, 0.16);

/* Toolbar 语义色 — 解决 Composer 按钮隐形 */
--toolbar-bg: var(--bg-surface);
--toolbar-bg-hover: rgba(124, 110, 93, 0.08);
--toolbar-bg-active: rgba(124, 110, 93, 0.14);
--toolbar-border: var(--line-strong);
--toolbar-text: var(--text-secondary);
--toolbar-text-active: var(--accent-primary);

/* Chat 语义色 — 统一聊天区域 */
--chat-user-bubble-bg: var(--bg-muted);
--chat-assistant-bubble-bg: var(--accent-primary-soft);
--chat-skill-panel-bg: var(--bg-surface);
--chat-skill-option-active-bg: var(--accent-primary-soft);
```

### 3.2 新增 CSS 复合类

```css
/* Callout 横幅 */
.callout-info    { background: var(--callout-info-bg);    border: 1px solid var(--callout-info-border);    border-radius: var(--radius-2xl); padding: 12px 16px; }
.callout-warning { background: var(--callout-warning-bg); border: 1px solid var(--callout-warning-border); border-radius: var(--radius-2xl); padding: 12px 16px; }
.callout-success { background: var(--callout-success-bg); border: 1px solid var(--callout-success-border); border-radius: var(--radius-2xl); padding: 12px 16px; }
.callout-danger  { background: var(--callout-danger-bg);  border: 1px solid var(--callout-danger-border);  border-radius: var(--radius-2xl); padding: 12px 16px; }

/* Toolbar 按钮 */
.ink-toolbar-icon { /* 见第四部分 */ }
.ink-toolbar-chip { /* 见第四部分 */ }
.ink-toolbar-toggle { /* 见第四部分 */ }
```

### 3.3 硬编码替换映射

| 模式 | 出现次数 | 替换为 |
|------|---------|--------|
| `bg-[rgba(58,124,165,0.07~0.1)]` 信息蓝 | ~5 | `callout-info` 类 |
| `bg-[rgba(183,121,31,0.08~0.14)]` 警告橙 | ~8 | `callout-warning` 类 |
| `bg-[rgba(196,136,61,0.08~0.16)]` 暖橙变体 | ~4 | `callout-warning` 类（与上统一） |
| `bg-[rgba(47,107,69,0.08)]` 成功绿 | ~2 | `callout-success` 类 |
| `bg-[rgba(196,90,90,0.08~0.1)]` 危险红 | ~3 | `callout-danger` 类 |
| `bg-[rgba(125,153,178,...)]` 蓝灰 | ~2 | `accent-primary-soft` 或 `--accent-info-soft` |
| `bg-[rgba(31,27,22,0.05~0.06)]` 深色叠加 | ~3 | `bg-surface-hover` / `bg-surface-active` |
| `bg-[rgba(61,61,61,0.05~0.06)]` 中性叠加 | ~2 | `bg-surface-hover`（例外：模板内联 CSS 可保留） |
| `bg-[#ffffff]` / `bg-[#f3ede3]` / `bg-[#ebeef3]` / `bg-[#b0bac8]` | ~6 | `bg-surface` / `bg-muted` / 对应 token |
| `bg-white` / `bg-white/80` / `bg-white/92` / `bg-white/95` / `bg-white/90` | ~10 | 不透明→`bg-surface`；带透明度→`bg-surface/N` 或新增 `--bg-surface-translucent` token |
| AuthForm 渐变背景 | 1 | 提取为 `--auth-bg-gradient` 变量，定义如下： |

**`--auth-bg-gradient` 定义：**
```css
--auth-bg-gradient: radial-gradient(circle at top left, rgba(196,167,125,0.18), transparent 30%),
  radial-gradient(circle at right 20%, rgba(90,154,170,0.16), transparent 28%),
  linear-gradient(180deg, #ebeef3 0%, #f4efe7 48%, #f4f5f7 100%);
```
注意：rgba 值将在主题色更新后同步调整（暖棕替换灰绿方向）。
| Studio 聊天面板硬编码 | ~8 | `--chat-*` token |
| `bg-[linear-gradient(...)]` 组件内线性渐变 | ~5 | 提取为对应 CSS 变量 |
| `workspace-shell.tsx` 背景渐变 rgba | 1 | 提取为 `--workspace-shell-accent-gradient` 变量 |

---

## 四、统一按钮体系

### 4.1 按钮体系归一

| 语义 | 类名 | 圆角 | 适用场景 |
|------|------|------|---------|
| 主操作 | `ink-button` | pill | 保存、创建、恢复 |
| 次操作 | `ink-button-secondary` | pill | 返回、重试、收起 |
| 危险操作 | `ink-button-danger` | pill | 删除、清空、确认离开 |
| 英雄 CTA | `ink-button-hero` | pill | 登录/注册提交 |
| Tab 切换 | `ink-tab` | md | 分类、过滤、模式切换 |
| 图标按钮 | `ink-icon-button` | md | 通用图标操作 |
| 标签选择 | `ink-pill` | pill | 状态标签、模式指示 |
| 链接按钮 | `ink-link-button` | pill | 文字链接按钮 |
| **工具栏图标** | **`ink-toolbar-icon`** | **lg** | Composer 上传/附件图标 |
| **工具栏 Chip** | **`ink-toolbar-chip`** | **lg** | 模型选择、上下文选择 |
| **工具栏 Toggle** | **`ink-toolbar-toggle`** | **lg** | 写入文稿开关 |

### 4.2 新增 CSS 类定义

```css
.ink-toolbar-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--radius-lg);
  background: transparent;
  color: var(--toolbar-text);
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}
.ink-toolbar-icon:hover {
  background: var(--toolbar-bg-hover);
  color: var(--toolbar-text-active);
}
.ink-toolbar-icon:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ink-toolbar-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--toolbar-border);
  border-radius: var(--radius-lg);
  background: var(--toolbar-bg);
  color: var(--toolbar-text);
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.ink-toolbar-chip:hover {
  background: var(--toolbar-bg-hover);
  border-color: var(--accent-primary-muted);
  color: var(--toolbar-text-active);
}
.ink-toolbar-chip[data-active="true"] {
  background: var(--toolbar-bg-active);
  border-color: var(--accent-primary-muted);
  color: var(--accent-primary);
}
.ink-toolbar-chip:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ink-toolbar-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--toolbar-border);
  border-radius: var(--radius-lg);
  background: var(--toolbar-bg);
  color: var(--toolbar-text);
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.ink-toolbar-toggle:hover {
  background: var(--toolbar-bg-hover);
  border-color: var(--accent-primary-muted);
  color: var(--toolbar-text-active);
}
.ink-toolbar-toggle[aria-pressed="true"] {
  background: var(--toolbar-bg-active);
  border-color: var(--accent-primary-muted);
  color: var(--accent-primary);
}
.ink-toolbar-toggle:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
```

### 4.3 Arco Button 替换

消灭所有 Arco `<Button>` 直接使用，统一到 ink-button 体系:

| 文件 | 当前 | 替换为 |
|------|------|--------|
| `studio-chat-composer.tsx` 发送按钮 | `<Button type="primary" shape="round" loading={...}>` | `<button className="ink-button" disabled={...}>` + loading 态由组件内条件渲染图标实现 |
| `studio-chat-message-bubble.tsx` 复制/追加/新建 (3处) | `<Button size="mini" shape="round" type="secondary">` | `<button className="ink-button-secondary text-xs h-7 px-2.5">` |
| `studio-chat-history-panel.tsx` 删除对话 | `<Button shape="circle" status="danger" type="text">` | `<button className="ink-icon-button text-accent-danger">` |
| `incubator-chat-panel.tsx` 发送按钮 | `<Button type="primary" shape="round">` | `<button className="ink-button">` |
| `incubator-chat-history-panel.tsx` 发送/删除 (2处) | `<Button type="primary" shape="round">` / `<Button type="text">` | `<button className="ink-button">` / `<button className="ink-button-secondary">` |
| `incubator-chat-draft-panel-support.tsx` 操作按钮 (2处) | `<Button>` | `<button className="ink-button-secondary">` |
| `incubator-chat-draft-guidance.tsx` 操作按钮 | `<Button>` | `<button className="ink-button-secondary">` |
| `incubator-chat-panel-support.tsx` 操作按钮 | `<Button>` | `<button className="ink-button-secondary">` |

### 4.4 对比度修复

| 问题 | 修复 |
|------|------|
| `ink-button-secondary` 边框太浅 | `--line-strong` 提升到 `rgba(124,110,93,0.20)` |
| `ink-button-secondary` 背景和面板接近 | `--bg-elevated` 改为 `#ffffff`（与 `--bg-surface: #fdfcf9` 拉开差距）+ `ink-button-secondary` background 改用 `var(--bg-elevated)` |
| `ink-tab[data-active]` 背景太浅 | `--accent-primary-soft` 从 0.08 提升到 0.12 |
| Composer 工具栏按钮和底栏融为一体 | 新 toolbar 类有明确边框 `var(--toolbar-border)` |
| 聊天面板"新对话"按钮不可见 | 改为 `ink-button-secondary` 小尺寸，有边框 + shadow |
| Skill 面板按钮自定义样式不统一 | 全部改为 `ink-toolbar-chip` |

---

## 五、圆角统一

### 5.1 统一规则

| 语义级别 | Token | 值 | 用途 |
|----------|-------|----|------|
| 小 | `--radius-sm` | 8px | badge、小标签 |
| 中 | `--radius-lg` | 12px | 输入框、图标按钮、toolbar chip、列表项 |
| 大 | `--radius-2xl` | 20px | 面板、卡片、对话框、下拉触发 |
| 全圆 | `--radius-pill` | 9999px | 所有交互按钮、pill 标签 |

### 5.2 替换映射

| 当前 | 替换为 | 影响范围 |
|------|--------|---------|
| `rounded` (6px) 状态标签 | `rounded-sm` via token | 聊天状态标签 |
| `rounded-md` (8px) 附件 pill | `rounded-sm` via token | 附件标签、小标签 |
| `rounded-lg` (12px) 列表项/chip | `rounded-lg` via token | 对话列表项、toolbar chip |
| `rounded-xl` (16px) 面板内部 | `rounded-2xl` via token (20px) | 面板内部区域、下拉触发 |
| `rounded-2xl` (20px) | 保持 | 卡片、树节点 |
| `rounded-3xl`/`4xl`/`5xl` hero-card | hero-card CSS 类内置 | 保持 |
| `rounded-full` chip/触发器 | `rounded-pill` via token | 新对话按钮、Skill 触发器 |
| `rounded-[10px]` | `rounded-lg` via token (12px) | 空状态图标 |

### 5.3 保留的中间 Token

`--radius-xs`(6px) 和 `--radius-md`(10px) 保留为 ink-input / ink-tab / ink-icon-button 等现有 CSS 类的内部引用，不对外暴露给组件直接使用。组件应使用 5.1 定义的 4 个语义级别。

### 5.4 约束

- 组件中不再允许直接写 Tailwind `rounded-*` 类，一律通过 CSS 变量或 ink-* 复合类引用
- 新增 `ink-toolbar-*` 类内置圆角，不需要外部再写 `rounded-*`

---

## 六、Studio 共创助手专项修复

### 6.1 Composer 输入区域

| 元素 | 当前 | 改为 |
|------|------|------|
| ToolbarIconButton | 透明底 + `rounded-2xl` | `ink-toolbar-icon` + `rounded-lg`(内置) |
| ToolbarChipButton | `bg-surface-hover` 无边框 + `rounded-lg` | `ink-toolbar-chip` 有边框 + `rounded-lg`(内置) |
| ToolbarToggleButton | `bg-surface-hover` 无边框 + `rounded-lg` | `ink-toolbar-toggle` 有边框 + `rounded-lg`(内置) |
| ReasoningChipButton | 自定义 `border px-3 py-1` + `rounded-full` | `ink-toolbar-chip` + `data-active` |
| 发送按钮 | Arco `<Button type="primary" shape="round">` | `<button className="ink-button">` |
| 渠道下拉触发 | `bg-white/92 shadow-xs` + `rounded-xl` | `ink-toolbar-chip` + 更大尺寸变体 |

### 6.2 聊天面板头部

| 元素 | 当前 | 改为 |
|------|------|------|
| "新对话"按钮 | `bg-surface shadow-sm` + `rounded-full` 无边框 | `ink-button-secondary` 小尺寸 + pill |
| 历史记录触发器 | `bg-surface shadow-sm` + `rounded-full` 无边框 | `ink-toolbar-chip` + pill 变体 |
| 删除对话按钮 | Arco `<Button type="text" status="danger" shape="circle">` | `ink-icon-button` + danger 色 |

### 6.3 Skill 面板

| 元素 | 当前 | 改为 |
|------|------|------|
| 面板背景 | `bg-[rgba(249,246,239,0.92)]` | `bg-surface` + `backdrop-blur` |
| 选项卡片激活态 | `border-accent-primary-muted bg-[rgba(238,244,234,0.86)]` | `border-accent-primary-muted bg-accent-primary-soft` |
| Skill 触发器 | 自定义 `bg-white shadow-xs` | `ink-toolbar-chip` |
| 普通/会话 Skill 按钮 | 自定义 `rounded-full border px-2.5` | `ink-toolbar-chip` + `data-active` |

### 6.4 消息气泡操作按钮

| 元素 | 当前 | 改为 |
|------|------|------|
| 复制/追加/新建 | Arco `<Button size="mini" shape="round" type="secondary">` | `<button className="ink-button-secondary text-xs h-7 px-2.5">` |
| Markdown 复制 | 自定义 `bg-white shadow-xs` | `ink-button-secondary` 小尺寸 |

---

## 七、影响范围

### 7.1 必改文件

| 文件 | 改动类型 |
|------|---------|
| `globals.css` | Token 更新 + 新增 CSS 类 |
| `studio-chat-composer.tsx` | 替换所有自定义按钮为 ink-toolbar-* |
| `studio-chat-message-bubble.tsx` | 替换 Arco Button 为 ink-button-secondary |
| `studio-chat-history-panel.tsx` | 替换 Arco Button + 新对话/历史触发器 |
| `studio-chat-skill-panel.tsx` | 替换硬编码颜色 + 自定义按钮 |
| `ai-chat-panel.tsx` | 替换硬编码颜色 |
| `auth-form.tsx` | 提取渐变背景为 CSS 变量 |
| `workspace-shell.tsx` | 替换硬编码 rgba |
| `incubator-chat-panel.tsx` | 替换 Arco Button + 硬编码 rgba/渐变 |
| `incubator-chat-panel-support.tsx` | 替换 Arco Button + 硬编码 rgba |
| `incubator-chat-draft-panel-support.tsx` | 替换 Arco Button (2处) |
| `incubator-chat-draft-guidance.tsx` | 替换 Arco Button |
| `incubator-chat-history-panel.tsx` | 替换 Arco Button (2处) + 硬编码颜色 |
| 所有含 callout 横幅的组件 | 替换为 callout-* 类 |

### 7.2 可能影响但低风险

| 文件 | 改动类型 |
|------|---------|
| `document-tree.tsx` | `bg-[#b0bac8]` → token |
| `markdown-document-editor.tsx` | `bg-[#ffffff]` → `bg-surface` |
| `json-document-editor.tsx` | `bg-[#ffffff]` → `bg-surface` + 补充 `accent-info` 引用 |
| `incubator-chat-panel.tsx` | 已升为必改 |
| `engine-export-panel.tsx` | 硬编码 rgba → callout-success 类 |
| `engine-task-form-panels.tsx` | 硬编码 rgba → callout-warning 类 |
| `config-registry-page-primitives.tsx` | 硬编码 rgba → callout-info 类 |
| `config-registry-skill-reader.tsx` | 硬编码 rgba → callout-info 类 |
| `credential-center-list.tsx` | 硬编码 rgba → token |
| `credential-center-form.tsx` | 硬编码 rgba → callout-info 类 |
| `lobby-project-shelf.tsx` | 硬编码 rgba → token |
| `assistant-preferences-form.tsx` | 硬编码 rgba → callout-warning 类 |
| `assistant-skill-editor.tsx` | 硬编码 rgba → callout-warning 类 |
| `assistant-hook-guided-fields.tsx` | 硬编码 rgba → callout-info 类 |
| `assistant-agent-guided-editor.tsx` | 硬编码 rgba → callout-info 类 |
| `assistant-getting-started-panel.tsx` | `bg-[linear-gradient(...)]` → CSS 变量 |
| `assistant-config-file-map-panel.tsx` | `bg-[linear-gradient(...)]` → CSS 变量 |
| `project-setting-summary-editor.tsx` | `rgba(196,136,61,...)` → callout-warning 类 |
| `project-setting-summary-panel.tsx` | `rgba(196,136,61,...)` → callout-warning 类 |
| `chapter-stale-notice.tsx` | 硬编码 rgba → callout-warning 类 |
| `app-select.tsx` | 硬编码 `rgba(183,121,31,...)` → callout-warning 类 |
| `incubator-panels-support.tsx` | 硬编码 `rgba(19,19,18,0.08)` → token |
| `incubator-preview.tsx` | `accent-info` 引用（需确保 token 存在） |
| `incubator-chat-settings-panel.tsx` | 硬编码 rgba → callout-info 类 |

### 7.3 不改

- 组件内部逻辑、状态管理、API 调用
- 布局结构（grid/flex 排列方式）
- 文案内容
- 暗色模式（下一阶段）

### 7.4 暗色模式前置说明

本轮新增的所有 Token（`--callout-*`、`--toolbar-*`、`--chat-*`、`--accent-info-*`）使用了 `rgba()` 硬编码透明度值。这些值基于浅色背景调校，在暗色模式下需要提供覆盖值。建议实施暗色模式时：
- 使用 `[data-theme="dark"]` 选择器覆盖所有 `--callout-*` 和 `--toolbar-*` token
- 或改用 `color-mix()` / 双层变量结构降低迁移成本

### 7.5 `ink-toolbar-chip` 与 `ink-toolbar-toggle` 公共基类

`ink-toolbar-chip` 和 `ink-toolbar-toggle` 除激活态选择器外样式完全一致，保留为两个独立类以支持未来差异化（chip 可能发展为下拉触发器，toggle 可能增加开关指示器）。当前实现中提取公共部分到注释标记，不引入额外基类以避免过度抽象。

---

## 八、验证标准

1. 所有页面在新主题色下按钮清晰可辨，不再和背景融为一体
2. Studio Composer 所有工具栏按钮有明确边框和背景区分
3. 全项目零硬编码 `bg-[rgba(...)]` / `border-[rgba(...)]` / `bg-[#hex]` 颜色值（例外：模板内联 CSS 如 `dangerouslySetInnerHTML` 中的可保留）
4. 零 Arco `<Button>` 直接使用（仅保留 Arco 组件内部渲染的按钮）
5. 圆角仅使用 4 个语义级别 token（sm/lg/2xl/pill），`--radius-xs` 和 `--radius-md` 保留为 ink-input/ink-tab 等现有 CSS 类内部引用
6. 色彩对比度满足 WCAG AA 标准
7. 现有功能不受影响（纯样式改动）
8. `ink-button` 的 loading 态需通过组件内条件渲染实现（替代 Arco Button 的 `loading` prop）
