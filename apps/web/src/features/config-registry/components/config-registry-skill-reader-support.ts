import type {
  ConfigRegistryObject,
  JsonValue,
  SkillConfigDetail,
} from "@/lib/api/types";

export type SkillSchemaMode = "empty" | "io" | "variables";
export type SkillResourceKey = "model-config" | "raw-config" | "schema" | "skill-markdown";

export type SkillFieldSummary = {
  defaultValue: string | null;
  description: string | null;
  key: string;
  required: boolean;
  typeLabel: string;
};

export type SkillFieldSection = {
  emptyMessage: string;
  items: SkillFieldSummary[];
  title: string;
};

export type SkillModelRow = {
  label: string;
  value: string;
};

export type SkillResourceItem = {
  description: string;
  filename: string;
  key: SkillResourceKey;
};

const PROMPT_REF_PATTERN = /{{\s*([a-zA-Z0-9_.-]+)\s*}}/g;

export function extractSkillPromptRefs(prompt: string): string[] {
  const refs = new Set<string>();
  for (const match of prompt.matchAll(PROMPT_REF_PATTERN)) {
    const value = match[1]?.trim();
    if (value) {
      refs.add(value);
    }
  }
  return [...refs];
}

export function resolveSkillSchemaMode(detail: SkillConfigDetail): SkillSchemaMode {
  if (Object.keys(detail.variables).length > 0) {
    return "variables";
  }
  if (Object.keys(detail.inputs).length > 0 || Object.keys(detail.outputs).length > 0) {
    return "io";
  }
  return "empty";
}

export function resolveSkillSchemaModeLabel(detail: SkillConfigDetail): string {
  const mode = resolveSkillSchemaMode(detail);
  if (mode === "variables") {
    return "变量注入";
  }
  if (mode === "io") {
    return "结构化输入 / 输出";
  }
  return "未声明";
}

export function buildSkillSchemaSections(detail: SkillConfigDetail): SkillFieldSection[] {
  const mode = resolveSkillSchemaMode(detail);
  return [
    {
      emptyMessage:
        mode === "io" ? "当前 Skill 使用结构化输入 / 输出，不单列可用变量。" : "当前未声明可用变量。",
      items: buildSkillFieldSummaries(detail.variables),
      title: "可用变量",
    },
    {
      emptyMessage:
        mode === "variables" ? "当前 Skill 使用变量注入，不单列输入结构。" : "当前未声明输入结构。",
      items: buildSkillFieldSummaries(detail.inputs),
      title: "输入定义",
    },
    {
      emptyMessage:
        mode === "variables" ? "当前 Skill 使用变量注入，不单列输出结构。" : "当前未声明输出结构。",
      items: buildSkillFieldSummaries(detail.outputs),
      title: "输出定义",
    },
  ];
}

export function buildSkillModelRows(model: ConfigRegistryObject | null): SkillModelRow[] {
  if (!model) {
    return [];
  }
  const capabilities = readStringArray(model.required_capabilities);
  return [
    buildSkillModelRow("服务来源", readString(model.provider) ?? "已配置"),
    buildSkillModelRow("模型名称", readString(model.name) ?? "未单独指定"),
    buildSkillModelRow("单次回复上限", formatOptionalNumber(model.max_tokens) ?? "未设置"),
    buildSkillModelRow("发散程度", formatOptionalNumber(model.temperature) ?? "未设置"),
    buildSkillModelRow("附加能力", capabilities.length > 0 ? capabilities.join("、") : "未声明"),
  ];
}

export function buildSkillResourceItems(detail: SkillConfigDetail): SkillResourceItem[] {
  const items: SkillResourceItem[] = [
    {
      description: "说明视图，按文件式 Skill 入口展示当前能力",
      filename: "SKILL.md",
      key: "skill-markdown",
    },
  ];
  if (Object.keys(detail.variables).length > 0 || Object.keys(detail.inputs).length > 0 || Object.keys(detail.outputs).length > 0) {
    items.push({
      description: "系统生成的字段结构与输入输出定义",
      filename: "schema.generated.json",
      key: "schema",
    });
  }
  if (detail.model) {
    items.push({
      description: "系统生成的模型覆盖配置",
      filename: "model.generated.yaml",
      key: "model-config",
    });
  }
  items.push({
    description: "系统实际执行时使用的完整配置",
    filename: "runtime.generated.json",
    key: "raw-config",
  });
  return items;
}

export function buildSkillMarkdown(detail: SkillConfigDetail): string {
  const lines = [
    "---",
    `id: ${detail.id}`,
    `name: ${detail.name}`,
    `version: ${detail.version}`,
    `category: ${detail.category}`,
    `author: ${detail.author ?? "null"}`,
    `tags: ${detail.tags.length > 0 ? `[${detail.tags.join(", ")}]` : "[]"}`,
    `schema_mode: ${resolveSkillSchemaMode(detail)}`,
    "---",
    "",
    `# ${detail.name}`,
    "",
    detail.description ?? "当前还没有补充说明。",
    "",
    "## Prompt",
    "",
    "```text",
    detail.prompt.trim() || "暂无提示词。",
    "```",
  ];

  lines.push("");
  lines.push(...buildMarkdownSchemaSection(detail));

  if (detail.model) {
    lines.push("");
    lines.push("## Model");
    lines.push("");
    lines.push(...buildSkillModelRows(detail.model).map((row) => `- ${row.label}：${row.value}`));
  }

  return lines.join("\n");
}

export function buildSkillSchemaDocument(detail: SkillConfigDetail): string {
  return JSON.stringify(
    {
      inputs: detail.inputs,
      mode: resolveSkillSchemaMode(detail),
      outputs: detail.outputs,
      variables: detail.variables,
    },
    null,
    2,
  );
}

export function buildSkillModelDocument(model: ConfigRegistryObject | null): string {
  if (!model) {
    return "# 当前未单独设置模型\n";
  }
  const rows = buildSkillModelRows(model);
  return rows.map((row) => `${toYamlKey(row.label)}: ${row.value}`).join("\n");
}

function buildSkillFieldSummaries(schema: ConfigRegistryObject): SkillFieldSummary[] {
  return Object.entries(schema).map(([key, value]) => {
    if (!isObjectRecord(value)) {
      return {
        defaultValue: formatJsonValue(value),
        description: null,
        key,
        required: false,
        typeLabel: "已配置",
      };
    }
    return {
      defaultValue: formatJsonValue(value.default),
      description: readString(value.description),
      key,
      required: Boolean(value.required),
      typeLabel: readString(value.type) ?? "未声明",
    };
  });
}

function buildSkillModelRow(label: string, value: string): SkillModelRow {
  return { label, value };
}

function formatOptionalNumber(value: JsonValue | undefined): string | null {
  return typeof value === "number" ? String(value) : null;
}

function formatJsonValue(value: JsonValue | undefined): string | null {
  if (value === undefined || value === null) {
    return null;
  }
  if (typeof value === "string") {
    return value.trim() ? value : '""';
  }
  return JSON.stringify(value);
}

function isObjectRecord(value: JsonValue | undefined): value is ConfigRegistryObject {
  return Boolean(value) && !Array.isArray(value) && typeof value === "object";
}

function readString(value: JsonValue | undefined): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function readStringArray(value: JsonValue | undefined): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function buildMarkdownSchemaSection(detail: SkillConfigDetail): string[] {
  const sections = buildSkillSchemaSections(detail);
  const lines = ["## Schema", ""];
  for (const section of sections) {
    lines.push(`### ${section.title}`);
    lines.push("");
    if (section.items.length === 0) {
      lines.push(section.emptyMessage);
      lines.push("");
      continue;
    }
    lines.push(...section.items.map((item) => `- \`${item.key}\` | ${item.typeLabel} | ${item.required ? "必填" : "选填"}${item.description ? ` | ${item.description}` : ""}`));
    lines.push("");
  }
  return lines;
}

function toYamlKey(label: string): string {
  if (label === "服务来源") return "provider";
  if (label === "模型名称") return "model";
  if (label === "单次回复上限") return "max_tokens";
  if (label === "发散程度") return "temperature";
  if (label === "附加能力") return "required_capabilities";
  return label;
}
