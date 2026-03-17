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

```python
class TokenUsage(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "token_usages"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("node_executions.id")
    )
    credential_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_credentials.id")
    )
    model_name: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[float] = mapped_column(Float)  # 估算费用（美元）
```

### 4.2 字段说明

- `node_execution_id` 可为 None，用于记录非节点执行场景的 token 消耗（如 dry-run 预估调用）
- `credential_id` 关联到 `ModelCredential`，通过 `credential.owner_type / owner_id` 可追溯费用归属（用户级或项目级）
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

```python
async def estimate_workflow_cost(
    workflow_config: WorkflowConfig,
    project_id: uuid.UUID,
) -> CostEstimate:
    """预估工作流成本（不调 LLM）"""
    total_min = 0
    total_max = 0
    node_estimates = []

    for node in workflow_config.resolved_nodes:
        # 预估上下文注入 token
        context_tokens = await estimate_context_tokens(node, project_id)

        # 预估生成 token（基于 Skill 的历史数据或默认值）
        gen_min, gen_max = estimate_generation_tokens(node)

        # 预估审核 token
        review_tokens = (
            estimate_review_tokens(node) if node.auto_review else 0
        )

        # 预估精修 token（按概率）
        fix_tokens = estimate_fix_tokens(node) if node.auto_fix else 0

        node_est = NodeEstimate(
            node_id=node.id,
            context_tokens=context_tokens,
            generation_tokens=(gen_min, gen_max),
            review_tokens=review_tokens,
            fix_tokens=fix_tokens,
        )
        node_estimates.append(node_est)

        total_min += context_tokens + gen_min + review_tokens
        total_max += context_tokens + gen_max + review_tokens + fix_tokens

    return CostEstimate(
        total_tokens=(total_min, total_max),
        estimated_cost=(
            calculate_cost(total_min),
            calculate_cost(total_max),
        ),
        node_estimates=node_estimates,
        budget_warnings=check_budget_warnings(
            total_min, total_max, project_budget
        ),
    )
```

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
| `accurate` | 在内存中真实构建上下文并计数，但**不调用 LLM** | 慢但准 | 用户主动查看详细预算时 |

**说明：**
- Dry-run 关注的是 token / 费用预估，不把数据库读取和字符串拼接耗时计入 token 成本
- 但 UI 应提示 `accurate` 模式可能较慢，因为它会真实读取内容和拼接上下文

---

## 6. Token 计数统一来源

### 6.1 设计原则

Dry-run 预估、上下文报告、执行记录、预算守卫等多处需要 token 计数。如果各自估算，容易出现"预估不超、实际超了"的不一致。因此定义 `TokenCounter` 作为单一事实来源。

### 6.2 TokenCounter 类

```python
class TokenCounter:
    """
    统一 Token 计数器（单一事实来源）。
    所有需要计数 token 的地方必须调用此类，禁止自行估算。
    """

    def __init__(self):
        self._tokenizers: dict[str, Tokenizer] = {}

    def count(self, text: str, model: str) -> int:
        """精确计数（有 tokenizer 时）"""
        tokenizer = self._get_tokenizer(model)
        return tokenizer.encode(text).length

    def estimate(self, text: str, model: str) -> int:
        """快速估算（无 tokenizer 时，按字符比估算）"""
        # 中文约 1.5 字/token，英文约 4 字符/token
        # 此比例集中配置，不允许各模块自定义
        ratio = MODEL_TOKEN_RATIOS.get(model, 1.5)
        return int(len(text) / ratio)

    def _get_tokenizer(self, model: str) -> Tokenizer:
        if model not in self._tokenizers:
            self._tokenizers[model] = load_tokenizer(model)
        return self._tokenizers[model]
```

### 6.3 调用约束

| 调用方 | 使用方法 | 场景 |
|--------|---------|------|
| BudgetGuard（预算守卫） | `TokenCounter.count()` | 精确检查，阻断超预算 |
| Dry-run（成本预估） | `TokenCounter.estimate()` | 快速预估，启动前展示 |
| ContextBuilder（上下文构建） | `TokenCounter.count()` | 报告实际 token 占用 |
| TokenUsage 记录 | LLM API 返回值 | 最权威来源，用于事后校准 |

---

## 7. 费用计算统一来源

### 7.1 ModelPricing 类

```python
class ModelPricing:
    """
    统一价格表（可配置、可版本化）。
    所有费用计算必须通过此类，禁止 hardcode 价格。
    """

    def __init__(self, config_path: str):
        self._prices = self._load_prices(config_path)

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        price = self._prices[model]
        return (
            input_tokens * price.input_per_1k / 1000
            + output_tokens * price.output_per_1k / 1000
        )
```

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
