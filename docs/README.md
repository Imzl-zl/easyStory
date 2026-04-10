# easyStory 文档导航

| 字段 | 内容 |
|---|---|
| 文档类型 | 索引 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-02 |
| 更新时间 | 2026-04-10 |

---

## 1. 技术规范

| 文档 | 状态 | 说明 |
|---|---|---|
| [技术栈确定](./specs/tech-stack.md) | 生效 | 技术选型与运行时基线 |
| [系统架构设计](./specs/architecture.md) | 生效 | 模块化单体、分层与边界 |
| [数据库设计](./specs/database-design.md) | 生效 | 数据模型和真值源 |
| [配置格式规范](./specs/config-format.md) | 生效 | Skills / Agents / Hooks / Workflows 配置 |
| [模型协议与工具调用标准](./specs/model-protocols/README.md) | 生效 | 可跨项目复用的模型协议与 agent runtime 标准入口 |
| [easyStory 采用映射](./specs/model-protocols/easystory-adoption-profile.md) | 生效 | 本项目对模型协议标准的字段、验证与工具面映射 |
| [主流模型厂商请求参数参考](./specs/model-provider-request-params-reference.md) | 参考 | 更宽口径的市场请求格式、thinking、上下文窗口与输出上限资料 |
| [主流模型厂商请求头与客户端标识参考](./specs/model-provider-client-identity-and-headers-reference.md) | 参考 | 更宽口径的鉴权头、兼容层与浏览器边界资料 |
| [主流模型厂商响应结构与流式事件参考](./specs/model-provider-response-contract-reference.md) | 参考 | 更宽口径的响应体、SSE 事件与返回头资料 |

---

## 2. 设计与计划

| 目录 | 说明 |
|---|---|
| [design/](./design/) | 功能设计与跨模块契约 |
| [plans/](./plans/) | 实施计划与落地路线 |
| [ui/README.md](./ui/README.md) | UI 设计与页面组件映射入口 |

---

## 3. 当前主文档

如果你要看“当前 assistant / 创作聊天主路径”，先读：

- [Assistant 运行时与聊天主路径](./design/20-assistant-runtime-chat-mode.md)
- [Assistant 原生 Tool-Calling Runtime 设计](./design/22-assistant-tool-calling-runtime.md)
- [Assistant 项目文稿工具设计](./design/21-assistant-project-document-tools.md)
- [模型协议与工具调用标准](./specs/model-protocols/README.md)
- [系统架构设计](./specs/architecture.md)
- [配置格式规范](./specs/config-format.md)

如果你要判断“哪些文档是当前真值”，按这个顺序看：

1. `docs/specs/*.md`
2. `docs/design/*.md`
3. 当前代码
4. `docs/plans/*.md`

`plans/` 默认视为实施记录或历史方案，不应直接覆盖 `specs/`、`design/` 和当前代码。

---

## 4. 使用说明

- 查“可跨项目复用的模型协议和 agent runtime 标准”时，先看 [模型协议与工具调用标准](./specs/model-protocols/README.md)。
- 查“easyStory 当前如何采用这些标准”时，看 [easyStory 采用映射](./specs/model-protocols/easystory-adoption-profile.md)。
- 查“更宽口径的厂商资料或市场对比”时，再看 [主流模型厂商请求参数参考](./specs/model-provider-request-params-reference.md)、[主流模型厂商请求头与客户端标识参考](./specs/model-provider-client-identity-and-headers-reference.md)、[主流模型厂商响应结构与流式事件参考](./specs/model-provider-response-contract-reference.md)。
