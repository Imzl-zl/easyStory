import type {
  AgentConfigSummary,
  ConfigRegistrySummary,
  ConfigRegistryType,
  HookConfigSummary,
  McpServerConfigSummary,
  SkillConfigSummary,
  WorkflowConfigSummary,
} from "@/lib/api/types";

export type ConfigRegistryEditorMode = "form" | "json";
export type ConfigRegistrySortValue = "name_asc" | "name_desc";
export type ConfigRegistryStatusValue = "all" | "enabled" | "disabled";

const DEFAULT_SORT: ConfigRegistrySortValue = "name_asc";

export function isConfigRegistryFormSupported(type: ConfigRegistryType): boolean {
  return type !== "workflows";
}

export function resolveConfigRegistryEditorMode(
  type: ConfigRegistryType,
  value: string | null,
): ConfigRegistryEditorMode {
  if (!isConfigRegistryFormSupported(type)) {
    return "json";
  }
  return value === "json" ? "json" : "form";
}

export function serializeConfigRegistryEditorMode(
  type: ConfigRegistryType,
  mode: ConfigRegistryEditorMode,
): string | null {
  if (!isConfigRegistryFormSupported(type)) {
    return "json";
  }
  return mode === "json" ? "json" : null;
}

export function resolveConfigRegistrySortValue(value: string | null): ConfigRegistrySortValue {
  return value === "name_desc" ? "name_desc" : DEFAULT_SORT;
}

export function serializeConfigRegistrySortValue(value: ConfigRegistrySortValue): string | null {
  return value === DEFAULT_SORT ? null : value;
}

export function supportsConfigRegistryTagFilter(type: ConfigRegistryType): boolean {
  return type === "skills" || type === "agents" || type === "workflows";
}

export function supportsConfigRegistryStatusFilter(type: ConfigRegistryType): boolean {
  return type === "hooks" || type === "mcp_servers";
}

export function resolveConfigRegistryStatusValue(
  type: ConfigRegistryType,
  value: string | null,
): ConfigRegistryStatusValue {
  if (!supportsConfigRegistryStatusFilter(type)) {
    return "all";
  }
  if (value === "enabled" || value === "disabled") {
    return value;
  }
  return "all";
}

export function serializeConfigRegistryStatusValue(
  type: ConfigRegistryType,
  value: ConfigRegistryStatusValue,
): string | null {
  if (!supportsConfigRegistryStatusFilter(type) || value === "all") {
    return null;
  }
  return value;
}

export function parseConfigRegistryCsvParam(value: string | null): string[] {
  return value ? value.split(",").map((item) => item.trim()).filter(Boolean) : [];
}

export function serializeConfigRegistryCsvParam(values: string[]): string | null {
  const normalized = deduplicateStrings(values);
  return normalized.length > 0 ? normalized.join(",") : null;
}

export function filterConfigRegistryItems({
  items,
  query,
  sort,
  status,
  tags,
  type,
}: {
  items: ConfigRegistrySummary[];
  query: string;
  sort: ConfigRegistrySortValue;
  status: ConfigRegistryStatusValue;
  tags: string[];
  type: ConfigRegistryType;
}): ConfigRegistrySummary[] {
  const normalizedQuery = query.trim().toLowerCase();
  const normalizedTags = deduplicateStrings(tags).map((item) => item.toLowerCase());
  const filtered = items.filter((item) => {
    if (!matchesConfigRegistryQuery(item, type, normalizedQuery)) {
      return false;
    }
    if (!matchesConfigRegistryTags(item, type, normalizedTags)) {
      return false;
    }
    return matchesConfigRegistryStatus(item, type, status);
  });
  return [...filtered].sort((left: ConfigRegistrySummary, right: ConfigRegistrySummary) =>
    compareConfigRegistryName(left.name, right.name, sort),
  );
}

export function listConfigRegistryFilterTags(
  items: ConfigRegistrySummary[],
  type: ConfigRegistryType,
): string[] {
  if (!supportsConfigRegistryTagFilter(type)) {
    return [];
  }
  const tags = new Set<string>();
  items.forEach((item) => {
    if ("tags" in item && Array.isArray(item.tags)) {
      item.tags.forEach((tag) => {
        if (tag.trim()) {
          tags.add(tag);
        }
      });
    }
  });
  return Array.from(tags).sort((left: string, right: string) => left.localeCompare(right, "zh-CN"));
}

export function resolveConfigRegistryRoutePatches({
  activeItemId,
  hasLoadedList,
  mode,
  query,
  routeItemId,
  routeMode,
  routeQuery,
  routeSort,
  routeStatus,
  routeTags,
  routeType,
  sort,
  status,
  tags,
  type,
}: {
  activeItemId: string | null;
  hasLoadedList: boolean;
  mode: ConfigRegistryEditorMode;
  query: string;
  routeItemId: string | null;
  routeMode: string | null;
  routeQuery: string | null;
  routeSort: string | null;
  routeStatus: string | null;
  routeTags: string | null;
  routeType: string | null;
  sort: ConfigRegistrySortValue;
  status: ConfigRegistryStatusValue;
  tags: string[];
  type: ConfigRegistryType;
}): Record<string, string | null> | null {
  const patches: Record<string, string | null> = {};
  let hasChanges = false;

  hasChanges = assignPatch(patches, "type", routeType, type) || hasChanges;
  hasChanges =
    assignPatch(patches, "mode", routeMode, serializeConfigRegistryEditorMode(type, mode)) || hasChanges;
  hasChanges =
    assignPatch(patches, "q", routeQuery, query.trim() ? query.trim() : null) || hasChanges;
  hasChanges =
    assignPatch(patches, "sort", routeSort, serializeConfigRegistrySortValue(sort)) || hasChanges;
  hasChanges =
    assignPatch(
      patches,
      "status",
      routeStatus,
      serializeConfigRegistryStatusValue(type, status),
    ) || hasChanges;
  hasChanges =
    assignPatch(
      patches,
      "tags",
      routeTags,
      supportsConfigRegistryTagFilter(type) ? serializeConfigRegistryCsvParam(tags) : null,
    ) || hasChanges;

  if (!hasLoadedList) return hasChanges ? patches : null;
  hasChanges = assignPatch(patches, "item", routeItemId, activeItemId) || hasChanges;
  return hasChanges ? patches : null;
}

function assignPatch(
  patches: Record<string, string | null>,
  key: string,
  currentValue: string | null,
  nextValue: string | null,
): boolean {
  if (currentValue === nextValue) {
    return false;
  }
  patches[key] = nextValue;
  return true;
}

function compareConfigRegistryName(
  left: string,
  right: string,
  sort: ConfigRegistrySortValue,
): number {
  const comparison = left.localeCompare(right, "zh-CN");
  return sort === "name_desc" ? comparison * -1 : comparison;
}

function matchesConfigRegistryQuery(item: ConfigRegistrySummary, type: ConfigRegistryType, query: string): boolean {
  return !query || buildSearchTokens(item, type).some((token) => token.toLowerCase().includes(query));
}

function buildSearchTokens(item: ConfigRegistrySummary, type: ConfigRegistryType): string[] {
  const base = [item.id, item.name, item.description ?? "", item.author ?? "", item.version];
  if (type === "skills") {
    const skill = item as SkillConfigSummary;
    return [...base, skill.category, ...skill.tags, ...skill.input_keys, ...skill.output_keys];
  }
  if (type === "agents") {
    const agent = item as AgentConfigSummary;
    return [...base, agent.agent_type, ...agent.tags, ...agent.skill_ids, ...agent.mcp_servers];
  }
  if (type === "hooks") {
    const hook = item as HookConfigSummary;
    return [...base, hook.action_type, hook.trigger_event, ...hook.trigger_node_types];
  }
  if (type === "mcp_servers") {
    const mcp = item as McpServerConfigSummary;
    return [...base, mcp.transport, mcp.url];
  }
  const workflow = item as WorkflowConfigSummary;
  return [
    ...base,
    workflow.mode,
    ...workflow.tags,
    ...workflow.default_inject_types,
    ...workflow.nodes.flatMap((node) => [node.id, node.name, node.node_type]),
  ];
}

function matchesConfigRegistryTags(
  item: ConfigRegistrySummary,
  type: ConfigRegistryType,
  tags: string[],
): boolean {
  if (!supportsConfigRegistryTagFilter(type) || tags.length === 0) {
    return true;
  }
  if (!("tags" in item) || !Array.isArray(item.tags)) {
    return false;
  }
  const itemTags = item.tags.map((tag) => tag.toLowerCase());
  return tags.every((tag) => itemTags.includes(tag));
}

function matchesConfigRegistryStatus(
  item: ConfigRegistrySummary,
  type: ConfigRegistryType,
  status: ConfigRegistryStatusValue,
): boolean {
  if (status === "all" || !supportsConfigRegistryStatusFilter(type)) return true;
  const enabled = "enabled" in item ? item.enabled : false;
  return status === "enabled" ? enabled : !enabled;
}

function deduplicateStrings(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => {
    const normalized = value.trim();
    if (!normalized || seen.has(normalized)) {
      return false;
    }
    seen.add(normalized);
    return true;
  });
}
