# easyStory UI/UX 设计文档执行与对齐指南

## 1. 核心目标：消除"设计-代码"断层

将 docs/ui 文档从"宏观架构"转向"生产级真值"，重点补全已具备后端能力但缺失 UI 定义的子流程，统一路由定义与物理表现层。

---

## 2. P0 级核心补全：子页面与子流程（立即执行）

### 2.1 Incubator（新建项目向导）深度设计

- **关联位置**：`docs/ui/ui-design.md:53` / `docs/ui/ui-interaction-supplement.md:180`
- **后端真值**：`apps/api/app/modules/project/entry/http/router.py:87`（模板问答、自由对话、一键建项目）
- **前端现状**：`apps/web/src/features/lobby/components/lobby-page.tsx:131`（内联表单）
- **执行动作**：
  - 路由定义：统一为 `/workspace/lobby/new`
  - UI 补全：设计支持三条能力线的"分步向导"，替换当前的内联简易表单

### 2.2 Template Library & Management（模板管理）

- **关联位置**：`docs/ui/ui-interaction-supplement.md:35`（能力矩阵需新增）
- **后端真值**：`apps/api/app/modules/template/entry/http/router.py:22`（完整 CRUD）
- **执行动作**：
  - 路由定义：`/workspace/lobby/templates`
  - UI 补全：设计模板列表、模板详情查看、创建/编辑表单

### 2.3 Credential Center（凭证中心）精细化

- **关联位置**：`docs/ui/ui-design.md:55` / `docs/ui/ui-interaction-supplement.md:180`
- **前端组件**：`apps/web/src/features/settings/components/credential-center.tsx:54`
- **执行动作**：
  - UI 补全：增加"验证结果反馈（入纸感）"、"删除确认（带影响分析）"、"最近验证时间"及"异常文案定义"
  - 交互逻辑：明确用户级与项目级凭证的切换/覆盖 UI 逻辑

### 2.4 Audit Log（审计日志）视图

- **后端真值**：`apps/api/app/modules/observability/entry/http/router.py:38`
- **执行动作**：
  - 挂载点确认：项目审计挂载至 Project Settings Drawer；全局审计挂载至 `/workspace/lobby/settings?tab=audit`
  - UI 补全：设计轻量化审计流视图，对齐 Engine 的 JetBrains Mono 风格

---

## 3. P1 级系统化重构：配置注册与 Studio 增强

### 3.1 Config Registry Admin（配置注册中心）

- **后端真值**：`apps/api/app/modules/config_registry/entry/http/router.py:31`
- **执行动作**：
  - 路由定义：`/workspace/lobby/config-registry`
  - UI 补全：Skills / Agents / Hooks / Workflows 的管理入口、层级结构及 YAML 高亮表单设计

### 3.2 Studio 右侧辅助面板体系

- **关联位置**：`docs/ui/ui-design.md:176`
- **前端现状**：`apps/web/src/features/studio/components/studio-page.tsx:133`（已有 PreparationStatusPanel 等）
- **执行动作**：
  - UI 框架：统一折扇式侧板结构，支持 Version、Stale 章节提醒、影响面板等多面板切换

---

## 4. 结构性修正清单

| 修正项 | 目标位置 | 修改内容建议 |
|---|---|---|
| 能力矩阵 | `ui-interaction-supplement.md:35` | 补入：Template CRUD, Config Registry Admin, Audit Log |
| 路由定义 | `ui-interaction-supplement.md` 路由部分 | 补入：`/project/:projectId/settings?tab=audit` 等具体 Tab 路由 |
| 表现层定义 | `ui-design.md:53` | 澄清：明确哪些是独立 Page（如 Lobby），哪些是 Drawer（如 Project Settings），哪些是 Page Toggle |

---

## 5. 视觉组件规范（水墨流）

### 5.1 Incubator：多模式向导交互设计

**目标**：将"新建项目"从简单的表单提升为一种"开篇仪式感"。

**视觉方案**：

- 模式选择卡片：采用三列布局。卡片背景使用 `--bg-surface`（微黄纸感），边框在 Hover 时呈现"湿墨晕开"效果（淡灰色不规则阴影，而非硬质边框）
- 进度指示器：不使用传统的圆形步骤条，改用"横向展开的卷轴"进度条。已完成步骤显示为"浓墨实心点"，进行中为"水墨圆环"，未开始为"极淡虚线"

**关键交互**：

- 动态表单流：点击"模板问答"后，页面通过 `opacity` 和 `transform: translateY(10px)` 平滑过渡到问答界面
- 流式输入：自由对话模式下，AI 的引导语采用"墨迹渗入纸面"的动效（文字逐个浮现，伴随极微弱的模糊到清晰的变化）

**真值路由**：`/workspace/lobby/new?mode=template|chat|one-click`

### 5.2 Credential Center：验证与反馈样式

**目标**：让枯燥的 API 配置具备"确定感"与"安全性"。

**视觉方案**：

- 凭证状态印章：验证通过后，右侧不只是绿勾，而是一个类似"朱砂印章"的小图标（颜色使用 `--accent-success` 的变体），带轻微的印压纹理感
- 错误信息：验证失败时，输入框底部出现"红墨泼溅"般的警示线条（1px 不规则波浪线），配合 `--accent-danger` 文本

**微交互**：

- 验证动效：点击"Verify"时，按钮内部出现一个向外扩散的"水波纹"加载圈，模拟墨水滴入水中
- 敏感信息遮写：API Key 在非编辑态下显示为"浓墨涂抹"的长条，悬浮 0.5s 后平滑淡入显示前四位

**字段补充**：增加 Last Verified（最后验证时间）和 Dependency Count（关联项目数）的小字标签，字体使用 `--text-secondary`

### 5.3 Studio 侧边面板框架（Side Panel Framework）

**目标**：解决多任务面板切换时的视觉跳变。

**交互方案**：

- 折扇式开合：面板宽度固定在 320px-400px。展开时采用 `cubic-bezier(0.25, 1, 0.5, 1)` 曲线，模拟折扇打开的轻盈感
- 标签切换：侧边面板顶部的 Tab 切换不使用滑块，而是"宣纸叠加"感——选中态 Tab 的背景比未选中态稍微亮一点点，且边框有淡淡的墨色勾勒

**"Stale"（失效）状态深度设计**：

- 视觉表现：受影响的章节列表项背景色变为 `--bg-muted`（灰褐色），文字透明度降至 0.6，并在左侧边缘出现一条"干墨笔触"的垂直警示线
- 交互联动：点击面板中的"View Impact"，主编辑区的对应段落会产生瞬间的"纸面微颤"提示

### 5.4 Audit Log & Config Registry：高级视图规范

**目标**：处理高密度信息，保持可读性。

**Audit Log 时间轴**：

- 采用垂直极细墨线连接。每个记录点是一个"墨迹点"，Hover 时墨迹点会像水滴一样变大
- 日志详情（Payload）背景采用"方格信纸"（Grid Paper）纹理（极淡的灰色格线），配合 JetBrains Mono 字体

**Config Registry 编辑器**：

- 代码背景：放弃纯黑或纯白背景，采用"浓墨背景"（暗灰色 `#1A1A1A`），代码高亮使用水墨色系：枯草黄（关键字）、石青蓝（函数）、胭脂红（错误）
- 校验反馈：Schema 错误直接在行号处显示一个"X"形的红色笔画

### 5.5 枯墨与润墨的状态隐喻（Ink Texture Metaphor）

**目标**：无需阅读文字标签，用户凭视觉直觉即可判断内容的"新鲜度"。

**润墨（Active）状态**：

- 适用场景：正在编辑或刚生成的内容
- 视觉表现：边缘有极轻微的"湿润感"，通过 `text-shadow: 0 0 2px rgba(46, 111, 106, 0.15)` 实现极淡的晕染
- CSS 实现：
  ```css
  .content-active {
    text-shadow: 0 0 2px rgba(46, 111, 106, 0.15);
  }
  ```

**枯墨（Stale）状态**：

- 适用场景：失效内容，需要重新生成
- 视觉表现：透明度降低 + "枯笔"纹理效果，暗示内容已"干涸"
- CSS 实现：
  ```css
  .content-stale {
    opacity: 0.6;
    mask-image: url('data:image/svg+xml,...'); /* 叠加噪点纹理 */
    -webkit-mask-image: url('data:image/svg+xml,...');
  }
  ```

**状态对比表**：

| 状态 | 视觉隐喻 | 用户感知 |
|---|---|---|
| Active（润墨） | 边缘晕染、微湿润感 | 新鲜、可继续编辑 |
| Stale（枯墨） | 干涸纹理、透明度降低 | 过时、需重新生成 |

### 5.6 长卷滚动条设计（Long Scroll Interaction）

**目标**：将枯燥的滚动行为转化为"浏览长卷"的沉浸式体验。

**适用场景**：Audit Log、Engine 日志流、Config Registry 列表

**视觉方案**：

- 滚动条轨道：设计为一根"细长笔杆"，颜色使用 `--bg-muted`
- 滚动条滑块：设计为"笔头"，颜色使用 `--accent-ink`
- 蘸墨效果：随着滚动位置向下，笔头部分呈现"蘸墨"的深浅变化（顶部浅、底部深）

**CSS 实现**：

```css
/* 长卷滚动条 */
.long-scroll::-webkit-scrollbar {
  width: 8px;
}

.long-scroll::-webkit-scrollbar-track {
  background: var(--bg-muted);
  border-radius: 4px;
}

.long-scroll::-webkit-scrollbar-thumb {
  background: linear-gradient(
    to bottom,
    rgba(46, 111, 106, 0.3),
    rgba(46, 111, 106, 0.8)
  );
  border-radius: 4px;
}

.long-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--accent-ink);
}
```

**无障碍降级**：

- `prefers-reduced-motion: reduce` 时，滚动条恢复为浏览器默认样式
- 确保滚动条宽度不小于 8px，保证可操作性

---

## 6. 前端组件与交互实现细节（代码级）

### 6.1 Incubator 状态机与流程细节

#### 核心状态定义（TypeScript）

```typescript
type IncubatorState = 
  | 'SELECT_MODE'   // 模式选择（三路：模板、自由、一键）
  | 'FILL_FORM'     // 表单填写 / 对话输入
  | 'VALIDATING'    // 前端/后端校验
  | 'ERROR'         // 校验失败（重试态）
  | 'SUCCESS';      // 进入 Studio
```

#### 状态流转图

```
IDLE -> SELECT_MODE -> FILL_FORM -> VALIDATING -> SUCCESS -> STUDIO
                          ↓              ↓
                       CANCEL         ERROR -> RETRY
```

#### 关键交互细节

| 交互点 | 实现方案 |
|---|---|
| 模式切换动效 | `transform: translateX(-20px) -> 0`，`opacity: 0 -> 1`，持续 300ms |
| 流式对话文字 | 每 50ms 改变一个字符的透明度，模拟"墨水慢慢渗出"效果，避免打字机硬动效 |
| 进度指示器 | 横向卷轴式：已完成=浓墨实心点，进行中=水墨圆环，未开始=极淡虚线 |

### 6.2 响应式布局断点细节

#### Template Library（模板库）

| 断点 | 布局方案 |
|---|---|
| `>= 1024px` | 左侧卡片墙（Grid, 3 columns）+ 右侧常驻详情侧板 |
| `768px - 1023px` | 双列卡片 + 点击后右侧抽屉详情 |
| `< 768px` | 单列卡片，详情以"全屏抽屉（Bottom Sheet）"从底部弹起 |

#### Config Registry（配置中心）

| 断点 | 布局方案 |
|---|---|
| `>= 1024px` | 双栏：左侧配置树 + 右侧编辑区 |
| `768px - 1023px` | 隐藏侧边配置树，改为顶部 Breadcrumb/Select 导航 |
| `< 768px` | 编辑器默认 readOnly，点击"墨滴"浮标进入全屏编辑，防止键盘遮挡 |

### 6.3 "水墨流"无障碍降级细节

#### CSS 降级规则

```css
@media (prefers-reduced-motion: reduce) {
  .ink-ripple,
  .fan-open {
    transition: none !important;
    animation: none !important;
  }
  .ink-ripple::after {
    display: none; /* 移除动态水波纹 */
  }
  .seal-stamp {
    transform: none !important; /* 印章无缩放动画 */
  }
}
```

#### 降级映射表

| 原始效果 | 降级后效果 |
|---|---|
| 墨滴波纹 | 简单 opacity 过渡 |
| 折扇开合 | 线性展开（无曲线） |
| 流式文字浮现 | 直接显示 |
| 朱砂印章按压 | 静态背景色高亮 |

### 6.4 异常态与空态的"水墨风"文案设计

#### 空态文案（Empty States）

| 场景 | 文案 |
|---|---|
| 模板库为空 | "书案初设，尚无典籍。点击'创建模板'，为你的创作定下法度。" |
| 审计日志为空 | "雪地无痕，暂无往来行迹。待你落笔生花，此处自见功过。" |
| Config Registry 为空 | "机枢未发，灵窍尚待开启。" |
| 无项目 | "空山新雨，静候佳作。点击'新建项目'，开启你的创作之旅。" |

#### 失败态样式（Red Ink Splash）

| 元素 | 实现方案 |
|---|---|
| 错误提示背景 | 使用 `mask-image` 配合"淡墨泼溅"SVG 作为底纹 |
| 错误文字颜色 | `#B2412E`（朱砂红） |
| 输入框错误边框 | 1px 不规则波浪线，模拟"红墨泼溅" |

### 6.5 执行 Roadmap：第一个技术任务

**建议首个任务：实现 CredentialCenter 的"朱砂印章"组件**

#### 选择理由

1. 代码改动量小，见效快
2. 是验证"水墨美学"与"功能反馈"结合的最佳实验场
3. 可复用于后续其他验证场景

#### 技术实现细节

```tsx
// CredentialSeal.tsx - 朱砂印章组件原型
import { motion } from 'framer-motion';

const CredentialSeal = ({ isValid }: { isValid: boolean }) => {
  return (
    <motion.div
      className="seal-stamp"
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: [0.8, 1.1, 1], opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 1, 0.5, 1] }}
      style={{
        width: 24,
        height: 24,
        borderRadius: '50%',
        background: isValid ? 'var(--accent-success)' : 'var(--accent-danger)',
        boxShadow: 'inset 0 0 4px rgba(0,0,0,0.3)', // 印压纹理感
      }}
    >
      {isValid ? '✓' : '✗'}
    </motion.div>
  );
};
```

#### 视觉细节

| 属性 | 值 |
|---|---|
| 尺寸 | 24px × 24px |
| 颜色 | 成功：`var(--accent-success)`；失败：`var(--accent-danger)` |
| 动画曲线 | `cubic-bezier(0.25, 1, 0.5, 1)` |
| 纹理 | `box-shadow: inset 0 0 4px rgba(0,0,0,0.3)` 模拟印压感 |

---

## 7. 完整执行真值表

| 模块 | 子路由/Tab | 核心交互手势 | 关键视觉 Token | 后端 API |
|---|---|---|---|---|
| Incubator | `/new/:step` | 左右滑动翻页感 | `--bg-canvas` 叠加 3% 噪点纹理 | `POST /api/projects` |
| Templates | `/templates/:id` | 卡片"入纸"阴影 | `--accent-ink` 描边 | `GET/POST/PUT/DELETE /api/templates` |
| Credential | `/settings/credentials` | 按钮点击"墨滴"波纹 | `--accent-success` 朱砂印章感 | `GET/POST/PUT/DELETE /api/credentials` |
| Audit Log | `?tab=audit` | 滚动时时间轴动态生长 | `--text-secondary` 极细灰线 | `GET /api/observability/audit` |
| Config Admin | `/config/:type` | 侧边树状结构"折纸"层级 | `--bg-muted` 方格底纹 | `GET/PUT /api/config-registry/{type}` |

---

## 8. 后续执行步骤

1. **文档同步**：更新 `ui-interaction-supplement.md` 的能力矩阵和路由定义
2. **组件原型**：先实现 `CredentialSeal` 组件验证水墨美学
3. **前端 Task 化**：将 P0 级 UI 补全拆分为具体 Issue
4. **评审确认**：前后端负责人确认真值后开始大规模开发
