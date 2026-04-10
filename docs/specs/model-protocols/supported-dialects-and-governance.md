# 支持范围与治理规则

| 字段 | 内容 |
|---|---|
| 文档类型 | 技术规范 / 治理规则 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-10 |
| 更新时间 | 2026-04-10 |
| 关联文档 | [模型协议与工具调用标准](./README.md)、[easyStory 采用映射](./easystory-adoption-profile.md) |

---

## 1. 目标

本文定义一套可跨项目复用的 agent runtime 协议基线。

它不描述某个具体产品的字段名、数据库列名或 UI 动作，而描述：

- 先应该覆盖哪些主流协议族
- 运行时内部应该抽象哪些 canonical contract
- 如何把厂商协议事实与项目实现策略分层

## 2. 建议先覆盖的 4 个协议族

如果目标是做一个能稳定支持主流 agent / tool-calling 的通用 runtime，建议先覆盖这 4 个协议族：

- `openai_responses`
- `openai_chat_completions`
- `anthropic_messages`
- `gemini_generate_content`

原因：

- 这是当前主流 agent / tool-calling 场景里最常见的四类协议形态
- 它们能覆盖大部分直连官方接口与大量兼容网关的基础形态
- 其余很多渠道本质上只是其中某一族的变体，不应一开始就被建模成全新的协议族

## 3. 渠道、网关与协议族要分层

标准分层应保持：

- `protocol_family`
  - 协议族，例如 `openai_responses`
- `provider`
  - 厂商，例如 OpenAI / Anthropic / Google
- `gateway`
  - 具体中转或代理
- `profile`
  - 同一协议族下的实现差异或兼容性变体

原则：

- 不要把渠道品牌名直接写成新的 `api_dialect`
- 不要把“某个网关能跑”误写成“新的协议标准”
- 能用 profile 表达的差异，不要上升为新的协议族

## 4. 一个可移植 runtime 至少需要的 canonical contract

建议内部先抽象这些对象，再做协议映射：

- `ConnectionProfile`
  - 鉴权方式、base URL、协议族、客户端身份、网关 profile
- `CanonicalRequest`
  - 模型、消息、系统指令、生成参数、工具声明、续接上下文、响应格式
- `CanonicalTool`
  - 工具名、描述、参数 schema、信任等级、是否只读、是否需要审批
- `CanonicalToolCall`
  - tool name、call id、arguments、provider payload
- `CanonicalToolResult`
  - status、structured output、error、审计信息
- `CanonicalResponse`
  - content、finish reason、usage、tool calls、provider response id
- `CanonicalStreamEvent`
  - text delta、tool delta、reasoning delta、terminal response

## 5. 标准与实现要分层

标准文档只写这三类内容：

- 官方协议事实
- 可移植的 runtime 设计建议
- 跨协议的稳定最小交集

不应直接混入：

- 某个项目自己的字段名
- 某个项目自己的审批流程
- 某个项目自己的数据库列
- 某个产品页签上的验证按钮文案

如果某个项目需要记录“本仓库当前怎么落地”，应单独维护 adoption profile。  
本仓库对应文档见 [easyStory 采用映射](./easystory-adoption-profile.md)。

## 6. 官方事实与推荐策略要分开写

写协议文档时必须显式区分：

- `官方事实`
  - 来自官方 API 参考、官方工具调用指南、官方结构化输出文档
- `推荐策略`
  - 为了跨协议稳定性而做的工程建议
- `项目采用`
  - 某个项目当前实际采用的配置和门控

例如：

- “Anthropic `max_tokens` 必填”是官方事实
- “多协议本地 tool loop 默认关闭并行 tool call”是推荐策略
- “某项目把流式和非流工具能力分成两个持久化字段”是项目采用

## 7. 对 agent runtime 的治理建议

- 先做协议族适配器，再做网关 profile，不要先堆 provider 分支
- 工具名、tool schema、tool result continuation 必须统一通过 canonical codec 处理
- 流式 reader 和协议状态机要分离，避免把 transport 问题和协议解析问题混在一起
- 工具能力验证应覆盖“定义可接受、真实会调、结果能续接”三个层次，不只做文本探活
- mutation 工具必须显式建审批模型，不要和只读工具混在一套静默策略里

## 8. 一句话边界

本目录里的标准文档，目标是“换个项目也能直接参考建 agent runtime”。  
某个项目自己的字段名、审批门槛、按钮文案和工具面，不属于这里的标准层。
