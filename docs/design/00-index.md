# easyStory 功能设计索引

| 字段 | 内容 |
|---|---|
| 文档类型 | 设计索引 |
| 文档状态 | 生效 |
| 创建时间 | 2026-03-16 |
| 更新时间 | 2026-04-10 |

---

## 1. 使用方式

本目录只负责回答两件事：

1. 当前有哪些正式设计文档
2. 不同主题应该优先看哪一份

详细需求、约束和实现边界以对应设计文档本身为准。

> `docs/plans/` 默认是实施记录，不替代本目录和 `docs/specs/` 的正式设计真值。
>
> assistant runtime 当前正式入口直接看 [20-assistant-runtime-chat-mode](./20-assistant-runtime-chat-mode.md)、[22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)、[23-provider-tool-interop-compatibility-layer](./23-provider-tool-interop-compatibility-layer.md)、[21-assistant-project-document-tools](./21-assistant-project-document-tools.md) 和 [模型协议与工具调用标准](../specs/model-protocols/README.md)；其中 23 与 model-protocols 已覆盖 shared runtime 的 tool/stream codec、conformance probe、`interop_profile`、transport-mode 工具能力验证以及 Credential Center 工具验证语义。若需要查看 2026-04-07 这轮收口的历史过程，再看 [Assistant Runtime 文档重构计划](../plans/2026-04-07-assistant-runtime-doc-refactor.md)。

---

## 2. 建议阅读顺序

1. [01-core-workflow](./01-core-workflow.md)
2. [20-assistant-runtime-chat-mode](./20-assistant-runtime-chat-mode.md)
3. [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)
4. [23-provider-tool-interop-compatibility-layer](./23-provider-tool-interop-compatibility-layer.md)
5. [21-assistant-project-document-tools](./21-assistant-project-document-tools.md)
6. [06-creative-setup](./06-creative-setup.md)
7. [19-pre-writing-assets](./19-pre-writing-assets.md)
8. [02-context-injection](./02-context-injection.md)
9. [03-review-and-fix](./03-review-and-fix.md)

---

## 3. 模块总览

| 编号 | 模块 | 文件 | 优先级 | 说明 |
|---|---|---|---|---|
| 01 | 核心工作流 | [01-core-workflow](./01-core-workflow.md) | 🔴 | 节点系统、执行绑定、状态机 |
| 02 | 上下文注入 | [02-context-injection](./02-context-injection.md) | 🔴 | 注入层级、预算、裁剪 |
| 03 | 审核精修 | [03-review-and-fix](./03-review-and-fix.md) | 🔴 | ReviewResult、聚合规则、精修策略 |
| 04 | 章节生成 | [04-chapter-generation](./04-chapter-generation.md) | 🔴 | 章节循环、拆分、恢复 |
| 05 | 内容编辑 | [05-content-editor](./05-content-editor.md) | 🔴 | 版本、编辑影响、stale 传播 |
| 06 | 创作设定 | [06-creative-setup](./06-creative-setup.md) | 🔴 | `ProjectSetting` 建立与维护 |
| 07 | 小说分析 | [07-novel-analysis](./07-novel-analysis.md) | 🟡 | 上传、采样、分析、Skill 生成 |
| 08 | 成本控制 | [08-cost-and-safety](./08-cost-and-safety.md) | 🔴 | 预算、安全阀、重试边界 |
| 09 | 错误处理 | [09-error-handling](./09-error-handling.md) | 🔴 | 失败分类、重试、显式暴露 |
| 10 | 用户与凭证 | [10-user-and-credentials](./10-user-and-credentials.md) | 🔴 | 用户、项目、模型凭证 |
| 11 | 导出 | [11-export](./11-export.md) | 🔴/🟡 | TXT / Markdown 基础导出与扩展 |
| 12 | 流式输出 | [12-streaming-and-interrupt](./12-streaming-and-interrupt.md) | 🟡 | SSE、中断、停止语义 |
| 13 | AI 偏好学习 | [13-ai-preference-learning](./13-ai-preference-learning.md) | 🟡 | 偏好学习与注入治理 |
| 14 | 伏笔追踪 | [14-foreshadowing-tracking](./14-foreshadowing-tracking.md) | 🟡 | 伏笔生命周期与提醒 |
| 15 | 写作面板 | [15-writing-dashboard](./15-writing-dashboard.md) | 🟡 | 指标、趋势、可视化 |
| 16 | MCP 架构预留 | [16-mcp-architecture](./16-mcp-architecture.md) | 🔴 | MCP client / server 分层约束 |
| 17 | 跨模块契约 | [17-cross-module-contracts](./17-cross-module-contracts.md) | 🔴 | 幂等、模板安全、删除边界 |
| 18 | 数据备份 | [18-data-backup](./18-data-backup.md) | 🟡 | 回收站、执行日志、Prompt 回放 |
| 19 | 前置创作资产 | [19-pre-writing-assets](./19-pre-writing-assets.md) | 🔴 | 设定、大纲、开篇、章节衔接 |
| 20 | Assistant 主路径 | [20-assistant-runtime-chat-mode](./20-assistant-runtime-chat-mode.md) | 🔴 | 普通聊天、规则、Skill、Agent、MCP 分层 |
| 21 | Assistant 项目文稿工具 | [21-assistant-project-document-tools](./21-assistant-project-document-tools.md) | 🟡 | 项目内文稿读写工具、统一路径路由、目录/版本/revision 约束 |
| 22 | Assistant 原生 Tool-Calling Runtime | [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md) | 🔴 | ordinary chat tool loop、provider 适配、run/step 真值与 SSE 语义 |
| 23 | 模型工具调用兼容层 | [23-provider-tool-interop-compatibility-layer](./23-provider-tool-interop-compatibility-layer.md) | 🔴 | canonical tool contract、协议族适配、gateway profile 与 conformance 验证 |

---

## 4. 主题映射

按主题找文档时，优先这样看：

- Assistant / Studio 聊天：`20 -> 22 -> 23 -> 21 -> specs/architecture -> specs/config-format`
- 创作准备链路：`06 -> 19 -> 04 -> 05`
- Workflow / 审核 / 上下文：`01 -> 02 -> 03 -> 08 -> 09`
- 凭证 / 用户 / 配置：`10 -> specs/config-format -> specs/database-design`
- UI 页面实现：`docs/ui/README.md`

---

## 5. 维护约束

- 新增正式设计时，先补这里的索引，再补对应 `docs/specs/` 或 `docs/design/`
- 若某份设计已废弃，应在这里移除或改状态，不保留第二套入口
- 不再在本文件维护过长的 MVP 清单、阶段性任务清单和历史验收表
