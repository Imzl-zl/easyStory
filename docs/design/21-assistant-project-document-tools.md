# Assistant 项目文稿工具设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 文档状态 | 生效 |
| 创建时间 | 2026-04-03 |
| 更新时间 | 2026-04-06 |
| 关联文档 | [20-assistant-runtime-chat-mode](./20-assistant-runtime-chat-mode.md)、[22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)、[16-mcp-architecture](./16-mcp-architecture.md)、[系统架构设计](../specs/architecture.md) |

---

## 1. 目的

定义 easyStory 在 `Studio` 聊天中引入“项目文稿读写工具”的正式方案。

目标不是复刻 Claude / Codex CLI 的通用文件代理，而是在 easyStory 既有真值边界上，提供一组稳定、可审计、可控的项目级文稿工具，解决这些高频场景：

- 章节写完后，需要同步人物关系、势力关系、时间轴、伏笔记录
- 用户已经勾选参考文稿，但当前聊天只有路径提示，没有真实读取能力
- 一次修改往往会影响多份资料，不能继续靠逐份手工打开再追问

ordinary chat 的原生 tool-calling runtime、provider 适配、run / step 真值、SSE 协议和授权模型，统一见 [22-assistant-tool-calling-runtime](./22-assistant-tool-calling-runtime.md)。本文只定义“项目文稿能力域”本身。

---

## 2. 范围

### 2.1 目标

本方案要求：

1. 模型可以在聊天过程中读取项目内相关文稿
2. 模型可以在获得授权的前提下更新需要同步的项目文稿
3. 模型不需要知道底层是 DB 还是文件层
4. 所有读写都走现有正式 service，不引入第二条真值写入路径
5. 失败必须显式暴露，不做静默降级或“猜路径”
6. 默认只读，写入必须有显式授权
7. 写入结果必须带稳定 `version / revision / audit` 锚点
8. 第一阶段统一读取 canonical + 文件层文稿，但写入只覆盖已有项目文件层文稿

### 2.2 非目标

本方案暂不追求：

- 任意 OS 文件读写
- 任意 shell 命令执行
- 通用 IDE / CLI 代理
- 自动修改项目外文件
- `v1A` 直接写 canonical 大纲 / 开篇 / 正文章节真值
- 让 assistant 私有化项目文稿目录、identity、版本与 revision 规则

---

## 3. 核心边界

### 3.1 工具面向“项目文稿能力”，不是“文件系统”

模型看到的是统一项目文稿路径，例如：

- `大纲/总大纲.md`
- `正文/第一卷/第003章.md`
- `设定/人物.md`
- `数据层/人物关系.json`

模型不需要知道：

- 这份文稿落盘在哪个目录
- 这份正文是不是存在数据库
- 当前读写应该调用哪一个内部 service
- 这份文稿是 canonical、文件层，还是目录占位节点

这些判断必须由后端项目文稿能力层完成。

### 3.2 项目文稿能力主归属 `project` 域，`content` 只提供 canonical 适配

assistant 只负责：

- 暴露工具合同
- 执行 tool loop
- 维护 run / step
- 把工具结果写回模型上下文

assistant 不负责：

- 维护统一目录真值
- 定义 canonical / file 的文稿身份规则
- 维护文稿 version / revision / catalog 真值
- 自己决定应该走哪条业务保存链

主归属约束直接定死为：

- `project`
  - 拥有统一目录、`path -> document_ref`、`resource_uri`、`catalog_version`
  - 拥有文件层文稿 version / revision / audit 真值
  - 对 assistant 暴露统一项目文稿能力入口
- `content`
  - 只通过公开 service 提供总大纲 / 开篇设计 / 章节等 canonical 文稿读取适配
  - 不拥有统一目录真值，不反向拥有 assistant tool executor

assistant 只依赖 `project` 暴露的统一项目文稿能力，不直接同时编排 `project` 与 `content` 两套平行文稿入口。

### 3.3 `path` 只是定位键，不是内部稳定身份

对模型与 UI 暴露的统一定位键仍然是 `path`，但内部版本、审计、幂等与冲突检测不能直接绑定路径。

运行时在真正读写前，必须先把 `path` 解析成稳定 `document_ref`：

- `path`
  - 面向模型与 UI 的主要定位键
- `document_ref`
  - 面向版本、revision、幂等与审计的稳定身份
- `resource_uri`
  - 面向内部资源层与后续 MCP Resources 映射的稳定资源标识

进一步约束：

- 写入 grant、版本冲突检测、dirty buffer 对比、revision 映射都必须绑定 `document_ref + base_version`
- `path` 允许变，但 `document_ref` 不能因为重命名、目录调整或 canonical 投影变化而漂移
- 如果请求入口仍只提供 `path`，runtime 也必须先完成 `path -> document_ref` 归一化，再暴露工具或签发写入能力

### 3.4 真值边界保持不变

引入工具后，真值边界仍然不变：

- `ProjectSetting`
  - 结构化摘要真值
- `contents + content_versions`
  - 大纲 / 开篇 / 正文章节真值
- 项目文件层
  - 设定、数据层、时间轴、附录、校验、导出等工作文稿

第一阶段明确：

- `project.read_documents` 可以统一读取 canonical + 文件层文稿
- `project.write_document` 第一阶段只允许更新已有项目文件层文稿
- canonical 文稿可以出现在统一目录中，但必须明确返回 `writable=false`

### 3.5 内部提前区分 Resource Plane 与 Mutation Plane

对模型暴露的长期最小能力面保持：

- `project.list_documents`
- `project.search_documents`
- `project.read_documents`
- `project.write_document`

但在 runtime 与业务实现内部，应提前区分：

- `Resource Plane`
  - 统一目录
  - 搜索
  - 读取
  - 上下文候选发现
- `Mutation Plane`
  - 显式写回
  - 版本冲突
  - 权限控制
  - JSON 校验
  - 审计与 revision

这样后续即使增加 MCP resource 映射、目录订阅、外部检索增强，也不需要回头拆 assistant runtime。

---

## 4. 领域对象

### 4.1 `ProjectDocumentEntry`

建议统一目录长期围绕 `ProjectDocumentEntry` 建模，至少包含：

- `path`
- `document_ref`
- `resource_uri`
- `source`
- `title`
- `document_kind`
- `mime_type`
- `schema_id`
- `content_state`
- `writable`
- `version`
- `updated_at`
- `catalog_version`

其中：

- `source`
  - `outline | opening_plan | chapter | file`
- `path`
  - 当前统一目录中的稳定路径视图
  - `v1A` 正式真值先收口到 `path`
  - 若后续需要补 `source_key / current_path`，也只能作为派生投影，不能替代当前正式字段
- `content_state`
  - `ready | empty | placeholder`
- `version`
  - 面向并发控制的 opaque token
  - 不能退化成 `updated_at` 或文件 `mtime`

### 4.2 `ProjectDocumentRevision`

如果 latest content 继续由现有 DB / 文件层保存，则 revision 层只承担 append-only metadata、hash 与 audit mapping，不得变成第二条 latest content 真值路径。

建议至少包含：

- `document_ref`
- `document_revision_id`
- `content_hash`
- `version`
- `created_at`
- `run_audit_id`
  - 指向单次已提交写入效果对应的 append-only audit 记录
  - `v1A` 建议至少做到 `run_id + tool_call_id` 粒度；同一 run 内多次写同一文稿时，不能继续只用裸 `run_id`

一旦检测到 latest content 与 revision metadata 不一致，必须显式返回 `revision_state_mismatch`。

### 4.3 `ProjectDocumentCatalog`

目录一致性必须有正式版本锚点。

建议最少包含：

- `catalog_version`
- `entries[]`

`catalog_version` 用途：

- 标识目录视图是否过期
- 支撑 `document_context` 新鲜度判断
- 支撑 `catalog_version_mismatch`
- 为后续资源订阅、变更事件和缓存校验提供唯一锚点

不建议继续只用 `catalog_stale=true` 这类布尔语义承载目录一致性。

但 `catalog_version` 的职责只限于：

- 目录 freshness / discovery / context selection
- 统一目录快照是否过期

`catalog_version` 不应承担：

- 单份目标文稿的 `path -> document_ref` mutation binding
- 因无关目录 churn 而一刀切阻断当前目标文稿写入

单文稿写入前的稳定锚点应另有独立 `binding_version`。

`v1A` 还必须明确：

- 即使当期不对模型暴露 `list / search`，后端也要先具备完整统一目录真值
- `catalog_version` 必须基于完整统一目录生成，不能基于当前选中路径子集临时生成
- 建议至少纳入每个目录项的 `document_ref / path / resource_uri / title / source / document_kind / mime_type / schema_id / content_state / writable / version`
- 否则 `document_context.catalog_version` 与后续 `catalog_version_mismatch` 都会退化成伪锚点

### 4.4 `ProjectDocumentContextBinding`

`document_context` 若要真正成为 ordinary chat 的正式系统字段，文稿域内部还需要一层稳定绑定对象。

建议至少包含：

- `path`
- `document_ref`
- `resource_uri`
- `binding_version`
- `base_version`
- `buffer_hash`
- `catalog_version`
- `selection_role`

其中：

- `binding_version`
  - 标识某个 `path -> document_ref + writable/source/document_kind` 绑定视图的稳定版本
  - 用于 mutation 前校验目标解析是否仍与签发 grant 时一致
  - 不等同于全目录 `catalog_version`

- `base_version`
  - 对应当前编辑 buffer 所基于的文稿版本
  - 用于 dirty buffer 拒签、版本冲突检测和写回前校验
- `buffer_hash`
  - 用于标识当前缓冲区快照
  - 不能退化成 `updated_at`
- `selection_role`
  - `active | selected`
  - 用于区分当前主文稿与额外参考文稿

约束：

- `catalog_version` 负责 discovery freshness
- `binding_version` 负责 mutation binding
- 写入前优先校验 `binding_version`；`catalog_version` 只在当前 turn 显式依赖目录 freshness 时参与附加校验
- `v1A` 若要允许非 active 目标写入，必须先为每个候选目标补齐自己的 buffer 快照；不能继续只靠单个 `active_buffer_state`

三层映射长期固定为：

1. request projection
   - 前端 / API 透传的 flat `document_context`
   - 例如 `active_document_ref`、`active_binding_version`、`selected_document_refs`、`active_buffer_state`
2. runtime normalized binding
   - ordinary chat runtime 内部冻结的 `DocumentContextBinding[]`
   - 用于 run snapshot、grant 解析与恢复
3. project binding
   - 项目文稿能力层正式消费的 `ProjectDocumentContextBinding`
   - 用于 `path -> document_ref`、`binding_version`、`base_version`、`buffer_hash` 与 `resource_uri` 校验

字段映射至少应固定为：

- `document_context.active_document_ref -> ProjectDocumentContextBinding.document_ref`
- `document_context.active_binding_version -> ProjectDocumentContextBinding.binding_version`
- `document_context.active_buffer_state.base_version -> ProjectDocumentContextBinding.base_version`
- `document_context.active_buffer_state.buffer_hash -> ProjectDocumentContextBinding.buffer_hash`
- `document_context.catalog_version -> ProjectDocumentContextBinding.catalog_version`

---

## 5. 工具定义与暴露策略

### 5.1 长期最小工具集

| 工具 | 作用 | 一期优先级 |
|---|---|---|
| `project.list_documents` | 列出 assistant 可访问的统一文稿目录 | `v1A` |
| `project.search_documents` | 文稿候选发现；`v1A` 先按路径名 / 标题 / 基础元数据检索 | `v1A` |
| `project.read_documents` | 批量读取项目文稿 | `v1A` |
| `project.write_document` | 写回单份项目文稿 | `v1A` |

第一阶段不继续扩工具面，也不新增“读取当前上下文集合”这类重复语义入口。

### 5.2 descriptor 是正式真值，不在 handler 里临时拼

`project.*` 工具定义应由 `AssistantToolDescriptorRegistry` 统一生成，业务侧只提供稳定能力接口，不直接在执行器里拼 schema。

descriptor 最少包含：

- `name`
- `description`
- `input_schema`
- `output_schema`
- `origin`
- `trust_class`
- `plane`
- `mutability`
- `execution_locus`
- `approval_mode`
- `idempotency_class`
- `timeout_seconds`

其中：

- `plane`
  - `resource | mutation`
- `origin`
  - `project_document`
- `trust_class`
  - `local_first_party`
- `mutability`
  - `read_only | write`
- `execution_locus`
  - `local_runtime | provider_hosted | remote_mcp`
  - `project.*` 长期固定为 `local_runtime`
- 长期 `approval_mode`
  - `none | grant_bound | always_confirm`
- 但 `v1A`
  - 只暴露 `none | grant_bound`

### 5.3 协议基线必须足够“硬”

第一阶段协议要求：

- 输入参数全部使用 strict JSON schema
- 所有 object 明确 `additionalProperties=false`
- 返回值使用固定 output schema，结构化字段是真值
- `project_id`、`owner_id`、写权限 scope 不进入工具 schema，由 runtime 绑定
- `run_id`、`tool_call_id`、`write_grant`、`document_ref` 不要求模型填写
- `v1A` 关闭模型侧并行 tool call
- 读操作可批量，写操作串行
- mutation 工具必须在 descriptor 中显式声明 `approval_mode` 与 `idempotency_class`

`v1A` 当前已落地并应稳定暴露的错误码至少包括：

- `invalid_arguments`
- `document_not_found`
- `document_not_readable`
- `document_not_writable`
- `version_conflict`
- `write_grant_expired`
- `invalid_json`
- `schema_validation_failed`
- `binding_version_mismatch`
- `revision_state_mismatch`
- `active_buffer_state_required`
- `active_buffer_state_invalid`
- `dirty_buffer_conflict`
- `write_target_not_allowed`
- `write_target_mismatch`

其中：

- 目录外或不存在路径在 `v1A` 统一按 `document_not_found` 返回，不再区分 `unsupported_path`
- 当前 request 级写目标形状校验仍由 assistant request contract 负责，错误码为 `unsupported_write_target_scope`

tool loop 自身边界错误仍由 runtime 单独处理，例如 `tool_loop_exhausted`。

---

## 6. 统一结果 envelope

每个 `project.*` 工具都先返回统一执行 envelope，再承载各自业务字段。

统一 envelope 最少包含：

- `tool_call_id`
- `status`
- `structured_output`
- `content_items`
- `resource_links`
- `error`
- `audit`

其中：

- `structured_output`
  - 模型继续推理时依赖的结构化真值
- `content_items`
  - 作为工具结果的正式内容投影
  - 长期应可映射到 MCP `content[]`
- `resource_links`
  - 作为稳定资源引用投影
  - 长期应优先承载 `resource_uri`
- `error`
  - 至少包含 `code / message / retryable / recovery_hint / requires_user_action`
- `audit`
  - 至少包含 `run_audit_id`
  - 必要时补 `document_revision_id`
  - `run_audit_id` 必须指向当前这次实际写入效果，不得偷懒退化成整轮 run 的唯一 id

`v1A` 若当前前端仍需要纯文本摘要，可额外提供：

- `display_text`
  - 只作为 `content_items` 的 UI projection
  - 不作为 runtime、SSE、trace 或持久化回放的唯一真值

序列化口径必须固定：

- 顶层正式真值只保留 `tool_call_id / status / structured_output / content_items / resource_links / error / audit`
- `display_text` 若存在，只是兼容期 UI projection，不得承载独立业务语义
- 各工具业务字段一律进入 `structured_output`
- 不允许同一语义同时出现在顶层与 `structured_output` 两处
- 若 `display_text` 与 `content_items` 语义冲突，以 `content_items` 为准

与 MCP 长期对齐约束：

- `structured_output` 语义上应可无损映射到 MCP 的 `structuredContent`
- `content_items` 语义上应可无损映射到 MCP 的 `content`
- 若工具结果需要补充可再次读取的文稿引用，应优先通过 `resource_uri` 映射到资源链接，而不是继续堆自定义顶层字段

---

## 7. 读取语义

### 7.1 `project.read_documents`

对模型只暴露真正需要决定的业务参数：

- `paths`
- 可选 `cursors`

`structured_output` 最少包含：

- `documents`
- `errors`
- `catalog_version`

单个 `documents[]` 项至少包含：

- `path`
- `document_ref`
- `resource_uri`
- `title`
- `source`
- `document_kind`
- `mime_type`
- `schema_id`
- `content_state`
- `writable`
- `version`
- `updated_at`
- `content`
- `truncated`
- `next_cursor`

### 7.1A 读取范围边界

`project.read_documents` 面向的是“统一项目目录”，不是任意文件系统。

必须明确：

- `paths` 必须是当前统一目录可解析的项目文稿路径
- 不接受 OS 绝对路径、`..` 跳转、glob、目录遍历或“顺便看看这个目录里还有什么”的文件系统语义
- `v1A` 的读取范围固定为 `project catalog bounded`
  - 只要某个 path 能在当前统一目录中解析，且文稿状态允许读取，就可以被读取
- `selected_paths / selected_document_refs`
  - 只表示当前上下文提示与 UI 选中集合
  - 不构成硬读取白名单
- 若后续产品要做更窄的读取暴露面，应在 runtime / policy 层新增 `DocumentReadPolicy` 或等价对象，而不是修改 `project.read_documents` 的 schema

### 7.2 读取规则

- “文稿内容为空” 与 “文稿不存在” 必须是两种不同结果
- canonical 路径若不存在，必须直接返回显式错误，不能伪装成空文稿
- placeholder 节点若未物化，应返回 `document_not_readable`
- 部分路径成功、部分失败时，返回 `documents[] + errors[]`
- 超出读取预算时，必须显式返回 `truncated` 或 `content_too_large`
- `truncated=true` 时，必须同时返回可继续读取的锚点，例如 `next_cursor` 或等价分页信息；不能只截断内容不告诉模型如何继续
- 截断语义应保持稳定，可采用 head-tail、分页窗口或等价确定性策略；禁止每次随机裁剪不同片段
- 若返回的是截断内容，`content` 必须明确只是部分正文，不得让 `display_text` 或摘要伪装成完整读取结果
- 若单份文稿大到无法在当前预算内返回任何有意义片段，应直接返回 `content_too_large`，而不是塞一个空内容成功结果
- `truncated=true + next_cursor` 应被视为“可继续读取”的正式结果语义；在 runtime compaction 里，它不应被当成普通旧工具结果优先压缩

### 7.3 `v1A` 不要求先暴露目录工具，但要先有后端目录能力

即使 `v1A` 只先开放 `read / write`，后端也应先具备统一目录与 `path -> document_ref` 解析能力。

原因：

- assistant tool loop 需要稳定定位和校验锚点
- `document_context` 需要 `catalog_version`
- 后续 `list / search` 不应再回头改目录层

---

## 8. 写入语义

### 8.1 `project.write_document`

第一阶段语义明确为：

- 基于 `base_version` 整份写回下一版完整内容

对模型暴露的业务参数长期应保持最小集：

- `path`
- `content`
- `base_version`

其中 `document_ref`、`write_grant`、`run_id`、`tool_call_id` 都由 runtime 绑定，不要求模型填写。

本轮写目标资格来源长期固定为：

- `requested_write_scope`
- `requested_write_targets`
- 归一化后的 `document_context` bindings

其中：

- `requested_write_scope`
  - 只定义“本轮是否允许写”
- `requested_write_targets`
  - 只定义“哪些文稿可以成为候选写目标”
  - request 形状长期固定为 `document_ref[]`
- `selected_paths / selected_document_refs`
  - 只是读取/参考集合，不得隐式升级为写入白名单
- 若 `requested_write_targets` 缺失
  - `v1A` 默认只把 `active_document_ref` 视为候选写目标
- `v1A` 实际只接受“缺失”或“仅包含 `active_document_ref` 的单元素集合”
  - 若请求显式包含其他 `document_ref`，必须返回 `unsupported_write_target_scope`
  - 原因不是授权不愿放，而是当前正式 request contract 只有 `active_buffer_state`，还不足以稳定保护其他目标的未保存缓冲区

写入真正执行前，runtime 还必须同时绑定并校验：

- `path -> document_ref`
- `document_ref` 是否命中当前 `write_grant.target_document_refs`
- `base_version` 是否命中 grant 与当前文稿版本约束
- `v1A` 下当前目标是否就是 `active_document_ref`
- 当前 `document_context.active_buffer_state` 是否允许写回
- 当前目标 `binding_version` 是否仍命中 grant 与路径解析锚点
- 若本轮显式依赖目录 freshness，再额外判断 `catalog_version` 是否仍可接受

`structured_output` 最少包含：

- `path`
- `document_ref`
- `resource_uri`
- `source`
- `version`
- `document_revision_id`
- `updated_at`
- `diff_summary`
- `run_audit_id`

### 8.2 写入规则

- canonical 文稿统一返回 `document_not_writable`
- `v1A` 只允许更新“统一目录中已存在、且允许写入”的项目文件层文稿
- `project.write_document` 不承担“顺便创建不存在文稿”的语义
- `base_version` 与当前版本不一致时，必须显式返回 `version_conflict`
- 不允许静默覆盖
- 不允许“偷偷重读最新内容后直接改写”
- 若当前活跃 buffer 仍基于旧 `base_version` 且未保存，runtime 必须显式拒绝写入，而不是把旧 buffer 当成最新正文继续覆盖
- 不允许因为 `selected_paths / selected_document_refs` 中出现某文稿，就自动扩大当前 run 的写入目标集合

### 8.3 默认整份写回，不做 patch 式编辑

`v1A` 写入语义明确为：

1. 读取当前文稿全文
2. 模型生成下一版完整内容
3. 运行时带 `base_version` 整份写回

不做按行编辑、字符区间编辑或 patch 式 diff 执行。对小说与资料文稿来说，整份写回更接近业务语义，也更利于审计、diff 与回滚。

### 8.4 JSON 校验绑定 `schema_id`，不绑定路径

第一阶段 `.json` 文稿仍按整份文本写回，但校验边界要收紧：

- 普通 `.json` 文稿至少做 JSON 语法校验
- 已知数据层文稿做 strict shape 校验
- 校验器通过 `schema_id -> validator` 注册表绑定
- 路径只用于定位，不应成为长期唯一校验入口

第一批建议覆盖：

- `project.data_schema`
- `project.characters`
- `project.factions`
- `project.character_relations`
- `project.faction_relations`
- `project.memberships`
- `project.events`

校验失败直接显式报错，不做 schema 自动补全、字段猜测或静默修复。

---

## 9. 统一目录与路由

### 9.1 统一目录不能继续依赖前端临时拼树

当前真实情况是：

- 后端 `document-files/tree` 只覆盖项目文件层树
- canonical 节点仍由 Studio 前端额外补进文稿树

因此 assistant 看到的统一目录必须由后端聚合，而不是继续复用前端临时树。

长期更稳的方向是：

- Studio UI
  - 也逐步切到同一后端统一目录能力
- assistant tools
  - 直接复用同一目录能力

### 9.2 统一目录建议返回扁平列表

对 assistant 工具来说，扁平列表比深层树更稳定。

目录元数据最少包含：

- `path`
- `title`
- `source`
- `document_kind`
- `mime_type`
- `schema_id`
- `content_state`
- `writable`
- `version`
- `updated_at`
- `catalog_version`

内部资源平面仍保留稳定 `resource_uri`。对于模型侧协议：

- `list / search` 不要求默认暴露 `resource_uri`
- `read / write` 的 `structured_output` 可以返回 `resource_uri`，用于后续 trace、资源映射和稳定引用

### 9.3 内部分类规则

读取时：

1. 总大纲 canonical path -> 大纲读取链路
2. 开篇设计 canonical path -> 开篇读取链路
3. 章节 canonical path -> 章节读取链路
4. 其他路径 -> 项目文件层读取链路

写入时（第一阶段）：

1. canonical path -> 直接返回 `document_not_writable`
2. 其他允许写入路径 -> 项目文件层保存链路

Studio 手工保存与 assistant `project.write_document` 必须共享同一条文件层写入约束：同样要求 `base_version`、同样落 `document_revision_id / run_audit_id`、同样执行 `schema_id` 绑定校验，不能再保留一条绕过 revision/schema/version 的 UI 保存旁路。

若仍保留 `PUT /projects/{project_id}/documents` 这类 Studio 保存投影接口，其返回体也必须携带当前这次提交对应的 `document_revision_id / run_audit_id`，不能把能力层元数据落库后再在 UI 投影层丢掉。

这样对外仍是一套 `project.*` 工具，对内继续走正式 service。

---

## 10. 版本、revision 与审计

第一阶段就要把三层职责分开：

- `version`
  - 面向并发控制
  - 必须是稳定 opaque token
  - 不能退化成 `updated_at`、前端时间戳或文件 `mtime`
- `document_revision_id`
  - 指向单份文稿的已持久化 revision
- `run_audit_id`
  - 指向单次已提交写入效果的 append-only 工具审计记录
  - `v1A` 可先采用 `run_id + tool_call_id`
  - 同一 run 内若允许多次提交写入，后续再按 write-effect / step 继续细化，但不能退化成裸 `run_id`

文件层不能继续只靠“当前文件内容 + mtime”承担版本与审计真值。

若文件系统继续作为 latest content source，则 revision 层只承担 append-only metadata、hash 与 audit mapping，不得长成第二条 latest content 读取路径。一旦检测到文件内容 hash 与当前 revision 不一致，应显式返回 `revision_state_mismatch`。

---

## 11. 实现落点

建议直接复用现有模块，但补齐中立的项目文稿能力层，不新起 assistant 私有平行真值层：

- `ProjectService`
- `ChapterContentService`
- `StoryAssetService`
- `studio_document_file_store`

在 `project` 域补齐薄编排对象，例如：

- `ProjectDocumentCatalogService`
- `ProjectDocumentReadService`
- `ProjectDocumentWriteService`
- `ProjectDocumentVersionService`

这层负责：

- `path -> document_ref`
- `document_ref -> resource_uri`
- 统一目录聚合
- 批量读取编排
- `base_version` 冲突校验
- JSON schema 校验
- revision / audit 收口
- 向 assistant 暴露稳定工具 DTO 能力
- 内部再按需调用 `content` 公开 service 获取 canonical 文稿

这层不负责：

- 自己决定内容真值
- 直接写底层数据库或磁盘绕过正式 service
- 复制一套 outline / chapter 保存逻辑
- 承担 tool loop 或 provider 适配职责

assistant 侧只需要：

- `AssistantToolDescriptorRegistry`
- `AssistantToolExposurePolicy`
- `AssistantToolExecutor`

---

## 12. 分阶段实施

### 12.1 `v1A`

`v1A` 先拿到真实可稳定读写的最小闭环：

1. 落地 `path -> document_ref` 与 `catalog_version`
2. 实现 `project.read_documents`
3. 实现 `project.write_document`
4. 统一 canonical 缺失显式报错
5. 第一阶段只写已有项目文件层文稿
6. 建立稳定 `version / document_revision_id / run_audit_id`
7. 已知数据层 JSON 使用 `schema_id` 驱动严格校验
8. 把这层能力作为 assistant tool executor 的正式依赖

### 12.2 `v1B`

`v1B` 再补前端交互和 UX 收口；目录与搜索能力已在 `v1A` 实现：

1. 完整统一目录 API
2. 补齐 `project.list_documents` / `project.search_documents` 的 UI 收口
3. 补齐目录与搜索的授权提示、加载态与空结果态
4. 补齐更完整的 `catalog_version` 校验
5. 评估把 Studio 文稿树也切到同一后端统一目录
6. 再评估是否把 `catalog_snapshot` 接回 `document_context`

---

## 13. 硬约束

以下约束违反任意一条，后续都会重新变脆：

1. 禁止让模型读取任意项目外文件
2. 禁止让模型直接写底层磁盘路径
3. 禁止让模型自己决定 DB 写入口
4. 禁止路径不存在时静默补空文稿
5. 禁止 canonical 写失败后偷偷改写到文件层
6. 禁止把 `path` 当成唯一版本主键
7. 禁止把 `updated_at`、mtime 或前端时间戳直接当成 `version`
8. 禁止继续把统一目录长期留在前端临时拼装
9. 禁止让前端直接决定真实可写路径白名单
10. 禁止 assistant 私有化项目文稿目录、identity、版本或 revision 真值
11. 禁止把完整统一目录主归属继续写成 `project/content` 联合边界
12. 禁止第一阶段开放 canonical 文稿写回
13. 禁止把 `selected_paths / selected_document_refs` 当成隐式写白名单
14. 禁止把 `catalog_version` 当成 mutation 唯一锚点；单文稿写入必须有独立 `binding_version`

---

## 14. 结论

本方案的本质不是“给聊天多加一个文件工具”，而是把 easyStory 的项目文稿访问正式收口成：

- 一套统一路径
- 一层稳定身份 `document_ref`
- 一个正式目录版本锚点 `catalog_version`
- 一组严格结构化的读写工具
- 一条由 `project` 统一暴露、内部再按需调用 `content` 适配的正式访问路径

这样 ordinary chat 拿到的就是“项目文稿能力”，而不是一套会越做越像旁路脚本的伪文件代理。
