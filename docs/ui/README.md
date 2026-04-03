# easyStory UI 文档导航

| 字段 | 内容 |
|---|---|
| 文档类型 | UI 索引 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-01 |
| 更新时间 | 2026-04-03 |

---

## 1. 当前可用文档

| 文档 | 作用 |
|---|---|
| [frontend-page-component-style-map.md](./frontend-page-component-style-map.md) | 页面路由、主组件、样式真值与查找路径 |
| [project-settings-ui-redesign.md](./project-settings-ui-redesign.md) | 项目设置页的结构、交互边界和优化方向 |

---

## 2. 使用顺序

如果你要定位前端页面或样式，先看：

1. [frontend-page-component-style-map.md](./frontend-page-component-style-map.md)
2. 当前页面对应的 `apps/web/src/features/**`
3. `apps/web/src/app/globals.css`
4. `apps/web/tailwind.config.ts`

如果你要看项目设置页，再补：

1. [project-settings-ui-redesign.md](./project-settings-ui-redesign.md)
2. `apps/web/src/features/project-settings/components/*`
3. `apps/web/src/features/settings/components/*`

---

## 3. 当前边界

- `docs/ui/` 只保留当前仍有维护价值的 UI 文档
- 历史草图、一次性实施稿、失效路径说明不再保留为默认入口
- 页面实现真值始终以当前代码为准，UI 文档只负责帮助定位与解释
