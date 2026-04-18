# easyStory Framework-First 深度重构计划

| 字段 | 内容 |
|---|---|
| 文档类型 | 深度重构计划 |
| 文档状态 | 提议 |
| 创建时间 | 2026-04-18 |
| 更新时间 | 2026-04-18 |
| 关联文档 | [技术栈确定](../specs/tech-stack.md)、[系统架构设计](../specs/architecture.md)、[Assistant 运行时与聊天主路径](../design/20-assistant-runtime-chat-mode.md)、[Assistant Tool Calling Runtime](../design/22-assistant-tool-calling-runtime.md)、[模型工具调用兼容层设计](../design/23-provider-tool-interop-compatibility-layer.md)、[LiteLLM Southbound Integration Plan](./2026-04-16-litellm-southbound-integration-plan.md) |

## 1. 背景与目标

当前 easyStory 已经把一部分模型 southbound 复杂度收口到了 `LiteLLM + native_http backend`，但 assistant runtime、workflow runtime 与通用 agent/tool loop 仍有较多自研运行时逻辑。近期问题表现不是“某个点坏了”，而是：

- 一处修完，另一处继续出错
- assistant / tool / provider / hook / workflow 互相牵连
- shared/runtime 的协议边界虽然在收口，但 assistant 主链仍承载了较多通用 runtime 复杂度

本计划的目标不是“把 easyStory 改成一个通用 agent 平台”，而是反过来：

1. **能交给框架的通用运行时，尽量交给框架**
2. **只有小说产品独有的真值和业务语义留在 easyStory 内部**
3. **通过分阶段替换，降低继续修补自研底座的维护成本**

本计划采用的总原则是：

- `LangGraph`：承接状态化工作流、恢复、中断、人工确认等通用 graph runtime
- `LangChain`：承接高层 agent 便利层、middleware、MCP adapter、常见 multi-agent 模式
- `LiteLLM`：承接 southbound 多模型网关
- easyStory：继续持有 `project / content / review / context / workflow` 业务真值

同时，本轮还要一起纠正一个领域建模问题：

- **不再把 `ProjectSetting` 当创作主真值**
- 长期设定真值回到项目文稿
- 如果仍保留结构化对象，它只能是 `ProjectBrief / ProjectDigest` 一类派生摘要，不再是创作根对象

### 1.1 本轮采用“硬切换”，不做旧方案兼容

本轮重构不是在旧系统上继续做兼容演进，而是明确采用**硬切换 + 重新开始**的策略。

明确约束：

1. **不兼容旧运行时路径**
   - 不保留旧 assistant runtime 的长期兼容入口
   - 不保留旧 workflow 状态机的兼容执行路径
   - 不保留“新旧两套实现按配置切换”的长期模式
2. **不兼容旧运行时数据**
   - 旧 `turn run / tool step / workflow snapshot / tool loop state` 不作为新主链运行前提
   - 旧中间状态、旧缓存、旧临时快照可以直接废弃
3. **不为了迁移旧数据污染新代码**
   - 如果确实要保留历史资料，只允许做一次性离线导出/归档
   - 不允许把迁移适配逻辑常驻在正式运行时
4. **不做“完美兼容”**
   - 不为历史字段、旧 DTO、旧 snapshot、旧目录结构长期保留兼容分支
   - 不以“老数据还能凑合跑”作为架构目标

这条策略的原因很直接：

- 当前最大问题不是“迁不迁得动”，而是“旧运行时包袱已经过重”
- 如果继续追求平滑兼容，最终只会把新框架实现再堆到旧胶水上
- 对当前项目阶段来说，**源码整洁和长期稳定**比保留旧运行时兼容更重要

### 1.2 为什么这次必须是“深度重构”，不是继续修补

这次不能再按“发现一个 bug 修一个 bug”的方式推进，原因不是 bug 数量多，而是**错误来源已经主要集中在自研通用 runtime 本身**：

- assistant 主链同时承担了产品真值和通用 agent runtime 两类职责
- workflow 主链虽然业务边界清楚，但图编排仍是自研 while-loop + 状态机
- Hook / MCP / provider / tool loop 之间虽然已有边界，但仍然高度依赖自研运行时胶水

继续局部修补的结果通常是：

1. 新逻辑必须适配旧运行时约束，复杂度继续上升
2. 同一条能力链横跨 assistant / workflow / shared runtime，改动面持续扩大
3. 测试只能证明“这次没坏”，不能证明底层结构已经稳定

因此本轮必须按**深度重构**理解：

- 优先替换通用运行时，不再继续为其堆补丁
- 先切职责，再切实现
- 完成某一阶段后，删除旧代码和旧路径，不保留长期双轨
- 不兼容旧 runtime 数据与旧执行路径，必要时直接重建

---

## 2. 当前源码判断

### 2.1 已经接近目标的层

#### 2.1.1 southbound 模型网关

当前 `shared/runtime/llm` 已经显式落成 backend 分层，核心入口包括：

- [llm_tool_provider.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_tool_provider.py)
- [litellm_backend.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/litellm_backend.py)
- [llm_backend.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/llm/llm_backend.py)

当前事实：

- 上层继续消费 `LLMGenerateRequest / NormalizedLLMResponse`
- 默认 backend 走 LiteLLM
- 不适合 LiteLLM 的场景显式走 `native_http backend`
- canonical tool name / schema / continuation 仍留在项目内 contract

结论：**这一层不应该再大改，只需要继续保持 shared runtime contract 稳定。**

#### 2.1.2 PluginRegistry / Hook / MCP 薄注册边界

当前 assistant / workflow 都已经通过统一注册器装配扩展能力，典型入口包括：

- [plugin_registry.py](/home/zl/code/easyStory/apps/api/app/shared/runtime/plugins/plugin_registry.py)
- [assistant_hook_providers.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/hooks_runtime/assistant_hook_providers.py)
- [workflow_hook_providers.py](/home/zl/code/easyStory/apps/api/app/modules/workflow/service/workflow_hook_providers.py)

当前事实：

- `script / webhook / agent / mcp` 已被统一挂在 registry 下
- Hook/MCP 还不是完全框架化，但注册边界已经比完全散落在业务层更稳

结论：**这层不需要推倒重来，后续只需要把 LangChain/MCP adapter 挂到现有薄边界后面。**

### 2.2 当前最脆弱、最值得替换的层

#### 2.2.1 assistant 通用 runtime 过重

当前 assistant 主链的通用运行时复杂度集中在：

- [assistant_service.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/assistant_service.py)（944 行）
- [assistant_tool_loop.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/tooling/assistant_tool_loop.py)（759 行）
- [assistant_turn_llm_bridge_support.py](/home/zl/code/easyStory/apps/api/app/modules/assistant/service/turn/assistant_turn_llm_bridge_support.py)

这部分已经承载了：

- turn / run 生命周期
- tool loop
- streaming tool loop
- continuation state
- tool policy / visibility
- step store / state snapshot
- recover / replay / cancel 语义

其中一部分是产品真值，但一大部分其实是**通用 agent runtime 复杂度**。这也是为什么这里最容易出现“修一处、坏一片”。

结论：**assistant 主链需要 framework-first 重构，但不能整块直接替换。**

#### 2.2.2 workflow 当前仍是轻量自研状态机 + while loop

当前 workflow engine 主链包括：

- [workflow_engine.py](/home/zl/code/easyStory/apps/api/app/modules/workflow/engine/workflow_engine.py)（56 行）
- [state_machine.py](/home/zl/code/easyStory/apps/api/app/modules/workflow/engine/state_machine.py)（75 行）
- [workflow_runtime_service.py](/home/zl/code/easyStory/apps/api/app/modules/workflow/service/workflow_runtime_service.py)

真实现状是：

- 状态迁移仍由自研 `WorkflowStateMachine` 维护
- 节点执行主链仍是 `while workflow.status == "running"` + `_dispatch_node()`
- 运行时能力散在多个 mixin 中

这层业务边界相对清楚，但通用 graph runtime 仍然是自研。

结论：**workflow 是最适合优先切入 LangGraph 的层。**

#### 2.2.3 `ProjectSetting` 定位仍然偏重

当前仓库里的正式口径已经开始把 `ProjectSetting` 降级为“结构化摘要 + 上下文投影”，但旧设计与部分实现仍然保留了它作为创作根对象的影子：

- [architecture.md](/home/zl/code/easyStory/docs/specs/architecture.md) 已经写成“结构化摘要、快速浏览、机器投影”
- [database-design.md](/home/zl/code/easyStory/docs/specs/database-design.md) 也明确说不要把它误当成完整创作设定真值
- 但 [06-creative-setup.md](/home/zl/code/easyStory/docs/design/06-creative-setup.md) 和 [19-pre-writing-assets.md](/home/zl/code/easyStory/docs/design/19-pre-writing-assets.md) 仍然把它放成根对象
- 代码里仍有 `ensure_setting_allows_preparation()`、`project_setting` 注入、投影与完整度检查等残余心智

这说明当前真正的问题不是“要不要保留一点结构化摘要”，而是：

- `ProjectSetting` 这个名字和这套旧设计仍然会把系统继续往“结构化创作前置表单”方向推
- 它已经妨碍“项目文稿才是长期设定真值”的新方向

结论：**本轮重构应同时把 `ProjectSetting` 从创作主链中降级或移除。**

#### 2.2.4 前端页面操作逻辑仍被旧心智绑定

当前前端不只是“显示了旧概念”，而是**交互流本身仍然在推动旧架构**。典型表现包括：

- 项目设置页默认 tab 仍是 `setting`，核心面板仍是 `ProjectSettingSummaryPanel`
  - [project-settings-page.tsx](/home/zl/code/easyStory/apps/web/src/features/project-settings/components/project-settings-page.tsx)
  - [project-settings-content.tsx](/home/zl/code/easyStory/apps/web/src/features/project-settings/components/project-settings-content.tsx)
- 项目设置页仍把 `checkProjectSetting()` / `setting_completeness` 作为重要状态
- Incubator 仍以“自由对话 -> 生成 `ProjectSetting` 草稿 -> 预览结构化摘要”为核心交互
  - `incubator-preview.tsx`
  - `incubator-chat-support.ts`
- Studio 仍保留 `panel=setting` 这类旧入口语义，容易继续把“结构化设定面板”当创作入口
- 项目设置侧栏仍在引导“先进项目设置，再去 Studio / Engine”，而不是把项目文稿和创作工作台作为默认起点

这说明如果只改后端真值链、不改前端操作逻辑，结果会是：

1. 前端继续驱动用户维护旧 `ProjectSetting`
2. 后端虽然降级了 `ProjectSetting`，但产品操作心智仍然没变
3. 新旧两套入口语义会在 UI 上并行存在

结论：**前端页面操作逻辑必须与后端真值链重构同步推进。**

---

## 3. 长期冻结边界

以下边界必须先冻结，后续接入框架也不能动摇：

### 3.1 easyStory 自己必须继续持有的真值

- 项目文稿 identity / revision / binding
- 项目文稿中的长期设定与约束
- 正文版本链
- `RuleBundle`
- `SkillAssembly`
- AgentProfile 配置真值
- 审查结论与审核动作
- `conversation_id / run_id / continuation_anchor`
- `NormalizedInputItem[] / AssistantOutputItem[]`
- `project.*` 本地工具的授权、版本、审计语义

### 3.2 可以交给框架的通用运行时

- 图编排
- 中断 / 恢复 / checkpoint
- agent 执行循环
- middleware
- MCP adapter
- 常见 multi-agent 编排模式
- southbound 模型接入和路由

### 3.2A `ProjectSetting` 的新正式口径

本轮重构后，正式口径改为：

1. **长期创作设定真值 = 项目文稿**
   - `项目说明.md`
   - 设定细分文稿
   - 数据层结构化资料
   - 其他项目文稿中的长期约束
2. **前置创作链改为**
   - `项目文稿 / 设定文稿 -> Outline -> OpeningPlan -> ChapterTask -> Chapter`
3. **`ProjectSetting` 不再是创作根对象**
   - 不再作为工作流启动的硬前置
   - 不再承载“必须先结构化完再创作”的心智
4. **如果保留结构化对象**
   - 只允许作为 `ProjectBrief / ProjectDigest` 这类派生摘要
   - 用于项目列表展示、筛选、预算估算、快速投影
   - 允许不完整
   - 从项目文稿或对话中派生，不反过来强约束创作

这意味着：

- 旧 `ProjectSetting -> Outline -> OpeningPlan -> ChapterTask -> Chapter` 不再作为新主链
- 新系统不再接受“把完整创作设定先压成固定 schema 再开写”作为默认入口
- 结构化摘要若存在，也只能是附属投影，不是主真值

### 3.3 必须继续保留在 shared runtime 的共享基础设施

- canonical tool contract
- provider/gateway interop profile
- LiteLLM/native backend resolver
- capability probe / verifier 主链

### 3.4 旧代码清理硬要求

这轮不是“新增一套框架实现，再把旧实现留着以后慢慢删”，而是：

1. **每完成一个阶段，就删除对应旧实现**
2. **不保留长期兼容壳、临时桥接层、双轨运行路径**
3. **不允许出现“新旧两套 runtime 都能跑，只是配置不同”的长期状态**
4. **不允许为了兼容旧数据把迁移逻辑嵌进新 runtime**

允许的短期过渡只有一种：

- 在单个阶段内部，为了迁移和验证，存在明确标注、可快速删除的过渡 adapter

但阶段完成后必须立即清理：

- 旧入口
- 旧状态机
- 旧 while-loop
- 旧 tool loop 分支
- 无人再读写的 DTO / snapshot 字段
- 只为兼容旧运行时保留的 support glue
- 只为兼容旧数据读取保留的转换层

判断标准很简单：

- 如果某段代码不再承载当前正式真值
- 如果某段代码只服务于已废弃 runtime
- 如果某段代码的存在只是为了“以后也许回退方便”

那它就应该删除，而不是归档在主代码路径里。

---

## 4. 总体策略

不是“全部框架化，一次切换”，而是：

**先框架化 workflow，再框架化 assistant 的通用层，最后把 Hook / MCP / specialized agent 收到薄适配层。**

这样做的原因：

1. workflow 的边界已经比较清楚，最容易替换成 LangGraph
2. assistant 主链最复杂，必须先把“产品真值”和“通用运行时”拆出来，才能安全接 LangChain/LangGraph
3. LiteLLM 已经基本到位，不该重新折腾

### 4.1 本轮重构的成功标准

只有同时满足以下条件，这轮重构才算成功：

1. **通用运行时复杂度明显下降**
   - 不是把旧逻辑外面再包一层框架，而是旧 runtime 真正退场
2. **源码明显更整洁**
   - 没有长期双轨
   - 没有兼容壳堆积
   - 没有“新方案 + old_legacy_* support”常驻主路径
3. **业务真值更清晰**
   - 哪些是 framework state，哪些是 easyStory 真值，一眼能分清
4. **验证成本下降**
   - 新改动不再轻易牵动 assistant / workflow / provider 多条链同时回归
5. **旧包袱被真正切断**
   - 新主链不依赖旧数据
   - 新主链不依赖旧执行路径
   - 新主链不依赖迁移兼容壳

如果只是“接入了框架，但旧代码基本还在”，那不算成功，只是再次堆了一层。

---

## 5. 分阶段计划

### Phase 0：冻结边界，停止继续补自研底座

目标：

- 不再继续深挖自研通用 agent/runtime
- 先把框架接入边界写死
- 先把 `ProjectSetting` 从创作主真值位置上拿下来

动作：

1. 冻结 `assistant` 中以下对象的产品真值地位：
   - `AssistantTurnRun`
   - `AssistantToolStep`
   - `continuation_anchor`
   - `NormalizedInputItem[] / AssistantOutputItem[]`
2. 冻结 `project` 文稿 identity / revision / grant 语义
3. 明确禁止新增：
   - 新的 provider-specific assistant 分支
   - 新的自研通用 tool loop 特性
   - 新的自研 multi-agent runtime
4. 明确本轮代码清理原则：
   - 迁移完成的旧 runtime 必删
   - 兼容桥只允许阶段内短期存在
   - 不再接受“先并存以后再删”的无限延期
5. 明确本轮数据策略：
   - 旧 runtime 中间状态不迁移
   - 旧缓存/旧快照不迁移
   - 如需保留历史，仅做离线归档，不进入新正式主链
6. 明确 `ProjectSetting` 策略：
   - 不再把它作为创作根对象
   - 若保留，仅保留为 `ProjectBrief / ProjectDigest` 派生摘要
   - 旧 `setting_completeness` 阻塞逻辑退出主链
7. 明确前端同步策略：
   - 不再把“项目设置/结构化设定页”作为默认创作入口
   - 不再把 `setting_completeness` 作为主交互心智
   - 前端页面命名、默认 tab、入口 CTA 必须跟随新真值链一起调整

验收：

- 文档真值一致
- 后续重构 PR 不再新增“通用 runtime 复杂度”
- 新文档口径不再把 `ProjectSetting` 写成创作主真值

### Phase 0.5：重置项目真值链，移除 `ProjectSetting` 中心化设计

目标：

- 在进入 runtime 框架迁移前，先把领域真值链改正

新口径：

- 长期设定真值：项目文稿
- 结构化摘要：可选派生缓存
- 创作主链：`项目文稿 -> Outline -> OpeningPlan -> ChapterTask -> Chapter`

具体操作：

1. 文档层：
   - 重写 `06-creative-setup.md`
   - 重写 `19-pre-writing-assets.md`
   - 修正 `architecture/database-design/config-format` 中仍带旧心智的描述
2. 代码层：
   - 下线 `ensure_setting_allows_preparation()` 这类把 `ProjectSetting` 当硬前置的逻辑
   - 调整上下文注入：从项目文稿与 context bundle 构建长期约束
   - 若保留结构化摘要字段，改名或降级为 `ProjectBrief / ProjectDigest`
3. 数据层：
   - 新主链不依赖旧 `project_setting` 数据
   - 如仍保留旧字段，仅用于过渡期离线提取或后台重建，不进入新运行时主路径
4. 清理：
   - 删除旧完整度检查 support
   - 删除把 `ProjectSetting` 当“长期约束根对象”的文档与代码
   - 删除只服务旧 schema 的 prompt / projection glue

验收：

- 代码和文档都不再要求“先结构化设定再创作”
- 项目文稿成为默认长期设定入口
- `ProjectSetting` 若还存在，也不再阻塞工作流启动
- 新主链不依赖旧 `project_setting` 数据才能运行

### Phase 0.6：前端页面操作逻辑重置

目标：

- 让前端默认操作流与新真值链一致
- 不再由 UI 把用户推回旧 `ProjectSetting` 心智

新前端心智：

- 创作入口：项目文稿 / Studio / Outline
- 结构化摘要：可选辅助，不是必经入口
- 设置页：规则、模型、Skill、MCP、审计等配置中心
- 项目说明/设定文稿：在文稿树与项目文稿系统中直接维护

具体操作：

1. 项目设置页：
   - 不再以 `setting` 作为默认 tab
   - 弱化或移除 `ProjectSettingSummaryPanel` 的中心位置
   - 若保留摘要页，应改名为 `项目摘要` / `Project Brief`，明确为派生视图
   - `checkProjectSetting()` 与 `setting_completeness` 退出主交互中心
2. Incubator：
   - 不再以“生成结构化 ProjectSetting 草稿”作为核心目标
   - 改为“生成项目说明初稿 / 创作方向草稿 / 前置文稿草稿”
   - 若仍产出结构化摘要，只作为后台投影或辅助预览
3. Studio：
   - 移除或改名 `panel=setting` 等旧入口语义
   - 默认把项目说明、设定文稿、Outline、OpeningPlan 纳入文稿树主路径
   - 用户应能直接在文稿体系中维护长期设定，而不是跳去单独结构化设定页
4. Workflow / Preparation CTA：
   - 不再用 `setting_completeness` 作为主要阻塞文案
   - 改成基于“前置资产是否就绪”的语言，例如大纲、开篇设计、章节任务是否已建立
5. 命名清理：
   - 前端 UI 文案、query param、panel key、tab key 里，凡是把 `setting` 指向旧结构化根对象的，都要重命名或删除

清理要求：

- 删除旧的 ProjectSetting 中心化页面路径和文案
- 删除只为 `setting_completeness` 服务的前端状态、提示和跳转
- 不保留“新文稿入口 + 旧结构化入口”长期双轨

验收：

- 用户首次进入项目后，不会被默认引导去维护结构化 `ProjectSetting`
- 项目设置页不再承担“创作主入口”职责
- Incubator / Studio / Engine 的操作流与新主链一致
- 搜索前端页面 key / tab / panel 时，不再出现把 `setting` 当创作根对象的主入口语义

### Phase 1：Workflow 先迁移到 LangGraph

目标：

- 用 LangGraph 替换 workflow engine 里的通用 graph runtime
- 保留现有业务模型、API、运行记录和数据库结构

替换范围：

- `WorkflowEngine`
- `WorkflowStateMachine`
- `WorkflowRuntimeService.run()` 的主循环与节点路由

保留范围：

- `WorkflowExecution / NodeExecution`
- workflow snapshot / persistence
- 业务 mixin 中的实际节点业务
- Hook 事件与项目/内容服务交互

做法：

1. 先把当前节点执行和状态流转投影成 LangGraph state
2. 用 LangGraph 的 graph/edge/interrupt 取代 while-loop + 手写状态迁移
3. 保留 easyStory 自己的持久化模型，不直接把 LangGraph state 当数据库真值
4. 在迁移完成后删除：
   - `WorkflowEngine` 里旧的状态迁移帮助逻辑
   - `WorkflowStateMachine` 中被 LangGraph state/edge 替代的迁移规则
   - 只服务旧 while-loop 的 support glue
5. 不为旧 workflow snapshot 保留长期兼容解析路径；必要时重新生成新 snapshot
6. 新 workflow graph 直接面向“项目文稿 + 前置资产链”，不再默认依赖旧 `ProjectSetting` 根对象

收益：

- 减少自研状态机错误
- 为后续“暂停、恢复、人工确认、多候选分支”提供更稳的骨架

风险：

- 需要先定义 graph state 与 DB 真值的映射
- 节点 mixin 可能仍然比较散，需要一个 adapter 层

验收：

- 同一 workflow snapshot 能跑通现有章节主链
- pause/resume 语义不退化
- Hook 触发时机不漂移

### Phase 2：assistant 主链先做“真值/运行时”拆分，再接框架

目标：

- 不直接重写 `AssistantService`
- 先把最重的通用 runtime 从产品真值里剥出来

拆分方向：

1. 保留 easyStory 的：
   - turn/run store
   - tool step store
   - document binding / grant / policy
   - transcript / continuation / audit
2. 把可替换的通用层抽成 adapter：
   - model loop
   - tool planning/execution cycle
   - multi-step continuation orchestration

当前最需要拆的对象：

- `AssistantToolLoop`
- `assistant_turn_llm_bridge_support`
- `assistant_llm_runtime_support`

具体操作：

1. 先把 `AssistantService` 中“产品真值相关职责”和“通用 loop 调度职责”拆开
2. 把 `AssistantToolLoop` 拆成：
   - policy / descriptor / budget / document binding 这类业务侧对象
   - 真正的 model/tool cycle adapter
3. 删除只为了旧循环模型存在的 support 函数和中转 DTO
4. 先做到“assistant 主链内部分层清楚”，再谈框架替换
5. 明确不兼容旧 turn/tool-loop 中间状态；新主链按新 contract 重新落库或重建
6. 长期设定上下文默认来自项目文稿 / context bundle，而不是旧 `ProjectSetting` 全量注入

收益：

- 后续 LangGraph/LangChain 才有清晰挂点
- 不会把 framework state 直接塞进业务层

验收：

- `AssistantService` 继续持有 run lifecycle
- 通用 loop 逻辑与业务授权/文稿真值显式分层

### Phase 3：specialized agent 与 Hook agent 先接 LangChain

目标：

- 先把最容易收益高的 agent 场景交给 LangChain
- 不先碰 Studio 普通聊天主链

优先改造场景：

1. Hook 内 agent 执行
2. reviewer agent
3. 多候选章节生成 agent
4. 资料收集 / research agent

原因：

- 当前 `run_assistant_agent_hook()` 已经是一个相对独立的执行面
- 这类 agent 更像“独立工人”，很适合先用 LangChain 封装

保留：

- AgentProfile
- Skill / rules / preferences
- 项目本地工具与授权策略

具体操作：

1. 先把 `run_assistant_agent_hook()` 这类独立执行面替换成 LangChain 封装
2. 为 reviewer / research / multi-candidate 单独定义 agent adapter
3. 清理旧的专用 agent 执行 glue，不保留两套 agent 执行骨架并存
4. 不为旧 agent 执行产物或旧 prompt 形状保留长期兼容转换

收益：

- 先把“最重复、最脆”的 agent 封装交给框架
- 先积累 LangChain 接入经验，再决定是否下沉到 ordinary chat

验收：

- Hook agent 场景能稳定跑
- 规则、Skill、项目上下文注入不漂移
- run 级审计仍然保留

### Phase 4：ordinary chat tool loop 迁到 LangGraph 驱动

目标：

- 让 ordinary chat 的通用 tool loop 改为 LangGraph 驱动
- 但不放弃 easyStory 自己的 run/step/document/policy 真值

建议做法：

1. 把 `AssistantToolLoop` 重构成一个 graph adapter，而不是继续手写循环
2. graph state 只保存本轮运行时必要状态：
   - current messages/input items
   - planned tool calls
   - tool results
   - continuation markers
3. run / step / policy / document binding 仍由 easyStory 记录和校验
4. 完成迁移后删除：
   - 旧的手写 iteration 主循环
   - 旧的“仅为自研 tool loop 存在”的 state recorder glue
   - 已被 graph adapter 吸收的重复 planner / continuation 中转逻辑
5. 明确不读取旧 tool loop state snapshot；必要时让旧 run 直接终止或归档，而不是兼容恢复

不要做的事：

- 不把 provider server-side tool loop 当项目工具执行入口
- 不把 LangGraph state 直接当持久化真值
- 不把 LangChain memory/session 直接写成业务真值

风险：

- 这是最复杂阶段
- 一次替换过大容易把 run/step/replay 打坏

建议：

- 只在 workflow 迁稳、specialized agent 稳定后再做
- 先做非流式，再做流式

验收：

- 现有 `AssistantTurnRun / AssistantToolStep` 语义不退化
- 文稿工具权限、版本、审计不退化
- continuation / replay / cancel 仍可用

### Phase 5：MCP / Hook 保持薄适配层，统一挂框架能力

目标：

- 不再自研更重的 MCP / Hook 运行时
- 只保留 easyStory 的业务事件和薄适配层

做法：

- Hook 继续保留业务事件定义
- MCP 继续保留 server config / registry / trust boundary
- LangChain MCP adapter 放到执行侧，不改业务配置真值
- 清理只为旧 MCP / Hook 执行模型存在的重复胶水代码
- 不为旧 Hook/MCP payload 形状长期保留兼容分支

验收：

- 新增 MCP server 或 agent tool 不需要改 assistant 主链
- Hook 事件与业务层继续通过显式接口交互

### Phase 6：知识库只接到 `context` 模块

目标：

- 未来引入全文检索/向量库时，不触发 assistant/workflow 主结构大改

原则：

- 知识库不是新的正文真值
- 知识库不是新的 assistant memory 真值
- 只能作为 `context` 模块的检索能力扩展
- 知识库接入后若发现现有 `assistant/workflow` 需要大面积改写，说明边界设计失败，必须先回到 `context` 适配层修正，而不是把检索逻辑直接塞进主链

标准调用路径：

`assistant / workflow -> ContextService.build_context(...) -> document sources + story assets + knowledge retrieval -> context bundle`

这样后续无论接：

- SQLite FTS
- PostgreSQL FTS / pgvector
- Qdrant / Milvus / Weaviate

都不应该要求重写 assistant/workflow 主链。

---

## 6. 推荐实施顺序

建议顺序固定为：

1. **先重置 `ProjectSetting`，把项目文稿拉回长期真值位置**
2. **同步重置前端页面操作逻辑**
3. **Workflow -> LangGraph**
4. **Hook agent / specialized agent -> LangChain**
5. **assistant 主链做真值/运行时拆分**
6. **ordinary chat tool loop -> LangGraph**
7. **MCP / Hook 保持薄适配**
8. **未来知识库 -> context 模块**

不要反过来先碰 ordinary chat 主链。  
那样风险最大，而且你现在最痛的稳定性问题也不会先缓解。

---

## 7. 风险与控制

### 风险 1：把框架对象直接写成业务真值

控制：

- 所有框架对象只存在于 adapter / engine 层
- 持久化层只写 easyStory 的 DTO / record / snapshot

### 风险 2：一口气替换 assistant 主链

控制：

- assistant 分两段改：先 specialized agent，再 ordinary chat
- 每段完成后立即删旧 runtime，不保留长期双轨

### 风险 3：LiteLLM 再次被“框架模型接口”重复包裹导致边界混乱

控制：

- 继续保留 `shared/runtime/llm` 为唯一 southbound 出口
- LangChain/LangGraph 不直接掌管 provider/gateway 细节

### 风险 4：知识库提前侵入业务真值

控制：

- 所有检索结果都先进入 `context bundle`
- 不单独形成新的正文/项目/审查真值链

---

## 8. 预期收益

如果按这个顺序执行，收益主要是：

1. 不再继续维护一套越来越重的自研通用 runtime
2. 把最容易反复出错的 graph/agent/tool loop 通用层交给成熟框架
3. 保住 easyStory 自己真正有价值的部分：小说业务真值与产品语义
4. 未来接知识库时，只是给 `context` 模块加能力，不是大拆主链
5. 创作入口不再被重结构化 `ProjectSetting` 限制，产品形态更自然

## 9. 源码整洁要求

这轮重构必须把“源码整洁”写成交付要求，而不是附带收益。

明确要求：

1. 删除废代码，不做收藏
2. 删除旧 support 文件，不留死入口
3. 删除只服务旧 runtime 的 snapshot / DTO / helper
4. 不保留“legacy / old / deprecated”长期目录
5. 不通过注释说明“这个以后再删”来替代真正删除
6. 不把“数据兼容”“历史兼容”当作保留旧代码的理由

提交层面的完成标准：

- 新代码路径可独立解释
- 旧代码路径已从主链退出
- 搜索关键旧对象时，不应再出现多套并行主入口
- 新的实现不依赖旧 runtime 才能成立
- 新实现不依赖旧 runtime 数据或旧 snapshot 才能成立

---

## 10. 结论

这轮重构不应该再走“继续修补自研通用底座”的路线。  
长期最稳的方案是：

- **LiteLLM** 继续做 southbound
- **LangGraph** 优先接 workflow，再逐步接 assistant tool loop
- **LangChain** 优先接 specialized agent、hook agent、review/research/multi-candidate 这类高价值场景
- easyStory 自己继续持有业务真值、授权、审计、文稿 identity、规则/Skill 装配和 context bundle
- `ProjectSetting` 从创作根对象降级或直接退场；长期设定真值回到项目文稿

一句话总结：

**框架负责“怎么跑”，easyStory 只负责“跑什么、真值归谁、什么时候停给用户确认”。**
