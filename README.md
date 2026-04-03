# easyStory

easyStory 是一个面向小说创作的工作台项目，当前代码与正式文档真值主要位于：

- 后端：`apps/api`
- 前端：`apps/web`
- 配置：`config`
- 正式文档：`docs`

文档入口统一从 [docs/README.md](./docs/README.md) 进入。

## 文档使用顺序

1. 先看 [docs/README.md](./docs/README.md)
2. 再按需看 `docs/specs/*.md`
3. 再看 `docs/design/*.md`
4. `docs/plans/*.md` 默认只作为实施记录或历史背景

## 当前高频文档

- [系统架构设计](./docs/specs/architecture.md)
- [数据库设计](./docs/specs/database-design.md)
- [配置格式规范](./docs/specs/config-format.md)
- [Assistant 运行时与聊天主路径](./docs/design/20-assistant-runtime-chat-mode.md)
- [前端页面 / 组件 / 样式对照](./docs/ui/frontend-page-component-style-map.md)

## 目录

```text
apps/
  api/        后端实现
  web/        前端实现
config/       Skills / Agents / Hooks / MCP / Workflows
docs/         正式规格、设计、计划与 UI 文档
tools.md      稳定协作知识
memory.md     当前状态快照
```
