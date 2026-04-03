# 多用户 Assistant 配置优化（Phase 1）

> 文档状态：历史实施记录
>
> 当前 assistant / Studio 聊天主路径请以 [Assistant 运行时与聊天主路径](../design/20-assistant-runtime-chat-mode.md)、[系统架构设计](../specs/architecture.md) 和当前代码为准。本计划保留为当时的阶段性实施背景，不再单独代表当前运行时真值。

## 问题

当前 easyStory 的业务资源已经是多用户模型，但 AI 配置层仍偏单租户：

- 项目、凭证已按 `owner_id / owner_type` 隔离
- `skill / agent / hook / mcp / workflow` 仍主要是平台内置 YAML 资源
- 普通用户缺少一层“我自己的长期规则”
- 项目也缺少一层“这个项目固定遵守的规则”

这会导致产品心智错位：业务是多用户平台，AI 能力却更像管理员演示面板。

## 最优思路

不直接把全部 YAML 编辑器开放给普通用户，而是先补真正的规则层：

1. 系统内置层
平台维护的 skill / agent / workflow，继续保留。

2. 用户层
每个用户拥有自己的长期规则，类似 `CLAUDE.md` / Cursor User Rules。

3. 项目层
每个项目可以覆盖自己的题材口径、风格禁忌、叙事要求。

运行时注入顺序：

`系统内置提示 -> 用户长期规则 -> 当前项目规则`

后出现的规则更具体，优先级更高。

## 本阶段落地范围

- 支持 `user / project` 两种 scope
- Assistant 聊天运行时自动注入用户规则与项目规则
- 新增全局设置“个人规则”入口
- 新增项目设置“规则”入口
- 规则真值以文件为主：
  - `apps/api/.runtime/assistant-config/users/<user_id>/AGENTS.md`
  - `apps/api/.runtime/assistant-config/projects/<project_id>/AGENTS.md`
- 用户 AI 偏好同样走文件：
  - `apps/api/.runtime/assistant-config/users/<user_id>/preferences.yaml`

> 早期草案曾以数据库表承载规则层；当前正式实现已改为文件优先，以符合多用户 agent 配置的可见、可迁移、可版本化心智。

## 暂不纳入本阶段

- 用户自定义 MCP 连接器
- 用户自定义 Assistant 资源编排
- 用户自定义 Workflow 编辑器
- `hook.script` 类服务端执行能力开放

这些属于后续阶段，必须建立在规则层先稳定的前提上。
