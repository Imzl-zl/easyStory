# 项目设置页沉浸式体验升级 (Project Settings Immersive UI)

## 1. 目标与背景

**当前状况**：
在清理了大量的局部 CSS modules 并迁移至 Tailwind 和全局变量后，项目设置页面的基础架构变得清爽，但也失去了之前模块内精细打磨的布局约束和视觉层级。尤其是在宽屏显示器下，表单字段被无限拉伸（最大宽至 1600px 减去侧边栏宽度），导致视觉涣散、操作距离长，整体显得“low”且“空旷”。

**升级目标**：
参考国内主流的高级编辑器/内容创作平台（如语雀、飞书文档），为网文创作者提供一种“沉浸”、“克制”、“留白”的呼吸感体验。
核心动作：收敛阅读视宽，去除冗余的卡片与线框，增强特定交互的心理暗示，从而大幅提升产品的“高级感”与“易读性”。

## 2. 设计原则

*   **克制与留白 (Minimal & Breathing Space)**：不依赖过重的边框和渐变背景来区分内容区块，转而通过合理的间距（Spacing）和排版（Typography）来建立视觉层级。
*   **聚焦的心流 (Focused Flow)**：符合中文最佳阅读宽度（约 35-45 个汉字，折合 700px - 800px 宽），减少视线横向游移。
*   **细节感知 (Micro-interactions)**：通过微弱的状态提示（如未保存小圆点）和聚焦高亮（Focus Glow），在不打扰用户的前提下提供清晰的反馈。

## 3. 具体改造项 (Scope of Changes)

### 3.1 页面级布局重组 (Page Layout Constraints)
*   **骨架保持**：继续使用 `grid-cols-[280px_1fr]` 的双栏布局（断点 1024px）。侧边栏（`ProjectSettingsSidebar`）固定。
*   **内容区限宽 (Critical Change)**：在右侧的 `ProjectSettingsContent` （或者其内部的主体部分）中，引入一个最大宽度为 `max-w-3xl`（约 768px）且 `mx-auto` 的居中容器。
*   **卡片去壳**：移除包裹整个表单或整个面板的强阴影与厚重边框，使其融入主干背景。

### 3.2 项目设定表单重塑 (ProjectSettingEditor)
*   **视觉分组**：取消当前带有 `border-[var(--line-soft)] bg-gradient` 的沉重 `fieldset`。
*   **排版调整**：
    *   通过原生的 `h3` (结合 `text-lg font-semibold`) 来标识 “基本信息”、“角色设定”、“世界观”、“规模设定”。
    *   每组下方保持 `grid-cols-1 md:grid-cols-2`。但在 `max-w-3xl` 容器的限制下，两列的宽度会非常适中且紧凑。
*   **长文本域发光 (Focus Glow)**：“核心冲突”、“剧情走向”、“特殊要求”这三个需要重度思考的文本域，其外层容器在获得焦点时，应用微光发光效果（如 `focus-within:shadow-[0_0_0_3px_rgba(90,122,107,0.15)]` ），营造沉浸输入感。

### 3.3 交互细节补齐 (UX Polish)
*   **侧栏未保存提示 (Dirty Dot)**：
    *   在 `ProjectSettingsSidebar` 中，如果对应的 Tab 有未保存更改（根据传入的 `dirtyState`），在其图标或文案旁显示一个显眼但不刺眼的橙色小圆点（例如 `bg-accent-warning w-2 h-2 rounded-full`）。
*   **审计面板友好过滤 (Audit Filter)**：
    *   在 `ProjectAuditPanel` 的过滤输入框上方，提供中文预设的快速过滤胶囊（Pill / Button），如 “项目更新 (project.updated)”、“设置变更 (project.setting.updated)”。
    *   将面板内的操作人显示由底层语境向自然语言转换（例如：`actor` 展现为 `操作人`， `details` 展现为 `详情`）。

## 4. 技术实施要点

1.  **文件范围**：
    *   `project-settings-page.tsx` (布局容器调整)
    *   `project-settings-sidebar.tsx` (Dirty dot)
    *   `project-setting-editor.tsx` (表单重塑、去线框)
    *   `project-audit-panel.tsx` (过滤胶囊、文案)
2.  **样式策略**：全程复用 `globals.css` 中的现存 Token（如 `--line-soft`, `--text-secondary`, `--bg-surface`, `.ink-pill`），尽量避免新增大量一次性 CSS 代码。

## 5. 验收标准

1.  在 1920x1080 屏幕上，项目设定的表单内容不再占满全屏横向空间，而是稳稳居中于约 700~800px 的区域内。
2.  短字段（如姓名、身份）组之间通过留白自然区分，没有厚重的外边框。
3.  长文本域聚焦时有温和的高亮包裹效果。
4.  编辑任意设定字段后，侧边栏的“设定”Tab 立即出现橙色提示点。
5.  审计面板可以通过点击中文预设标签，正确筛选对应底层的事件类型。