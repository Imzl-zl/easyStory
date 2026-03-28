import type {
  AgentConfigDetail,
  AgentConfigSummary,
  ConfigRegistryDetail,
  ConfigRegistryModelReference,
  ConfigRegistryObject,
  ConfigRegistrySummary,
  ConfigRegistryType,
  HookConfigDetail,
  HookConfigSummary,
  JsonValue,
  McpServerConfigDetail,
  McpServerConfigSummary,
  SkillConfigDetail,
  SkillConfigSummary,
  WorkflowConfigDetail,
  WorkflowConfigSummary,
} from "@/lib/api/types";

export type ConfigRegistryTabOption = {
  description: string;
  key: ConfigRegistryType;
  label: string;
};

export type ConfigRegistryMetaRow = {
  label: string;
  value: string;
};

const CONFIG_REGISTRY_TABS: ConfigRegistryTabOption[] = [
  { key: "skills", label: "Skills", description: "技能配置" },
  { key: "agents", label: "Agents", description: "角色配置" },
  { key: "hooks", label: "Hooks", description: "触发动作" },
  { key: "mcp_servers", label: "MCP", description: "MCP 服务" },
  { key: "workflows", label: "Workflows", description: "流程配置" },
];

export function listConfigRegistryTabs(): ConfigRegistryTabOption[] {
  return CONFIG_REGISTRY_TABS;
}

export function resolveConfigRegistryType(value: string | null): ConfigRegistryType {
  return CONFIG_REGISTRY_TABS.some((tab) => tab.key === value) ? (value as ConfigRegistryType) : "skills";
}

export function buildConfigRegistryPathWithParams(
  pathname: string,
  currentSearch: string,
  patches: Record<string, string | null>,
): string {
  const next = new URLSearchParams(currentSearch);
  Object.entries(patches).forEach(([key, value]) => {
    if (value === null) {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  const search = next.toString();
  return search ? `${pathname}?${search}` : pathname;
}

export function resolveActiveConfigId<T extends { id: string }>({
  items,
  selectedId,
}: {
  items: T[];
  selectedId: string | null;
}): string | null {
  if (selectedId && items.some((item) => item.id === selectedId)) {
    return selectedId;
  }
  return items[0]?.id ?? null;
}

export function resolveConfigRegistryRoutePatches({
  activeItemId,
  hasLoadedList,
  routeItemId,
  routeType,
  type,
}: {
  activeItemId: string | null;
  hasLoadedList: boolean;
  routeItemId: string | null;
  routeType: string | null;
  type: ConfigRegistryType;
}): Record<string, string | null> | null {
  const patches: Record<string, string | null> = {};
  let hasChanges = false;

  if (routeType !== type) {
    patches.type = type;
    hasChanges = true;
  }
  if (!hasLoadedList) {
    return hasChanges ? patches : null;
  }

  const normalizedRouteItemId = routeItemId ?? null;
  if (normalizedRouteItemId !== activeItemId) {
    patches.item = activeItemId;
    hasChanges = true;
  }
  return hasChanges ? patches : null;
}

export function parseConfigRegistryDocument(value: string): {
  errorMessage: string | null;
  parsed: ConfigRegistryObject | null;
} {
  try {
    const parsed = JSON.parse(value) as JsonValue;
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      return {
        errorMessage: "完整配置需要是对象格式。",
        parsed: null,
      };
    }
    return { errorMessage: null, parsed: parsed as ConfigRegistryObject };
  } catch (error) {
    return {
      errorMessage: error instanceof Error ? `完整配置格式有误：${error.message}` : "完整配置格式有误。",
      parsed: null,
    };
  }
}

export function formatConfigRegistryDocument(detail: ConfigRegistryDetail): string {
  return JSON.stringify(detail, null, 2);
}

export function buildConfigRegistrySummaryRows(
  type: ConfigRegistryType,
  summary: ConfigRegistrySummary,
): ConfigRegistryMetaRow[] {
  switch (type) {
    case "skills":
      return buildSkillSummaryRows(summary as SkillConfigSummary);
    case "agents":
      return buildAgentSummaryRows(summary as AgentConfigSummary);
    case "hooks":
      return buildHookSummaryRows(summary as HookConfigSummary);
    case "mcp_servers":
      return buildMcpServerSummaryRows(summary as McpServerConfigSummary);
    case "workflows":
      return buildWorkflowSummaryRows(summary as WorkflowConfigSummary);
  }
}

export function buildConfigRegistryDetailRows(
  type: ConfigRegistryType,
  detail: ConfigRegistryDetail,
): ConfigRegistryMetaRow[] {
  switch (type) {
    case "skills":
      return buildSkillDetailRows(detail as SkillConfigDetail);
    case "agents":
      return buildAgentDetailRows(detail as AgentConfigDetail);
    case "hooks":
      return buildHookDetailRows(detail as HookConfigDetail);
    case "mcp_servers":
      return buildMcpServerDetailRows(detail as McpServerConfigDetail);
    case "workflows":
      return buildWorkflowDetailRows(detail as WorkflowConfigDetail);
  }
}

function buildSkillSummaryRows(summary: SkillConfigSummary): ConfigRegistryMetaRow[] {
  return [
    { label: "分类", value: summary.category },
    { label: "输入 / 输出", value: `${summary.input_keys.length} / ${summary.output_keys.length}` },
    { label: "模型", value: formatModelLabel(summary.model) },
  ];
}

function buildAgentSummaryRows(summary: AgentConfigSummary): ConfigRegistryMetaRow[] {
  return [
    { label: "类型", value: formatAgentType(summary.agent_type) },
    { label: "Skills", value: formatList(summary.skill_ids) },
    { label: "MCP", value: formatList(summary.mcp_servers) },
  ];
}

function buildHookSummaryRows(summary: HookConfigSummary): ConfigRegistryMetaRow[] {
  return [
    { label: "触发事件", value: formatHookEvent(summary.trigger_event) },
    { label: "动作", value: formatHookAction(summary.action_type) },
    { label: "状态", value: summary.enabled ? "已启用" : "已停用" },
  ];
}

function buildWorkflowSummaryRows(summary: WorkflowConfigSummary): ConfigRegistryMetaRow[] {
  return [
    { label: "模式", value: formatWorkflowMode(summary.mode) },
    { label: "节点", value: `${summary.node_count} 个` },
    { label: "默认精修", value: summary.default_fix_skill ?? "未配置" },
  ];
}

function buildMcpServerSummaryRows(summary: McpServerConfigSummary): ConfigRegistryMetaRow[] {
  return [
    { label: "连接方式", value: formatTransport(summary.transport) },
    { label: "状态", value: summary.enabled ? "已启用" : "已停用" },
    { label: "超时", value: `${summary.timeout} 秒` },
  ];
}

function buildSkillDetailRows(detail: SkillConfigDetail): ConfigRegistryMetaRow[] {
  return [
    { label: "分类", value: detail.category },
    { label: "变量", value: `${Object.keys(detail.variables).length} 个` },
    { label: "输入 / 输出", value: `${Object.keys(detail.inputs).length} / ${Object.keys(detail.outputs).length}` },
    { label: "模型", value: formatModelLabel(detail.model) },
  ];
}

function buildAgentDetailRows(detail: AgentConfigDetail): ConfigRegistryMetaRow[] {
  return [
    { label: "类型", value: formatAgentType(detail.agent_type) },
    { label: "Skills", value: formatList(detail.skill_ids) },
    { label: "输出格式", value: detail.output_schema ? `${Object.keys(detail.output_schema).length} 个字段` : "未配置" },
    { label: "MCP", value: formatList(detail.mcp_servers) },
  ];
}

function buildHookDetailRows(detail: HookConfigDetail): ConfigRegistryMetaRow[] {
  return [
    { label: "状态", value: detail.enabled ? "已启用" : "已停用" },
    { label: "触发事件", value: formatHookEvent(detail.trigger.event) },
    { label: "适用节点", value: formatHookNodeTypes(detail.trigger.node_types) },
    { label: "重试", value: detail.retry ? `${detail.retry.max_attempts} 次 / ${detail.retry.delay} 秒` : "关闭" },
  ];
}

function buildMcpServerDetailRows(detail: McpServerConfigDetail): ConfigRegistryMetaRow[] {
  return [
    { label: "连接方式", value: formatTransport(detail.transport) },
    { label: "地址", value: detail.url },
    { label: "请求头", value: `${Object.keys(detail.headers).length} 个` },
    { label: "超时", value: `${detail.timeout} 秒` },
    { label: "状态", value: detail.enabled ? "已启用" : "已停用" },
  ];
}

function buildWorkflowDetailRows(detail: WorkflowConfigDetail): ConfigRegistryMetaRow[] {
  return [
    { label: "模式", value: formatWorkflowMode(detail.mode) },
    { label: "节点", value: `${detail.nodes.length} 个` },
    { label: "变更记录", value: `${detail.changelog.length} 条` },
    { label: "上下文注入", value: detail.context_injection ? "已配置" : "未配置" },
  ];
}

function formatList(values: string[]): string {
  return values.length > 0 ? values.join("、") : "未配置";
}

function formatModelLabel(
  model: ConfigRegistryModelReference | ConfigRegistryObject | null,
): string {
  if (!model) {
    return "未配置";
  }
  const provider = readOptionalString(model, "provider");
  const name = readOptionalString(model, "name");
  const parts = [provider, name].filter(Boolean);
  return parts.length > 0 ? parts.join(" / ") : "已配置";
}

function formatAgentType(value: string): string {
  if (value === "writer") return "写作助手";
  if (value === "reviewer") return "审稿助手";
  if (value === "checker") return "检查助手";
  return value;
}

function formatHookAction(value: string): string {
  if (value === "script") return "脚本";
  if (value === "webhook") return "回调请求";
  if (value === "agent") return "Agent";
  if (value === "mcp") return "MCP";
  return value;
}

function formatHookEvent(value: string): string {
  if (value === "before_workflow_start") return "流程开始前";
  if (value === "after_workflow_end") return "流程结束后";
  if (value === "before_node_start") return "节点开始前";
  if (value === "after_node_end") return "节点结束后";
  if (value === "before_generate") return "生成前";
  if (value === "after_generate") return "生成后";
  if (value === "before_review") return "审阅前";
  if (value === "after_review") return "审阅后";
  if (value === "on_review_fail") return "审阅失败时";
  if (value === "before_fix") return "修复前";
  if (value === "after_fix") return "修复后";
  if (value === "before_assistant_response") return "助手回复前";
  if (value === "after_assistant_response") return "助手回复后";
  if (value === "on_error") return "出错时";
  return value;
}

function formatHookNodeTypes(values: string[]): string {
  if (values.length === 0) {
    return "未限制";
  }
  return values.map((value) => {
    if (value === "generate") return "生成";
    if (value === "review") return "审阅";
    if (value === "export") return "导出";
    return value;
  }).join("、");
}

function formatTransport(value: string): string {
  if (value === "streamable_http") {
    return "流式 HTTP";
  }
  return value;
}

function formatWorkflowMode(value: string): string {
  if (value === "manual") return "手动";
  if (value === "auto") return "自动";
  return value;
}

function readOptionalString(
  source: ConfigRegistryModelReference | ConfigRegistryObject,
  key: "provider" | "name",
): string | null {
  const value = source[key];
  return typeof value === "string" && value.trim() ? value : null;
}
