# easyStory UI 实施状态

| 字段 | 内容 |
|---|---|
| 文档类型 | 实施对齐记录 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-31 |
| 最后更新 | 2026-03-31 |

---

## 1. 文档角色总览

```text
ui-design.md             当前生效的产品语义与布局规格
implementation-guide.md 当前生效的实现约束与代码真值说明
ui-design-v2.md          探索草图归档，保留 ASCII 图，不作运行时真值
UI-V2-README.md          apps/web 目录下的前端入口说明与页面草图
globals.css              运行时样式 token 真值
tailwind.config.ts       对 globals.css 的工具映射
```

---

## 2. 已对齐的事实

### 2.1 样式真值

- 当前样式真值文件是 `apps/web/src/app/globals.css`
- Tailwind 4 接入方式是 `@import "tailwindcss";`
- token 命名以 `--bg-* / --line-* / --text-* / --accent-*` 为准
- `tailwind.config.ts` 应映射这套真实变量名，不再写 `--color-*` 平行体系

### 2.2 页面真值

当前真实主路径页面如下：

```text
/workspace/lobby
/workspace/lobby/new
/workspace/lobby/settings
/workspace/lobby/config-registry
/workspace/lobby/recycle-bin
/workspace/lobby/templates
/workspace/project/[projectId]/studio
/workspace/project/[projectId]/engine
/workspace/project/[projectId]/lab
/workspace/project/[projectId]/settings
```

当前不存在：

- `src/app/demo/*`
- `globals-v2.css`
- `lobby-page-v2.tsx`
- `incubator-page-v2.tsx`
- `studio-page-v2.tsx`

### 2.3 结构真值

- 路由入口在 `src/app/**`
- 页面实现主要在 `src/features/**`
- 共享 UI 原件在 `src/components/ui/**`
- `cn` 工具真实路径是 `src/lib/utils/cn.ts`

---

## 3. 当前状态

### 已完成

- Creator-first 的页面语义已经收口到 `Lobby / Incubator / Studio / Engine / Lab`
- `globals.css`、`tailwind.config.ts`、`cn.ts` 这些基础设施文件已存在
- UI 文档已经拆分出“生效规格”和“提案归档”两种角色

### 进行中

- 更多页面细节与共享 UI 原件仍在持续收口
- Tailwind 与现有 CSS Module 的协作仍以渐进整合为主

### 不再使用的表达

- 不再把提案文档写成“已完成实现”
- 不再把概念草图写成真实文件结构
- 不再把 `--color-*` 写成当前运行时 token 真值

---

## 4. 使用方式

开发或评审 UI 时，按以下顺序读取：

1. `docs/ui/ui-design.md`
2. `docs/ui/implementation-guide.md`
3. `apps/web/src/app/globals.css`
4. 对应页面的 `src/app/**` 和 `src/features/**`

---

## 5. 快速检查清单

- [ ] 设计语义是否符合“创作工作台”，而不是后台管理
- [ ] ASCII 图是否保留，但没有伪装成真实文件树
- [ ] 文档状态是否明确区分“生效”和“提案”
- [ ] token 名称是否与 `globals.css` 一致
- [ ] 页面路径是否与 `src/app/**` 当前结构一致
