# Assistant 项目文稿工具设计

| 字段 | 内容 |
|---|---|
| 文档类型 | 功能设计 |
| 文档状态 | 待审 |
| 创建时间 | 2026-04-03 |
| 更新时间 | 2026-04-04 |
| 关联文档 | [20-assistant-runtime-chat-mode](./20-assistant-runtime-chat-mode.md)、[16-mcp-architecture](./16-mcp-architecture.md)、[系统架构设计](../specs/architecture.md) |

---

## 1. 目的

定义 easyStory 在 `Studio` 聊天中引入“项目文稿读写工具”的正式方案，解决当前这类高频问题：

- 当前章节写完后，人物关系、势力关系、时间轴、伏笔记录是否需要同步更新
- 用户已经勾选了参考文稿，但当前聊天只拿到了路径，没有真正读取正文
- 需要更新的文件往往不止一份，靠用户手动逐个打开、复制、追问，成本过高

本方案的目标不是复刻 Claude/Codex CLI 的通用文件代理，而是在 easyStory 现有真值边界上，增加一层稳定、可审计、可控的“项目级文稿工具”。

---

## 2. 背景与问题

### 2.1 当前主路径已经收口，但仍然缺一层“可执行能力”

当前 assistant 主路径已经明确为：

- 规则：长期自动注入
- 历史：只带当前会话
- Skill / Agent：显式增强
- MCP：能力层，不是常驻 prompt

这保证了普通聊天的语义清晰，但还存在一个现实缺口：

- 当前文稿路径和一段截断后的当前文稿内容会进入本轮请求
- 额外勾选的参考文稿当前只会把路径名带进请求
- 这些上下文会被前端固化进会话消息里的请求文本
- ordinary chat 后端仍然只是单次组装 prompt 后调用一次模型，不具备通用 tool-calling 主循环

也就是说，现状并不是“完全没有文稿上下文”，而是：

- 当前文稿：有少量正文注入
- 额外参考文稿：只有路径提示
- 模型：不能按路径真实读取，也不能按路径真实写回

因此，用户现在只能：

1. 先写正文
2. 再追问“哪些资料要更新”
3. 再手动打开对应文稿
4. 再让 AI 改一份、保存一份

这条链路在长篇创作里过于脆弱，也不符合“资料维护应被系统协助完成”的目标。

### 2.2 为什么不能直接照搬 Claude/Codex CLI

Claude/Codex CLI 面向的是通用编程环境，它们强调的是：

- 任意文件系统访问
- 任意 shell / 工具能力
- 广义代码仓库代理

easyStory 当前场景不是这个问题。

本项目的文稿真值已经分成两类：

- 项目文件层：设定、数据层 JSON、时间轴、附录、校验、导出
- DB 正式内容层：总大纲、开篇设计、章稿正文

如果把“任意读写本地文件”直接暴露给模型，会立刻带来这些问题：

- 模型需要自己判断该去 DB 还是去文件层
- 容易绕开现有业务服务，破坏真值边界
- 稳定性不可控，最终又会回到“一会儿能读、一会儿不能读”

因此，easyStory 需要的不是“通用文件系统工具”，而是“项目文稿工具”。

### 2.3 主流成熟方案真正值得借鉴的是什么

参考 Claude Code、Codex、Aider 这类成熟产品，真正稳定的共性并不是“CLI 外形”，而是：

- 工具集小而正交：`list / search / read / write` 分工清楚
- 输入输出契约严格结构化：`strict schema + fixed output schema + stable error codes`
- 不让模型填写系统已知参数：项目、用户、会话上下文由 runtime 绑定
- 读写权限显式分离：默认只读，写入能力需显式开启，并能收窄到指定 roots / paths
- tool loop 放在运行时编排层，不塞进底层 provider 抽象
- 改动可追溯：最小审计信息、冲突显式暴露、结果回执可解释
- 资源索引进入上下文，正文按需读取，而不是长期把全文硬塞进会话历史
- 初期先把并发面收窄：读操作可批量，写操作保持串行，不为“看起来更聪明”而放大执行复杂度

对 easyStory 来说，真正应该借鉴的是这些稳定约束，而不是复刻一套通用 CLI 形态。

项目级规则也不需要再额外发明一套 CLI 风格的 project instruction 真值源：

- 继续沿用现有 assistant rule bundle
- 文稿工具只负责读写能力，不重新定义规则注入体系

---

## 3. 设计目标

### 3.1 目标

本方案要满足：

1. 模型可以在聊天过程中读取项目内相关文稿
2. 模型可以在获得授权的前提下，更新需要同步的项目文稿
3. 模型不需要知道底层是 DB 还是文件层
4. 所有读写都走现有正式服务，不引入第二条真值写入路径
5. 失败明确暴露，不做静默降级或“猜测路径”
6. 默认只读，写入必须有显式授权，不做 silent write
7. 写入结果必须带最小版本与审计信息，冲突显式暴露
8. 第一阶段统一读取 canonical + 文件层文稿，但写入只覆盖已有项目文件层文稿

### 3.2 非目标

本方案暂不追求：

- 任意 OS 文件读写
- 任意 shell 命令执行
- 手工图编辑器式节点拖拽保存
- 通用 IDE/CLI 代理
- 自动修改用户项目外的任何文件

---

## 4. 核心原则

### 4.1 工具面向“项目文稿”，不是“文件系统”

模型看到的是：

- `设定/人物.md`
- `数据层/人物关系.json`
- `正文/第一卷/第012章.md`

模型不需要知道：

- 这份文稿实际落盘在哪个目录
- 这份正文是不是存数据库
- 当前读写应该调用哪一个内部 service

这些判断必须由后端服务层完成。

### 4.2 路径是统一定位键，不是存储实现细节

对模型与 UI 来说，统一使用“项目文稿路径”。

例如：

- `大纲/总大纲.md`
- `大纲/开篇设计.md`
- `正文/第一卷/第003章.md`
- `设定/势力.md`

后端根据路径决定：

- canonical 路径：转发到 `content` / `project` 正式服务
- 普通项目文稿路径：转发到项目文件层服务

模型只用路径，不直接接触“DB 工具”和“文件工具”的分叉。

但这里还需要补一条容易被忽略、却直接影响稳定性的约束：

- `path` 是对模型与 UI 暴露的统一定位键
- `path` 不是内部唯一版本主键，更不是并发控制主键

原因是：

- canonical 章节当前已经支持挂到 `正文/卷目录/第xxx章.md` 这类路径
- 后续还可能继续出现正文目录重排、路径重映射、卷目录重命名
- 同一份 DB 章节真值不应因为展示路径变化，就被视为另一份文稿

因此运行时在真正读写前，应先把 `path` 解析成内部稳定的 `document_ref`：

- 对模型与 UI：继续只暴露 `path`
- 对版本、审计、幂等、冲突检测：统一绑定 `document_ref`

也就是说：

- `path` 负责“找到它”
- `document_ref` 负责“确认它到底是谁”

### 4.3 真值边界不变

引入工具后，真值边界仍然不变：

- `ProjectSetting`：结构化摘要真值
- `contents + content_versions`：大纲 / 开篇 / 正文章节真值
- 项目文件层：设定、数据层、附录、时间轴、校验、导出等工作文稿

工具只是给 assistant 增加“通过正式入口访问真值”的能力，不改变真值归属。

第一阶段还要额外补一条边界：

- “统一目录” 不等于 “统一可写”
- `project.read_documents` 可以统一读取 canonical + 文件层文稿
- `project.write_document` 第一阶段只允许更新已有项目文件层文稿
- canonical 文稿在统一目录中可以出现，但应明确返回 `writable=false`
- 若后续确认需要 AI 直接改 canonical 文稿，应单独升阶段评审，不在第一阶段里混进来

### 4.4 失败显式暴露

不允许：

- 路径不存在时偷偷返回空文件
- canonical 文稿写失败时静默改写到文件层
- 写入被拒绝时伪装成成功

所有错误都必须直接暴露，便于模型与用户判断下一步。

这里还需要补一条实现约束：

- canonical 文稿工具不能直接沿用当前“缺失时返回空字符串”的 seed 读取语义

对工具层来说：

- “文稿存在但内容为空” 与 “文稿不存在” 必须是两种不同结果
- `project.read_documents` 若命中不存在的 canonical 路径，应直接返回显式错误，而不是伪装成空文稿

### 4.5 先做受控工具，不做通用代理

第一阶段只实现：

- 项目内已知文稿
- 已知路径规则
- 已知读写边界

不做：

- 任意路径访问
- 目录穿越
- 项目外资源读写

### 4.6 默认只读，写入显式开启

第一阶段的权限模型应明确为：

- 默认只暴露 `project.list_documents`、`project.search_documents`、`project.read_documents`
- 只有用户显式开启“本轮允许更新文稿”或“当前会话允许更新文稿”时，才暴露 `project.write_document`
- 即使开启写权限，执行器内部也应再按服务端 `allowed_write_roots / allowed_write_paths` 收窄本次真实可写范围
- 写权限关闭时，模型若请求写入，必须返回显式权限错误

也就是说，用户可以自然地说“直接同步”，但系统是否真的给出写工具，不应靠模型猜测。

另外还要补一条成熟方案里很常见、但这里尤其重要的约束：

- `project_id`、`owner_id`、`session_id`、当前写权限 scope 这类系统已知参数，不应暴露给模型填写
- 它们应由 assistant runtime 从当前 turn context 直接绑定
- 工具参数只保留模型真正需要决定的业务参数，例如 `path`、`paths`、`query`、`content`

这里再补一条一期必须钉死的实现边界：

- 前端可以表达“申请 turn 级写权限”或“申请 session 级写权限”
- 前端不能直接决定真实 `allowed_write_roots / allowed_write_paths`
- 真实可写范围必须由后端签发成当前运行时可验证的 `write_grant`
- 具体 allowlist 只作为执行器内部约束，不要求暴露给模型，也不应成为 prompt-visible context 的稳定组成部分

建议口径：

- 请求层只表达 `requested_write_scope`
- runtime 在校验 owner / project / session 后，生成服务端 `write_grant`
- `write_grant` 绑定 `owner_id + project_id + session_id + scope + allowed_write_* + expires_at`
- 工具执行器只信任 `write_grant`，不信任客户端原样透传的可写范围

这样可以避免：

- 多标签页状态漂移
- 历史请求回放放大权限
- 客户端本地状态被误当成安全边界

### 4.7 审计先于回滚

第一阶段就应具备最小审计闭环：

- 记录本轮工具调用顺序
- 记录读取了哪些文稿、写入了哪些文稿
- 记录写入前后的版本标识
- 记录本次权限暴露范围、用户意图摘要和最终状态
- 回复中返回可追溯的 `audit_id`

完整快照回滚和 UI 入口可以后续增强，但“先有可追溯记录”应属于第一阶段基线，而不是增强项。

这里还要明确：

- `audit_id` 不能只是临时生成一个 UUID 再返回给前端
- `audit_id` 必须能指向已持久化的审计记录或 revision 记录
- 文件层不能只靠“当前文件内容 + mtime”承担版本与审计真值

更稳的做法应是：

- 第一阶段先把 `version` 与 `audit_id` 的职责分离
- `version` 必须来自已提交内容对应的稳定 revision token，不能退化成 mtime 或临时时间戳
- `audit_id` 指向本轮 turn 级 append-only 工具审计记录
- 在文件层完整 revision ledger 补齐前，不允许让 `audit_id` 反向承担文稿版本真值

这样后续无论做 diff、冲突恢复还是回滚入口，都会有真实锚点，而不是靠临时拼装。

### 4.8 幂等先于自动重试

ordinary chat 一旦进入 tool loop，就不能默认假设“每次写入只会发生一次”。

真实运行里很容易出现：

- SSE 断开后前端重连
- assistant runtime 内部自动重试
- 上游 provider 因网络抖动重复返回工具调用
- 同一 turn 在恢复时被再次执行

因此第一阶段就应明确：

- 每个 assistant turn 生成稳定 `run_id`
- 每个工具步骤生成稳定 `tool_call_id`
- 写入幂等键至少绑定 `run_id + tool_call_id + document_ref`

执行语义应为：

- 同一个幂等写请求重复到达时，返回第一次成功结果
- 不允许因为重试而重复制造 revision
- 自动重试只适用于只读操作，或尚未提交的写前阶段
- 一旦写入已提交，后续恢复应走“读最新状态后继续”，而不是盲写第二次

---

## 5. 用户场景

### 5.1 章节写完后同步资料

用户说：

> 这一章写完了，检查下人物关系、势力关系、时间轴和伏笔记录需不需要更新，必要的话直接改掉。

理想链路：

1. 模型读取当前章节
2. 模型读取人物、势力、人物关系、势力关系、隶属、时间轴、伏笔文稿
3. 模型判断哪些资料受影响
4. 模型逐份写回需要更新的文稿
5. 返回“这次修改了哪些文稿，改了什么”

### 5.2 基于勾选路径读取资料

用户在聊天面板里勾选：

- `设定/人物.md`
- `数据层/人物关系.json`
- `时间轴/章节索引.md`

理想链路：

- 当前 prompt 中仍只带路径提示
- 但模型看到这些路径后，可以调用读取工具获取全文
- 不再依赖把整份内容预先硬塞进 prompt

### 5.3 用户明确要求更新某份文稿

用户说：

> 把这一章导致的变化同步到 `数据层/势力关系.json`

模型应能：

- 先读当前章节
- 再读目标文稿
- 生成新内容
- 调用写入工具保存

---

## 6. 工具集合设计

### 6.1 第一阶段最小集合

建议第一阶段只做以下工具：

| 工具 | 作用 | 是否第一阶段 |
|---|---|---|
| `project.list_documents` | 列出当前 assistant 可访问的统一文稿目录 | 是 |
| `project.search_documents` | 基于路径名/标题搜索候选文稿 | 是 |
| `project.read_documents` | 批量读取项目文稿 | 是 |
| `project.write_document` | 写回单份项目文稿 | 是 |

第一阶段不需要再拆成“文件工具”和“DB 工具”两套对外接口。

对模型只暴露一套：

- `list`
- `search`
- `read`
- `write`

内部再路由。

不建议增加单独的 `project.read_current_context`：

- 当前会话关联路径本来就在前端与 prompt 侧已有来源
- 再做一层“读取当前上下文集合”容易形成第二套语义重复入口
- 工具层应聚焦统一目录、搜索、正文读取、正文写回

这里的 `project.list_documents` 语义不是直接复用现有 `document-files/tree` 接口。

当前真实情况是：

- 后端 `document-files/tree` 只覆盖项目文件层树
- `大纲/总大纲.md`、`大纲/开篇设计.md` 和章节 canonical 节点，是由 Studio 前端额外补进文稿树的

因此第一阶段必须额外做一次“统一聚合”：

- 要么由后端新增统一目录读取能力
- 要么由 assistant 侧工具执行器先聚合 canonical 节点 + 文件层树，再暴露给模型

但无论采用哪种实现，模型看到的都应是一份统一目录，而不是两套来源。

### 6.1.1 协议基线

第一阶段要把协议层收紧到足够“硬”，避免后续实现再靠 prompt 约定补洞：

- 四个工具的输入参数都使用 strict JSON schema，所有 object 明确 `additionalProperties=false`
- 四个工具的返回值都使用固定 output schema，结构化字段是真值，文本总结最多只是附加信息
- 工具层使用稳定错误码，不用自然语言句子充当错误协议
- `project_id`、`owner_id`、写权限 scope 等系统已知上下文不进入工具 schema，由 runtime 绑定
- 第一阶段保持 4 个工具即可，不继续扩工具面
- 第一阶段关闭模型侧并行 tool call；批量读取统一走 `project.read_documents`，写入由执行器串行落地
- `run_id`、`tool_call_id`、`write_grant`、`document_ref` 这类执行态字段也不要求模型填写，统一由 runtime 绑定或解析

建议第一阶段统一错误码至少覆盖：

- `invalid_arguments`
- `permission_denied`
- `unsupported_path`
- `document_not_found`
- `document_not_readable`
- `document_not_writable`
- `version_conflict`
- `write_grant_expired`
- `content_too_large`
- `json_invalid`
- `schema_validation_failed`

tool loop 自身的边界错误则单独收口为运行时错误，例如 `tool_loop_exhausted`。

### 6.1.2 模型侧错误恢复约定

仅有错误码还不够，运行时还需要明确告诉模型“拿到错误后应该怎么做”，否则工具调用很容易停在半路。

第一阶段建议在 tool description 或 system prompt 中固定以下恢复指引：

- `document_not_found`：不要猜路径，改用 `project.list_documents` 或 `project.search_documents` 重新确认路径
- `permission_denied`：明确告知用户当前未开启写权限或超出允许写范围，不要继续尝试写入
- `version_conflict`：重新读取目标文稿，拿到最新 `current_version` 后再决定是否重试
- `content_too_large`：改用 `next_cursor` 分段读取，不要继续一次性请求全文
- `json_invalid` / `schema_validation_failed`：先修正文稿内容结构，再尝试写回

更稳的协议形态是：

- 工具错误返回体除 `code / message / path` 外，还可以附带结构化 `recovery_hint`
- `recovery_hint` 由服务端生成，告诉模型“下一步该调用什么工具”或“应直接向用户说明什么”
- 不要求模型自己从错误码推理恢复计划

建议最小结构：

```json
{
  "code": "document_not_found",
  "path": "设定/人物关系.json",
  "message": "目标文稿不存在",
  "recovery_hint": {
    "kind": "tool_call",
    "tool": "project.search_documents",
    "suggested_arguments": {
      "query": "人物关系",
      "roots": ["数据层", "设定"]
    },
    "user_message": "该路径不存在，请先重新确认正确文稿路径。"
  }
}
```

这样可以避免模型把工具错误当成普通文本继续“硬聊”，也能减少无意义重试。

### 6.2 统一读工具

建议对外契约：

```json
{
  "tool": "project.read_documents",
  "arguments": {
    "paths": [
      "设定/人物.md",
      "数据层/人物关系.json",
      "正文/第一卷/第003章.md"
    ],
    "cursors": {
      "正文/第一卷/第003章.md": "opaque-cursor"
    }
  }
}
```

其中：

- `project_id` 不进入工具参数，由当前 assistant turn 自动绑定
- `cursors` 为可选项，仅在某份文稿上轮返回了 `next_cursor` 时使用
- `version`、`cursor` 等具体编码均视为 opaque token，模型不需要理解底层存储实现

返回：

```json
{
  "documents": [
    {
      "path": "设定/人物.md",
      "title": "人物设定",
      "source": "file",
      "document_kind": "setting_markdown",
      "mime_type": "text/markdown",
      "schema_id": null,
      "content_state": "ready",
      "writable": true,
      "version": "opaque-version",
      "updated_at": "2026-04-04T10:00:00Z",
      "content": "...",
      "truncated": false,
      "next_cursor": null
    },
    {
      "path": "正文/第一卷/第003章.md",
      "title": "第003章",
      "source": "chapter",
      "document_kind": "chapter",
      "mime_type": "text/markdown",
      "schema_id": null,
      "content_state": "ready",
      "writable": false,
      "version": "opaque-version-12",
      "updated_at": "2026-04-04T10:05:00Z",
      "content": "...",
      "truncated": true,
      "next_cursor": "opaque-cursor-2"
    }
  ],
  "errors": []
}
```

这里的 `source` 只作为返回信息，不作为模型必须理解的前置知识。

第一阶段建议再明确几条规则：

- 参数非法、路径全部失败、或请求越权时，整次工具调用直接失败
- 若是“部分路径可读、部分路径失败”，返回体里显式给出 `documents` 与 `errors` 两组结果
- `errors` 至少包含 `path / code / message`
- 不做 silent partial success，也不把失败路径偷偷吞掉
- 若某份文稿过长，必须显式返回 `truncated=true` 与 `next_cursor`
- “文稿内容为空” 与 “文稿不存在” 必须是两种不同结果，不允许用 silent clip 或空字符串混淆
- 执行器应显式限制 `max_paths_per_call`、`max_chars_per_document` 与 `max_total_chars_per_result`
- 单文稿超出单次读取预算时，返回 `truncated + next_cursor`
- 聚合结果超出总体预算时，必须显式返回 `truncation` 信息或 `content_too_large`，不能靠静默截断混过去
- 若统一目录中的某个 canonical 节点当前只是占位而未物化，读取时应返回 `document_not_readable`，而不是伪装成空文稿

### 6.3 统一写工具

建议对外契约：

```json
{
  "tool": "project.write_document",
  "arguments": {
    "path": "数据层/人物关系.json",
    "content": "{ ... }",
    "base_version": "opaque-version",
    "intent": "同步本章带来的关系变化"
  }
}
```

返回建议至少包含：

```json
{
  "path": "数据层/人物关系.json",
  "source": "file",
  "version": "opaque-version-next",
  "updated_at": "2026-04-04T10:10:00Z",
  "diff_summary": "新增一条敌对关系，更新时间轴索引引用",
  "audit_id": "uuid"
}
```

其中：

- `base_version` 是从 `project.list_documents` 或 `project.read_documents` 拿到的版本标识
- `version / base_version` 必须由后端统一生成，模型和 UI 都只把它当 opaque token 使用
- `base_version` 必须绑定内部稳定 `document_ref`，不能只绑定展示路径
- 第一阶段不能直接拿 `updated_at`、文件 mtime 或前端时间戳充当版本标识
- 文件层文稿应有自己的 revision token；canonical 文稿应把当前内容版本号或版本 ID 封装成统一 opaque token
- 若 `base_version` 与当前最新版本不一致，必须显式返回冲突错误
- 不允许静默覆盖，也不允许工具层偷偷重读后直接改写最新版本
- `version_conflict` 错误至少应返回：`path / code / message / current_version`
- `diff_summary` 必须由服务端基于写前/写后内容生成，不能把模型自报文本当审计真值
- 第一阶段至少要保证“成功回执里的 `version` 已持久化、`audit_id` 可追溯”，但两者仍是不同职责字段
- `audit_id` 必须对应已持久化的本轮工具审计记录，而不是临时回执字段

第一阶段写入路由应明确收窄为：

- canonical 文稿：`大纲/总大纲.md`、`大纲/开篇设计.md`、`正文/.../第xxx章.md`
  - 统一目录中可见、可读
  - `project.write_document` 对它们直接返回 `document_not_writable`
- 其他已存在且允许写入的项目文稿
  - 走项目文件层正式保存链路
  - 第一阶段只支持这类路径写回

这样做的原因很直接：

- 当前高频诉求本质是“读正文 / 大纲，再同步资料层文稿”
- 不是“普通聊天直接改正式正文真值”
- 先把写入面收窄，能显著降低版本、权限和并发复杂度

如果后续确认要开放 AI 直接更新 canonical 文稿，再补两条约束：

1. 对外契约仍保持 `path + content`

   模型不需要理解 canonical 文稿内部的 `title / change_source / context_snapshot_hash` 细节。

2. 执行器不能直接拼装底层写库逻辑

   对 canonical 文稿，执行器仍必须走：

   - `StoryAssetService.save_asset_draft()`
   - `ChapterContentService.save_chapter_draft()`

- `project.write_document` 只负责“更新已有文稿”
- 不承担“顺便创建不存在章节 / 不存在文稿”的语义
- 新建章节占位文稿、新建自定义文件，仍走现有创建链路
- 只有当前 turn / session 明确开启写权限时，`project.write_document` 才会出现在工具集合里

### 6.4 列表工具

建议对外契约：

```json
{
  "tool": "project.list_documents",
  "arguments": {
    "roots": ["设定", "数据层", "时间轴"],
    "prefix": "数据层/",
    "limit": 200,
    "cursor": "opaque-cursor"
  }
}
```

返回项目统一文稿目录，用于：

- 路径补全
- 判断相关资料是否存在
- 减少模型编造路径
- 为后续 `read / write` 提供 `version`、`writable`、`updated_at` 等最小元数据

这里返回的应是“统一目录视图”，至少包含：

- canonical 文稿：`大纲/总大纲.md`、`大纲/开篇设计.md`、现有章节路径
- 项目文件层文稿：设定、数据层、时间轴、附录、校验、导出等

不应让模型拿到一棵“只含文件层”的树，再由它自己猜哪些 canonical 文稿也存在。

建议最小返回字段：

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

这里建议再明确一个目录级状态：

- `content_state=ready`：文稿已物化，可正常读取
- `content_state=empty`：文稿存在但当前内容为空
- `content_state=placeholder`：路径当前只作为固定槽位或 canonical 占位出现，不代表已有可读正文

这样统一目录才能同时满足两点：

- UI 仍可保留固定槽位与 canonical 入口
- assistant 不会把“目录里看得到”误判成“现在一定可读”

对 assistant 工具来说，返回扁平列表通常比深层树更稳定：

- 模型更容易做路径匹配与工具参数拼装
- UI 需要树时，再由前端自行渲染
- 当章节数量增长后，也更容易做 `roots / prefix / cursor` 分页，避免整棵目录一次性塞进上下文

### 6.5 搜索工具

建议对外契约：

```json
{
  "tool": "project.search_documents",
  "arguments": {
    "query": "人物关系",
    "roots": ["数据层", "设定"],
    "limit": 10
  }
}
```

第一阶段建议把搜索范围收口到：

- 路径名
- 文稿标题或固定 label

也就是说，第一阶段搜索优先做：

- exact match
- prefix match
- 轻量 name contains

而不是一上来做：

- 向量语义检索
- 全文检索
- 跨全文打分排序

返回值只需提供候选项，不返回全文，例如：

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

这类搜索可以显著减少模型枚举整棵目录的成本，也比一上来做全文检索更容易稳定落地。

### 6.6 写入语义：默认整份写回，不做按行编辑

第一阶段的 `project.write_document` 语义应明确为：

- 先读取当前文稿全文
- 模型基于全文生成下一版完整内容
- 运行时带 `base_version` 整份写回

不采用以下语义：

- 修改第 N 行
- 只改某个字符区间
- 像代码补丁那样按 diff 执行局部编辑

原因如下：

1. 小说文稿不是稳定行号文本

   Markdown、JSON、时间轴、设定文稿都会频繁插入、合并、重排。  
   “第 37 行”这类定位在多轮编辑后并不稳定，按行编辑很容易改错位置。

2. 业务上更接近“产出下一版文稿”

   对人物关系、势力关系、时间轴、设定这类资料来说，模型的真实任务不是“动一行”，而是“基于当前全文生成更新后的下一版”。

3. 更容易统一文件层与 canonical 内容层

   大纲、开篇、章节正文本身就更接近“保存新版本全文”，不是文本编辑器意义上的局部补丁。  
   若项目文件层采用整份写回，DB canonical 内容也采用整份保存，整个工具模型会更统一。

4. 更利于审计、diff 与回滚

   整份写回后，系统可以稳定记录：

   - 修改前全文
   - 修改后全文
   - 本次变更 diff
   - 回滚点

   若一开始就做按行编辑，后续版本管理和问题排查会更复杂。

因此，本方案中的“编辑文稿”在用户感知上可以理解为“AI 帮我改文稿”，但在系统协议层应落成：

- `read_document(s)`：读取当前全文
- `write_document`：基于 `base_version` 写回下一版完整全文

对 `.json` 文稿再补一条边界：

- 第一阶段可以继续按“整份文本写回”处理
- 普通 `.json` 文稿至少做 JSON 语法校验
- 已知数据层文稿应做 strict shape 校验，至少覆盖：
  - `数据层/结构定义.json`
  - `数据层/人物.json`
  - `数据层/势力.json`
  - `数据层/人物关系.json`
  - `数据层/势力关系.json`
  - `数据层/隶属关系.json`
  - `数据层/事件.json`
- 这些校验应与当前 Studio 数据层 JSON 预览口径一致，例如固定 collection key：`characters / factions / character_relations / faction_relations / memberships / events`
- 校验失败直接显式报错
- 不做 schema 自动补全、字段猜测或静默修复

### 6.7 后续可选增强

如果后续确实出现大量高频、稳定、结构明确的局部修改场景，可以再评估新增更细粒度工具，例如：

- `append_section`
- `replace_block`
- `update_json_items`

但这些都不应进入第一阶段主路径，更不应替代“全文读取 + 整份写回”的基础模型。

---

## 7. 路由原理

### 7.1 为什么必须统一入口

如果直接给模型暴露两套工具：

- `file.read_document`
- `chapter.read_chapter`

模型就必须自己判断：

- 这份文稿是文件还是 DB
- 当前应该调用哪一套服务

这会把项目内部真值边界直接泄露给模型，并带来不必要的选择错误。

因此，正确做法是：

- 对外：统一 `project.read_documents / project.write_document`
- 对内：根据路径分类路由

### 7.2 内部分类规则

内部判断顺序建议直接复用现有 canonical path 逻辑：

读取时：

1. 若路径是总大纲 canonical path -> 走大纲读取链路
2. 若路径是开篇设计 canonical path -> 走开篇读取链路
3. 若路径是章节 canonical path -> 走章节读取链路
4. 否则 -> 走项目文件层读取链路

写入时（第一阶段）：

1. 若路径是 canonical path -> 直接返回 `document_not_writable`
2. 否则 -> 走项目文件层保存链路

这样可以复用当前现有真值服务，不再引入第二套文稿访问规则。

---

## 8. 运行时装配方式

### 8.1 当前状态

当前 ordinary chat 的链路仍然是：

1. 组装 `messages`
2. 组装 `system_prompt`
3. 单次调用上游模型
4. 返回文本

更具体地说，当前代码事实是：

- `AssistantTurnRequestDTO` / `AssistantTurnResponseDTO` 仍是“消息输入 + 文本输出”模型
- `AssistantService` 当前是 `_prepare_turn -> _call_turn_llm -> _finalize_turn` 的单次执行链
- 当前 `ToolProvider` 只负责 `llm.generate`
- 现有 Hook / MCP / Plugin 路径只服务 hook 事件，不是 ordinary chat 的通用工具循环

因此，当前 assistant runtime 还没有通用 tool-calling 主循环。

### 8.2 目标形态

引入项目文稿工具后，普通聊天链路应扩成：

1. 组装规则、历史、当前消息、结构化文稿上下文
2. 调用模型，允许它返回：
   - 直接文本回复
   - 或工具调用请求
3. 若模型请求工具：
   - 执行工具
   - 将工具结果写回运行时上下文
   - 再继续调用模型
4. 直到返回最终文本

这里不应写成“直接把现有 `ToolProvider` 扩一扩就好”。

更准确的实施口径应是：

- 保留当前 `ToolProvider -> llm.generate` 作为模型调用出口
- 在 assistant runtime 内新增一层普通聊天专用的 tool loop / tool executor
- 由这层负责识别模型工具请求、执行项目文稿工具、把结果回填，再继续下一轮模型推理

这样既不会污染现有 Hook 插件执行路径，也不会把 project document 工具错误塞进底层 LLM provider 抽象。

从实现结构上，建议显式分成几层薄组件：

- `AssistantService`
- `DocumentToolLoop`
- `ProjectDocumentCatalog`
- `ProjectDocumentReader`
- `ProjectDocumentWriter`

这些可以是 service / support object / helper 的不同实现形态，但职责边界应保持稳定：

- `DocumentToolLoop` 负责循环、权限暴露、工具结果回填
- `Catalog / Reader / Writer` 负责统一目录聚合、路径路由、审计收口
- 底层真值仍由 `ProjectService`、`StoryAssetService`、`ChapterContentService` 承担

### 8.2.1 第一阶段执行策略

第一阶段的关键不是把 tool loop 做得多“智能”，而是让执行边界足够稳定。

建议执行器内部固定以下策略：

- 模型侧关闭并行 tool calls，避免同一轮里并发发起多次写入
- 多文稿读取统一走一次 `project.read_documents`
- `project.read_documents` 在执行器内部可以按路径分组并发读取，降低总等待时间
- 写入保持串行提交；每次写入完成后都以返回的新 `version` 作为后续真值
- 同一 turn 内对相同路径的重复读取可以命中 per-turn 内存缓存，但缓存不得跨 turn 复用
- 每个 turn 都生成稳定 `run_id`
- 每个工具步骤都分配稳定 `tool_call_id`，写入按此做幂等去重
- 第一阶段除 `max_tool_steps` 外，再固定少量执行边界，例如 `max_writes_per_turn`、`max_same_path_writes_per_turn=1` 与 `tool_loop_timeout_seconds`
- 读取并发保持小规模固定值即可，例如内部 `read_concurrency=2~3`，不把大量并发调度暴露成主协议
- 同一路径在同一 turn 内若已成功写入，不允许再次写入同一路径；后续如需继续修改，应开启新 turn 基于新 `version` 重来

这里要特别区分两层并发：

- 对模型暴露面：收窄，尽量一次读、多次顺序写
- 对执行器内部：可控并发，只用于只读 IO

这样既能减少延迟，也不会把一致性和冲突面放大。

### 8.2.2 流式事件口径

普通聊天一旦引入 tool loop，流式输出就不能再只有“文本 delta”一种事件。

第一阶段建议至少支持以下事件类型：

- `chunk`：最终回复文本增量
- `tool_call_start`：开始调用某个工具
- `tool_call_result`：某个工具执行完成，附带结果摘要
- `completed`：本轮 assistant turn 完成

其中：

- `tool_call_start` 至少应包含 `run_id`、`tool_call_id`、`tool_name` 与目标路径摘要
- `tool_call_result` 至少应包含 `run_id`、`tool_call_id`、`tool_name`、成功/失败状态、读取/写入摘要、`audit_id`（若有）
- 若工具执行时发现 `catalog_snapshot` 已过期，`tool_call_result` 还应显式带 `catalog_stale=true`
- 这些事件用于 UI 反馈，不改变工具协议真值

这样可以避免用户在“正在读取哪些文稿、是否已经写回”这类关键节点上只能黑盒等待。

另外还要补一条恢复语义：

- 流式断开后，前端与 runtime 都应能根据 `run_id / tool_call_id` 识别“这是已发生过的工具步骤”
- 不能因为事件重放，把同一份文稿再次写一遍

### 8.3 为什么路径提示仍然保留

即使有工具，当前文稿与勾选路径仍应保留在 prompt 中。

原因不是让模型直接“靠猜路径内容”，而是给模型一份相关文稿索引，帮助它决定：

- 这次是否需要读人物关系
- 是否需要读时间轴
- 是否需要写回某份数据层 JSON

也就是说：

- 没有工具时，路径只是弱提示
- 有了工具后，路径就变成工具调用的定位线索

### 8.4 文稿上下文应改为结构化 turn context

这里还需要把“文稿上下文如何进入 assistant turn”单独收口。

当前前端做法是把：

- 当前文稿路径
- 截断后的当前文稿内容
- 额外参考路径

直接拼进用户消息文本。

这对第一阶段工具方案并不理想。更稳的口径应是：

- `messages` 只保留真实会话消息
- 文稿上下文改走结构化 turn context
- 优先复用现有 `AssistantTurnRequestDTO.input_data`

这里的 `document_context` 应被明确为：

- assistant runtime 组装后的结构化上下文视图
- 不是前端 request DTO 的原样透传

建议结构至少包含：

```json
{
  "document_context": {
    "active_path": "正文/第一卷/第003章.md",
    "selected_paths": [
      "数据层/人物关系.json",
      "时间轴/章节索引.md"
    ],
    "write_scope": "disabled",
    "active_buffer_state": "clean",
    "snapshot_at": "2026-04-04T10:00:00Z",
    "catalog_snapshot": [
      {
        "path": "正文/第一卷/第003章.md",
        "source": "chapter",
        "document_kind": "chapter",
        "content_state": "ready",
        "writable": false
      },
      {
        "path": "数据层/人物关系.json",
        "source": "file",
        "document_kind": "data_file",
        "schema_id": "story.character_relations.v1",
        "content_state": "ready",
        "writable": true
      }
    ],
    "active_buffer_excerpt": "..."
  }
}
```

其中：

- `active_path`：当前打开文稿路径
- `selected_paths`：用户勾选的额外参考路径
- `write_scope`：runtime 当前已生效的写权限 scope，而不是前端申请值
- `active_buffer_state`：当前编辑区对应文稿是否存在未保存缓冲区，例如 `clean / dirty`
- `snapshot_at`：当前结构化文稿快照的生成时间，只用于提示其新鲜度，不承担真值语义
- `catalog_snapshot`：可选的轻量目录快照，只作为路径提示，不是独立真值源
- `active_buffer_excerpt`：可选，只作为只读提示，不得直接成为写入基线或 `base_version`
- 真实 `allowed_write_roots / allowed_write_paths` 仍由 runtime 依据 `write_grant` 生成，但建议只留在执行器内部，不要求进模型上下文

这条口径要明确：

- 额外参考文稿默认只传路径，不再把全文或长截断文本硬塞进消息历史
- `catalog_snapshot` 只放轻量元数据，不放全文，不代替 `project.list_documents`
- 当前打开文稿若需要补一段编辑区即时内容，也应放进结构化字段，而不是固化成自然语言消息
- 工具读取与写入操作只针对已持久化的项目文稿真值，不直接操作前端未保存缓冲区
- 若 `active_buffer_state=dirty`，runtime 不得签发写入用 `write_grant`，必须要求用户先保存当前文稿
- 若执行器发现 `catalog_snapshot` 与当前真实目录明显不一致，应在首个相关工具结果里显式返回 `catalog_stale=true`，并优先引导模型重新调用 `project.list_documents`
- 不允许把 `active_buffer_excerpt` 混成真实文稿最新版本，再去写回其他资料
- 若工具结果在本轮已被 assistant 消费，可以在运行时对旧结果做轻量压缩，只保留必要摘要，避免上下文快速膨胀
- 已消费的读取结果建议压缩为 `path + version + summary`
- 已完成的写入结果建议保留 `path + version + diff_summary + audit_id`
- 压缩是运行时内部行为，不改变工具返回 schema，只影响后续继续推理时回填到模型上下文的内容

---

## 9. UI 与用户交互建议

### 9.1 用户不需要在 prompt 里声明读写模式，但 UI 需要显式写权限开关

理想交互应保持自然聊天：

> 这一章写完了，看看哪些资料需要同步，直接更新。

系统内部再决定：

- 先读哪些文稿
- 改哪些文稿
- 最后返回结果

但稳定方案不应把“是否允许写回”也交给模型自行决定。

建议前端提供显式但轻量的写权限开关，例如：

- `本轮允许更新文稿`
- `当前会话允许更新文稿`

但前端与后端的职责需要再拆开：

- 前端只负责表达用户意图，例如 `requested_write_scope`
- 后端负责把当前意图解析成真实 `write_grant`
- `allowed_write_roots / allowed_write_paths` 应从后端签发结果进入 runtime，不应由前端单方面决定
- 真实 allowlist 默认只供执行器消费，不要求原样放进模型上下文

默认状态下，assistant 仍然可以：

- 读取文稿
- 判断哪些文稿需要更新
- 告诉用户“建议更新哪些文稿”

只是不会真正暴露 `project.write_document`。

### 9.2 结果回执必须明确

每次工具执行完成后，应向用户明确反馈：

- 读取了哪些文稿
- 更新了哪些文稿
- 哪些文稿判断为无需更新
- 是否出现权限拒绝或版本冲突
- 本次写入对应的 `audit_id`

建议格式：

- 已读取：`正文/第一卷/第003章.md`、`数据层/人物关系.json`
- 已更新：`数据层/人物关系.json`、`时间轴/章节索引.md`
- 未更新：`设定/势力.md`
- 审计编号：`audit_id`

### 9.3 推荐权限模式

第一阶段建议：

- 默认：只暴露 `list / search / read`
- 用户显式开启“本轮允许更新文稿”后：本轮额外暴露 `write_document`
- 用户显式开启“当前会话允许更新文稿”后：直到关闭前都持续暴露 `write_document`
- 即使写开关已打开，也建议由后端固定收窄第一阶段默认白名单，例如优先只开放 `数据层 / 时间轴 / 设定 / 附录 / 校验`
- session 级写权限应有明确过期、关闭或重签发机制，不能无限期悬挂在本地前端状态里

一旦用户在当前作用域内显式开写，不建议再为每次单独写入都弹阻塞式确认框，否则会把常见的“同步多份资料”场景重新拖回手工流程。

同时建议补一条约束：

- 第一阶段自动写入只针对“统一目录里已存在、且允许写入”的项目内文稿
- 写失败不能降级成“已跳过”或“判断无需更新”
- 未开启写权限时，写入请求必须是显式权限错误，而不是隐式忽略

---

## 10. 示例

### 10.1 示例一：同步人物关系

用户输入：

> 刚写完这一章，检查人物关系是否需要更新，必要的话直接同步。

假设当前已开启“本轮允许更新文稿”。

运行时过程：

1. 模型看到当前章节路径和已勾选文稿路径
2. 模型调用：
   - `project.read_documents([当前章节, 数据层/人物.json, 数据层/人物关系.json])`
3. 模型分析后判断需要更新人物关系
4. 模型调用：
   - `project.write_document(数据层/人物关系.json, next_content, base_version)`
5. 最终回复：
   - 已更新 `数据层/人物关系.json`
   - 依据：角色 A 与角色 B 的关系从合作转为敌对
   - 审计编号：`audit_id`

### 10.2 示例二：同步多份文稿

用户输入：

> 根据这一章，把相关设定资料一起更新。

假设当前已开启“当前会话允许更新文稿”。

运行时过程：

1. 读取当前章节
2. 读取：
   - `数据层/人物关系.json`
   - `数据层/势力关系.json`
   - `时间轴/章节索引.md`
   - `设定/伏笔.md`
3. 判断：
   - 人物关系需要改
   - 势力关系不变
   - 时间轴需要改
   - 伏笔需要补一条
4. 写回对应三份文稿
5. 回复用户“已改哪些、没改哪些”，并附本次 `audit_id`

---

## 11. 稳定性设计

### 11.1 为什么这个方案可以稳定

稳定性的关键不在“本地文件还是数据库”，而在：

- 工具集小而正交
- 输入输出契约严格、错误码稳定
- 读写权限显式分离
- 用户意图与服务端真实授权分离
- 所有工具只访问系统已知真值源
- 路径规则固定，但内部身份绑定 `document_ref`
- 服务入口固定
- 不允许模型绕过正式服务
- 写入带版本标识，冲突可显式暴露
- 每次写入都有最小审计记录
- 文件层 revision / audit 真值独立存在
- 目录索引与全文读取分层
- 统一目录聚合放在后端，不继续依赖前端临时拼树
- 统一目录能区分 `ready / empty / placeholder`，避免把占位节点误当可读文稿
- 不把 `updated_at` 或文件 mtime 当成真正版本标识
- 第一阶段关闭模型侧并行 tool call，批量读收口到单个工具，写入串行执行
- 工具执行过程对用户可见，流式事件能明确显示“读了什么、写了什么、失败在哪”
- 同一 turn 内的重复读取可以被受控缓存，减少重复 IO 与重复 token 消耗
- tool loop 具备 `run_id / tool_call_id` 幂等恢复能力
- 当前文稿存在未保存缓冲区时，不给写工具隐式放行

以及：

- 不直接复用当前“缺失 canonical 文稿返回空字符串”的读语义
- 不把“统一文稿目录”继续留在前端临时拼装

也就是说，只要文稿仍然属于这两类：

- 项目文件层
- DB 正式内容层

工具就可以稳定工作。

### 11.2 哪些做法会让系统重新变脆

以下做法应明确禁止：

- 让模型读取任意项目外文件
- 让模型直接写底层磁盘路径
- 让模型自己决定 DB 写入口
- 为了“看起来更智能”而自动猜测不存在的路径
- 文件不存在时静默补空文稿
- 把展示路径直接当成内部唯一文稿身份
- 把 `updated_at`、mtime 或前端本地时间戳直接当成 `version`
- 让前端直接决定真实 `allowed_write_roots / allowed_write_paths`
- 继续把统一目录留在前端临时拼装，再让工具层复用这份临时树
- 一次性把全部可变项目文稿都暴露成可写
- 允许模型并行发起多个写工具调用

这些行为都会把当前已经收口的真值边界重新打乱。

---

## 12. 实施方案

### 12.1 第一阶段：项目文稿工具最小闭环

内容：

1. 在 assistant runtime 增加最小 tool-calling 主循环，并先关闭模型侧并行 tool calls
2. 为 tool loop 增加显式边界，例如 `max_tool_steps` 与 `tool_loop_exhausted`
3. 新增后端统一目录层，把当前前端补 canonical 节点的逻辑下沉为 `ProjectDocumentCatalog`
4. 为四个工具定义 strict input schema、fixed output schema 与稳定错误码
   - `project_id`、`owner_id` 等上下文参数不对模型暴露
5. 为工具错误补充模型侧恢复指引，不让错误码停留在“只给前端看”的层面
6. 定义统一 `version / base_version` 语义
   - 文件层不能直接拿 mtime 充当版本
   - canonical 层要把现有内容版本封装成统一 opaque token
   - `version` 与 `audit_id` 保持职责分离
   - 后端内部仍应为 token 定义可观测的来源前缀或等价标记，便于排障，但对模型保持 opaque
7. 定义 assistant streaming 的最小工具事件协议，例如 `tool_call_start / tool_call_result / completed`
8. 实现支持 `roots / prefix / limit / cursor` 的 `project.list_documents`
   - 返回 `content_state`，显式区分 `ready / empty / placeholder`
9. 实现 `project.search_documents`
10. 实现带显式 `documents / errors / truncation` 的 `project.read_documents`
   - 执行器内部允许只读并发
   - 同一 turn 内增加轻量读缓存
   - 显式限制单次路径数与输出字符预算
   - 错误结果支持服务端生成的 `recovery_hint`
11. 实现带 `base_version / diff_summary / audit_id` 的 `project.write_document`
   - 第一阶段仅允许写入已有项目文件层文稿
   - 已知数据层 JSON 做 strict shape 校验
   - 写权限按服务端 `write_grant + allowed_write_roots / allowed_write_paths` 控制
12. 接入 `Studio` 的结构化 `document_context`、轻量 `catalog_snapshot`、显式写权限开关与 `requested_write_scope -> write_grant` 握手
   - 当前文稿 dirty 时不签发写入 grant
   - 快照至少带 `snapshot_at`
13. 记录最小工具审计信息，并为写入补齐稳定 revision / audit 真值
14. 为 tool loop 增加 `run_id / tool_call_id` 幂等恢复能力，并回传结果摘要
15. 为运行时增加已消费工具结果的轻量压缩策略，控制上下文膨胀

结果：

- 可以在对话中真实读写项目文稿
- 但只限项目文稿，不碰通用文件系统
- 默认只读，显式开启后才允许写回
- 且第一阶段只覆盖“统一目录中的已有文稿”，不把创建语义混进写回工具
- 普通聊天进入的是轻量 tool loop，而不是重型通用 agent 框架

### 12.2 后端实现落点

建议直接复用现有模块，不新起平行层：

- assistant runtime：
  - `AssistantService`
  - `assistant_execution_support`
  - 新增 `DocumentToolLoop`
  - 新增 `DocumentWriteGrantResolver`
  - 新增 `ProjectDocumentCatalog / Reader / Writer` 一类很薄的编排对象
- 项目文稿读写：
  - `ProjectService`
  - `studio_document_file_store`
- canonical 内容读写：
  - `StoryAssetService`
  - `ChapterContentService`

这里的“新增一层编排”不是要新起第二套真值服务，而是承认当前代码里缺少一个合适的统一入口。它的职责应严格限制为：

- 校验工具参数
- 绑定当前 turn 的 `project_id / owner_id / write_scope`
- 解析 `path -> document_ref`
- 绑定当前 turn 的 `run_id / tool_call_id`
- 控制当前 turn / session 的写权限暴露
- 控制显式 tool loop 边界
- 统一目录聚合
- 路径分类与批量编排
- `base_version` 冲突校验
- 最小审计记录
- 显式错误收口

它不负责：

- 自己决定内容真值
- 直接写底层数据库或磁盘
- 复制一套 outline / chapter 保存逻辑

这里还要再明确三个当前实现上的落点：

- `ProjectDocumentCatalog` 应成为 assistant 工具层看到的统一目录主入口，不能继续依赖前端临时把 canonical 节点补进树里
- 当前 `ProjectService.get_project_document()` 和 `studio_document_file_store` 只提供 `content / source / updated_at / tree` 还不够，需要补上 `document_ref / version / search / flat catalog metadata / content_state / revision-audit support`
- `DocumentToolLoop` 应在执行器内部自己做批量读取编排；读取可并发实现，但写入必须串行提交并逐次刷新版本
- 文件层需要新增稳定 revision / audit 真值，不应继续把 mtime 当作唯一可观测版本信息
- `DocumentToolLoop` 必须用 `run_id / tool_call_id` 对写入去重，避免恢复和重试造成重复提交
- `DocumentWriteGrantResolver` 应把真实 allowlist 留在执行器内部，不把它扩散成 prompt-visible context

实现层再补三条收口建议：

- 工具参数与结果 schema 优先使用 Pydantic DTO 定义，再通过 schema 导出给模型，而不是维护手写 JSON schema 字符串
- `DocumentToolLoop` 的具体实现可以是 async iterator、generator 或等价结构，但必须天然支持 streaming、cancel 和 step boundary
- per-turn 读缓存只服务当前 turn 的工具执行，不参与跨 turn 真值判断

建议执行链路：

1. `AssistantService` 先按收口后的方式准备规则、历史、消息和结构化文稿上下文
2. 若模型返回普通文本，直接结束
3. 若模型返回工具调用请求，交给受控的项目文稿工具执行器
4. 工具执行器内部调用 `ProjectService`、`StoryAssetService`、`ChapterContentService` 等正式 service
5. 工具结果写回运行时上下文
6. assistant runtime 继续下一轮推理，直到拿到最终回复

其中第一阶段还要明确两条基线：

- 文稿工具读语义不能直接照搬当前 `ProjectService.get_project_document()` 对 canonical seed 的“缺失返回空字符串”口径
- 文稿工具版本语义不能直接照搬当前 `updated_at` 或文件 mtime
- tool loop 的步数上限、超限错误和审计结果必须显式暴露，不能静默截断

这样可以保证：

- tool-calling 是 assistant runtime 的扩展，不是旁路脚本
- 文稿读写仍然经过正式业务 service
- 模型不直接碰基础设施层

### 12.3 前端接入落点

`Studio` 前端不需要重做整体交互模型，但接入并不是零成本；它需要在现有上下文选择基础上完成一次收口：

1. 当前文稿路径继续默认带入
2. 用户勾选的参考文稿路径继续带入
3. 当前“当前文稿内容直接注入消息”的做法需要同步收口
4. 文稿上下文改为通过结构化 `document_context` 透传，而不是继续拼进 `messages`
5. 路径提示改为帮助模型决定“哪些文稿值得优先读取”
6. UI 需要增加显式写权限开关，并把 scope 明确成“本轮”或“当前会话”
7. UI 只需要透传“申请什么范围的写权限”，真实允许写入的 roots / paths 由后端签发再注入 runtime
8. 工具结果区域需要能显示 `audit_id`、已更新文稿与冲突/失败信息

也就是说，当前 UI 的价值从：

- 把内容硬塞进 prompt

调整为：

- 提供相关文稿候选路径
- 作为工具读取的定位线索

这里要明确一点：这不是只改一处 composer 文案。

当前 Studio 会把：

- 当前文稿路径
- 截断后的当前文稿内容
- 额外参考路径

一起固化进会话消息的请求文本。

因此前端接入至少需要同步调整：

- 当前请求构造逻辑
- 会话历史里 `requestContent` 的持久化格式
- “历史消息是否继续保留旧上下文注入文本”的兼容口径
- 写权限 scope 的本地状态与请求透传方式
- `write_grant` 的申请、续期、失效与回放逻辑
- `input_data.document_context` 的组装与回放逻辑
- `catalog_snapshot` 的轻量构造与更新逻辑
- 当前编辑区存在未保存内容时，是否需要传 `active_buffer_excerpt` 的判定

### 12.4 第二阶段：更好的上下文检索

内容：

- 与勾选文稿联动
- 更精细的“当前上下文候选文稿”读取
- 更好的相关性排序
- 如确有必要，再评估全文检索而不是只靠路径/标题搜索
- 若一期稳定，再评估是否需要开放 canonical 文稿写回

### 12.5 第三阶段：更高层的故事维护工具

内容：

- `story.sync_context_assets`
- `story.refresh_relation_files`
- `story.update_timeline_after_chapter`

这一层不是必须的，但在基础读写稳定后，可以把高频操作再包装成故事域工具。

### 12.6 后续增强项（非第一阶段阻塞）

以下能力有明确价值，但不应阻塞第一阶段最小闭环：

1. 写入后快照与回滚提示

   价值：

   - 提升用户对“AI 自动改了几份资料”的安全感
   - 支持“刚才这次同步不对，回退到修改前”

   建议形态：

   - 每次写入或批量写入后记录一次快照
   - 回复里明确返回 `snapshot_id / can_revert`
   - UI 侧再决定是否提供“回滚这次修改”入口

   定位：

   - 属于增强层
   - 第一阶段先保证 `audit_id + base_version + diff_summary`，不为了回滚 UI 临时拼一套不完整快照机制

2. 批量写入语义

   价值：

   - 用户真实场景往往是一章触发多份资料更新
   - 比逐份独立写入更接近业务操作心智

   注意：

   - 当前真值同时覆盖文件层与 DB canonical 内容
   - 因此不应把“批量写入”简单理解成单数据库事务式的全有或全无

   建议演进顺序：

   - 第一阶段：逐份写入，但显式返回成功/失败清单
   - 后续阶段：再评估 `project.write_documents`
   - 若要增强一致性感知，更适合走“快照 + 补偿回滚”，而不是直接承诺跨存储强事务

3. 更好的并发冲突恢复体验

   价值：

   - 避免不同会话、不同窗口同时改同一文稿时相互覆盖而无感知

   建议形态：

   - 第一阶段已经要求基于 `base_version` 的冲突显式暴露
   - 后续再增强“重读最新版本并重试”的 UI 体验
   - 若以后需要更细粒度恢复，再评估是否要做合并提示或补偿操作

   定位：

   - 有价值
   - 但不应阻塞第一阶段“可稳定读写”的主目标

4. 更丰富的 diff 摘要与预览

   价值：

   - 在第一阶段已有简短 `diff_summary` 的基础上，进一步降低“整份写回”带来的不可见风险
   - 帮助模型和用户更快知道“这次到底改了哪几处”

   建议形态：

   - `write_document` 内部先读取旧内容，再计算新旧差异
   - 快照层保存完整 diff
   - 第一阶段先返回简短摘要；后续再评估是否提供更细的 diff 预览能力，避免 token 迅速膨胀

   定位：

   - 有明显价值
   - 但不应迫使第一阶段先做完整 diff 审阅系统

5. 更丰富的文稿元数据

   价值：

   - 帮助模型判断是否需要更新某份文稿
   - 为后续并发冲突检测和变更提示提供基础信息

   建议形态：

   - 第一阶段先提供 `content_state / updated_at / version / writable`
   - 后续再评估是否需要逐步增加其他可选元数据
   - 不建议一开始就塞入过多噪声字段

   定位：

   - 可以增强模型判断能力
   - 但不是第一阶段最小闭环的必要条件

6. 更丰富的工具循环治理与观测

   价值：

   - 避免模型反复读取同一批文稿或进入无意义循环
   - 帮助排查“为什么这次调用很慢 / 为什么读了很多次同一文件”

   建议形态：

   - 第一阶段已经有显式 `max_tool_steps`、审计与超限错误
   - 后续再细化记录工具调用次数、重复读取次数、读取路径、写入路径、总耗时
   - 若后续需要增加循环边界，应保持显式、可观测、可配置
   - 不允许做静默截断或偷偷吞掉工具调用

   定位：

   - 这是稳定性增强项
   - 不应把第一阶段实现拖成重型 agent 编排框架

7. 变更预览与人工接受

   价值：

   - 有助于建立用户对“AI 自动维护资料”的信任
   - 特别适合多份资料同时更新的场景

   建议形态：

   - 后端返回变更摘要和可回滚快照
   - 前端再选择是否提供“查看本次改动 / 接受 / 回滚”入口

   定位：

   - 更适合第二阶段或高级模式
   - 第一阶段不应因为审批流而让基本同步能力难以使用

---

## 13. 与当前设计的关系

本方案不改变以下正式口径：

- 普通聊天默认不依赖 Skill / Agent
- 规则继续自动注入
- 历史继续只带当前会话
- MCP 仍然是能力层

本方案只是在“普通聊天可用”的基础上，再增加：

- 项目文稿读取能力
- 项目文稿更新能力

也就是说，最终主语义会变成：

- 无工具时：`规则 + 历史 + 当前消息 + 结构化文稿上下文`
- 有工具时：`规则 + 历史 + 当前消息 + 结构化文稿上下文 + 按需文稿工具调用`

这仍然属于同一条 assistant 主路径，而不是第二套平行架构。

---

## 14. 结论

easyStory 需要的不是“像 Claude/Codex CLI 那样的通用文件代理”，而是“面向项目文稿的受控读写工具”。

这样设计的原因很明确：

- 小说场景确实需要让 AI 在聊天过程中同步多份资料
- 当前手动逐份维护成本过高
- 现有真值边界已经足够清楚，适合在此基础上做稳定工具

最关键的设计决策有七条：

1. 对模型暴露统一的“项目文稿工具”，不暴露底层 DB / 文件分叉
2. 默认只读，写入必须显式开启，并再通过服务端 allowlist 收窄真实可写范围
3. 第一阶段统一读 canonical + 文件层，但写入只覆盖已有项目文件层文稿
4. `project_id` 等系统已知上下文不让模型填写，工具契约保持最小必要参数
5. 文稿上下文走结构化 turn context，不继续把路径和截断正文硬塞进消息历史；当前文稿 dirty 时不放行写工具
6. tool loop 放在 assistant runtime 编排层，所有读写都复用现有正式服务，并返回最小版本/审计信息
7. 统一目录、版本语义、错误码和审计信息都要后端收口，不能继续依赖前端临时拼装；目录还要显式区分 `ready / empty / placeholder`

只要坚持这几条，这套能力就可以做得稳定，而且不会把当前 assistant 主路径重新搞乱。
