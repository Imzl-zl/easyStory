# easyStory UI 说明

这个文件说明 `apps/web` 当前的创作者产品 UI 基线。下面的 ASCII 图保留用于表达页面语义和布局草图，但它们不是独立 demo 路由，也不是另一套 `v2` 文件结构。

---

## 1. 当前入口

### 启动

```bash
pnpm --dir apps/web dev
```

### 主路径页面

```text
/workspace/lobby
/workspace/lobby/new
/workspace/project/[projectId]/studio
/workspace/project/[projectId]/engine
/workspace/project/[projectId]/lab
```

### 真实代码结构

```text
apps/web/
├── src/app/**                 # 路由入口
├── src/features/**            # 页面与业务模块实现
├── src/components/ui/**       # 共享 UI 原件
├── src/lib/**                 # api / store / hooks / utils
├── src/app/globals.css        # 运行时样式 token 真值
└── tailwind.config.ts         # Tailwind 工具映射
```

当前不存在单独的 `globals-v2.css`、`/demo` 页面或 `*-page-v2.tsx` 文件。

---

## 2. 设计方向

这轮 UI 的核心不是“做一套新后台”，而是把 easyStory 收口成创作者产品：

- 从“填表配置”到“对话生成”
- 从“后台管理”到“创作伙伴”
- 从“固定流程”到“灵活编排”

---

## 3. 页面草图

### 3.1 Lobby（书架）

Lobby 是作品入口，不是项目管理后台。

```text
┌──────────────────────────────────────────┐
│  轻导航              主舞台               │
│  ├─ 我的作品         ├─ 页面标题         │
│  ├─ 我的助手         ├─ 搜索与筛选       │
│  ├─ 模板库           ├─ 统计信息         │
│  └─ 回收站           └─ 项目卡片网格     │
└──────────────────────────────────────────┘
```

表达原则：

- 项目卡片更像“书卡”，不是“管理卡”
- 继续创作是主动作
- 设置和技术动作不抢视觉主位

### 3.2 Incubator（起稿）

Incubator 是把故事想法整理成可写项目的地方。

```text
┌──────────────────────────────────────────┐
│  对话区                预览区              │
│  ├─ 顶部引导           ├─ 当前草稿         │
│  ├─ 消息流             ├─ 生成的文档       │
│  └─ 输入区             └─ 创建项目动作     │
└──────────────────────────────────────────┘
```

表达原则：

- `AI 聊天` 是一起聊故事，不是配置向导
- `模板起稿` 是补齐必要信息，不是后台建表
- 预览区服务创作草稿，不展示后台资源树

### 3.3 Studio（创作桌面）

Studio 是写作主舞台，不是三块后台面板并排。

```text
┌──────────────────────────────────────────┐
│  结构树      正文主舞台      AI 助手      │
│  ├─ 设定     ├─ 标题栏       ├─ 消息流    │
│  ├─ 大纲     ├─ 编辑区       ├─ 上下文    │
│  └─ 正文     └─ 状态栏       └─ 输入区    │
└──────────────────────────────────────────┘
```

表达原则：

- 正文永远是主角
- 右栏是共创侧板，不是系统控制台
- 模型、工具、上传等会话能力应贴近输入区，不占顶部主位

---

## 4. 样式真值

运行时样式真值在：

- `apps/web/src/app/globals.css`
- `apps/web/tailwind.config.ts`

当前 token 命名以这几组为准：

```css
--bg-*
--line-*
--text-*
--accent-*
--shadow-*
--radius-*
--font-*
```

文档和代码都不应再并行维护一套 `--color-*` 作为当前真值。

---

## 5. 相关文档

- `docs/ui/ui-design.md`
- `docs/ui/implementation-guide.md`
- `docs/ui/ui-design-v2.md`
