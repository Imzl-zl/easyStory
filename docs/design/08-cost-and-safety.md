# 08 - 成本控制与安全阀

| 字段 | 内容 |
|---|---|
| 文档类型 | 设计规格 |
| 所属领域 | 成本控制、执行安全、预算管理 |
| 优先级 | MVP 必须 / MVP 建议 |
| 来源 | design-review-supplement §1, §21, §23.4 |

---

## 1. 概述

easyStory 的自动工作流模式存在 token 无限消耗的风险：自动精修 + 重试可能导致成本失控，用户在启动前无法预估费用，且没有"紧急刹车"机制。

本文档定义三层防线：
1. **Token 预算系统** - 事前设限，控制上限
2. **执行安全阀** - 事中拦截，防止无限循环
3. **Dry-run 成本预估** - 启动前让用户知情决策

同时定义 **TokenCounter** 和 **ModelPricing** 作为全系统的单一事实来源，避免多处各自估算导致不一致。

---

## 2. Token 预算系统

### 2.1 预算配置

```yaml
workflow:
  budget:
    max_tokens_per_node: 50000       # 单节点最大 token
    max_tokens_per_workflow: 500000  # 单次工作流最大 token
    max_tokens_per_day: 2000000      # 每日最大 token（项目级）
    max_tokens_per_day_per_user: 3000000  # 每日最大 token（用户级，可选）
    warning_threshold: 0.8           # 80% 时告警
    on_exceed: "pause"               # 超预算策略: pause / skip / fail
```

### 2.2 预算策略说明

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| `pause` | 暂停工作流，等待用户确认 | 默认推荐，安全优先 |
| `skip` | 跳过当前节点，继续执行 | 非关键节点可容忍跳过 |
| `fail` | 终止整个工作流 | 严格预算控制场景 |

### 2.3 预算层级

- **节点级** (`max_tokens_per_node`): 防止单个节点异常消耗
- **工作流级** (`max_tokens_per_workflow`): 限制单次执行总量
- **日级（项目）** (`max_tokens_per_day`): 限制单项目每日总量
- **日级（用户）** (`max_tokens_per_day_per_user`): 限制单用户跨项目总量，防止通过多项目绕过预算

当消耗达到 `warning_threshold`（默认 80%）时触发告警通知。

### 2.4 告警阈值边界

`warning_threshold` 的**展示值和生效值必须一致**：

- 用户配置 80%，系统就在 80% 告警
- Dry-run、ContextBuilder 和预算守卫可以额外提示“估算存在误差”
- 但后端**不得**为了安全余量静默把 80% 改成 75%

如果后续确实需要安全缓冲，必须使用独立且显式的配置项，而不是偷偷改写 `warning_threshold`

---

## 3. 执行安全阀

### 3.1 安全阀配置

```yaml
workflow:
  safety:
    max_retry_per_node: 3           # 单节点最大重试
    max_fix_attempts: 3             # 最大精修次数
    max_total_retries: 10           # 整个工作流最大重试总数
    execution_timeout: 3600         # 工作流超时（秒）
    node_timeout: 300               # 单节点超时（秒）
```

### 3.2 安全阀触发条件

| 参数 | 默认值 | 触发后行为 |
|------|--------|-----------|
| `max_retry_per_node` | 3 | 标记节点失败，按工作流策略处理 |
| `max_fix_attempts` | 3 | 停止继续精修，将最后一次结果作为 `final_candidate`，再由 `on_fix_fail` 决定后续动作 |
| `max_total_retries` | 10 | 暂停整个工作流 |
| `execution_timeout` | 3600s | 超时终止工作流 |
| `node_timeout` | 300s | 超时终止当前节点 |

安全阀与预算系统协同工作：预算系统控制"花多少钱"，安全阀控制"试多少次"。

> `max_fix_attempts` 只负责**计数和刹车**，不决定章节最终是否进入主线；最终动作由 [03-review-and-fix](./03-review-and-fix.md) 中的 `on_fix_fail` 控制。

---

## 4. 成本追踪数据模型

### 4.1 TokenUsage 模型

每次 LLM 调用后记录 token 消耗，关联到项目、节点执行和凭证，用于预算检查和费用追踪。

> → 数据模型详见 [数据库设计](../specs/database-design.md) § token_usages

### 4.2 字段说明

- `node_execution_id` 可为 None，用于记录非节点执行场景的 token 消耗（如 dry-run 预估调用）
- `credential_id` 关联到 `ModelCredential`，通过 `credential.owner_type / owner_id` 可追溯费用归属（用户级或项目级）
- `usage_type` 是强制分组字段，用于稳定区分 `generate/review/fix/analysis/dry_run`
- `estimated_cost` 基于 `ModelPricing` 计算，token 数来自 LLM API 返回值（最权威来源）

---

## 5. Dry-run 成本预估

### 5.1 流程

```
用户点击"启动工作流"
  |
  v
系统弹出预估面板（不调用 LLM）
  |
  v
+----------------------------------------------+
|  工作流预估报告                                |
|                                              |
|  节点数: 52（1 大纲 + 50 章 + 1 导出）         |
|  预估 Token 消耗: 350,000 - 520,000          |
|  预估费用: $1.50 - $2.20                      |
|  预算剩余: 500,000 tokens                    |
|                                              |
|  [!] 预计在第 35-40 章触发预算告警 (80%)       |
|  [!] 预计在第 45-50 章可能触发暂停             |
|                                              |
|  节点明细:                                    |
|  +-- 大纲: ~5,000 tokens                     |
|  +-- 每章: ~6,000-8,000 tokens               |
|  |   (含上下文注入 ~3,000 + 生成 ~4,000)      |
|  +-- 审核: ~1,000 tokens/章                  |
|  +-- 精修(概率): ~5,000 tokens/次             |
|                                              |
|  [确认启动]  [调整预算]  [取消]                |
+----------------------------------------------+
```

### 5.2 预估算法

预估流程（不调用 LLM）：

1. 遍历工作流的所有解析后节点
2. 对每个节点分别预估：
   - **上下文注入 token** — 根据节点依赖的数据量估算
   - **生成 token（区间）** — 基于 Skill 的历史数据或默认值
   - **审核 token** — 审核 prompt 较短且稳定，固定估算
   - **精修 token（概率加权）** — 基于历史精修触发率
3. 汇总所有节点，输出 token 区间和费用区间
4. 对比预算配置，输出告警信息（如"预计在第 35-40 章触发告警"）

### 5.3 预估数据来源

| 数据项 | 来源 | 说明 |
|--------|------|------|
| 上下文 token | 实际上下文构建结果 | 根据节点依赖的数据量估算 |
| 生成 token | Skill 历史数据 / 默认值 | 有历史数据时更准确 |
| 审核 token | 固定估算 | 审核 prompt 较短且稳定 |
| 精修 token | 概率加权 | 基于历史精修触发率 |

### 5.4 Dry-run 精度模式

`estimate_context_tokens()` 必须支持两种模式：

| 模式 | 行为 | 代价 | 适用场景 |
|------|------|------|---------|
| `fast` | 不完整拼接全文，只读取元数据、历史均值和必要摘要做估算 | 快 | 启动按钮前默认预估 |
| `accurate` | 在内存中真实构建上下文并计数，但**不调用 LLM** | 上下文拼装更真实（MVP token 计数仍为估算） | 用户主动查看详细预算时 |

**说明：**
- Dry-run 关注的是 token / 费用预估，不把数据库读取和字符串拼接耗时计入 token 成本
- 但 UI 应提示 `accurate` 模式可能较慢，因为它会真实读取内容和拼接上下文

---

## 6. Token 计数统一来源

### 6.1 设计原则

Dry-run 预估、上下文报告、执行记录、预算守卫等多处需要 token 计数。如果各自估算，容易出现"预估不超、实际超了"的不一致。因此定义 `TokenCounter` 作为单一事实来源。

### 6.2 TokenCounter 接口契约

TokenCounter 提供两个方法：

| 方法 | 说明 | 使用场景 |
|-----|------|---------|
| `count(text, model)` | 精确计数（有 tokenizer 时） | BudgetGuard 预算检查、ContextBuilder 报告 |
| `estimate(text, model)` | 快速估算（按字符比，中文约 1.5 字/token，英文约 4 字符/token） | Dry-run 成本预估 |

**MVP 降级说明：**
- MVP 阶段暂不引入外部 tokenizer 依赖（如 tiktoken），`count()` 内部退化为调用 `estimate()`
- 这意味着 MVP 阶段所有调用方（BudgetGuard、ContextBuilder 等）使用的都是字符比估算值，精度约 ±15%
- LLM API 返回的实际 token 数（记录在 TokenUsage 中）是最权威来源，用于事后校准估算精度
- 接入 tokenizer 后，`count()` 将切换为精确计数，调用方代码无需修改（接口不变）
- `warning_threshold` 的生效值应与配置值一致；估算误差通过 UI 提示和报表说明体现，不做静默偏移

**约束：**
- 所有需要计数 token 的地方必须调用 TokenCounter，禁止自行估算
- 字符比估算系数集中配置，不允许各模块自定义

### 6.3 调用约束

| 调用方 | 使用方法 | 场景 |
|--------|---------|------|
| BudgetGuard（预算守卫） | `TokenCounter.count()` | 预算检查（MVP 为估算值，接入 tokenizer 后为精确值） |
| Dry-run（成本预估） | `TokenCounter.estimate()` | 快速预估，启动前展示 |
| ContextBuilder（上下文构建） | `TokenCounter.count()` | 报告 token 占用（MVP 为估算值） |
| TokenUsage 记录 | LLM API 返回值 | 最权威来源，用于事后校准 |

---

## 7. 费用计算统一来源

### 7.1 ModelPricing 接口契约

ModelPricing 提供统一的费用计算方法 `calculate_cost(model, input_tokens, output_tokens) → float`。

**约束：**
- 所有费用计算必须通过 ModelPricing，禁止硬编码价格
- 价格数据来自可配置文件（支持热更新）
- 价格版本化，便于追溯历史费用计算依据
- 新增模型只需在配置文件中添加条目，无需改代码

### 7.2 价格配置文件

```yaml
# config/model_pricing.yaml
version: "2026-03-16"

models:
  claude-sonnet-4-20250514:
    input_per_1k: 0.003
    output_per_1k: 0.015
    context_window: 200000

  claude-opus-4-20250115:
    input_per_1k: 0.015
    output_per_1k: 0.075
    context_window: 200000

  gpt-4o:
    input_per_1k: 0.005
    output_per_1k: 0.015
    context_window: 128000

  deepseek-v3:
    input_per_1k: 0.001
    output_per_1k: 0.002
    context_window: 128000
```

### 7.3 运维要求

- 价格表支持**热更新**（不重启服务），通过文件监听或配置中心推送
- 价格版本化（`version` 字段），便于追溯历史费用计算依据
- 新增模型只需在配置文件中添加条目，无需改代码
