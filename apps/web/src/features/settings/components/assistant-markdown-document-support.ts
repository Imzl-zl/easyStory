import {
  hasIndentedChildLine,
  isFrontmatterBlockScalarMarker,
  parseFrontmatterBlockValue,
} from "./assistant-markdown-frontmatter-block-support";

export type FrontmatterScalar = boolean | number | string;
export type AssistantMarkdownFrontmatterObject = Record<string, FrontmatterScalar>;

export type AssistantMarkdownFrontmatter = Record<
  string,
  FrontmatterScalar | AssistantMarkdownFrontmatterObject
>;

export type AssistantMarkdownDocument = {
  body: string;
  frontmatter: AssistantMarkdownFrontmatter;
};

export function parseAssistantMarkdownDocument(
  source: string,
): AssistantMarkdownDocument {
  const normalized = source.replaceAll("\r\n", "\n");
  const lines = normalized.split("\n");
  if (lines[0] !== "---") {
    throw new Error("文件需要以 --- 开头。");
  }

  const closingIndex = lines.indexOf("---", 1);
  if (closingIndex < 0) {
    throw new Error("找不到 frontmatter 结束标记 ---。");
  }

  const body = lines.slice(closingIndex + 1).join("\n").replace(/^\n/, "");
  return {
    body,
    frontmatter: parseFrontmatterLines(lines.slice(1, closingIndex)),
  };
}

export function assertFrontmatterKeys(
  value: AssistantMarkdownFrontmatter,
  allowedKeys: readonly string[],
  label: string,
) {
  const unknownKey = Object.keys(value).find((key) => !allowedKeys.includes(key));
  if (unknownKey) {
    throw new Error(`${label} 不支持字段 ${unknownKey}。`);
  }
}

export function readOptionalFrontmatterBoolean(
  value: AssistantMarkdownFrontmatter,
  key: string,
  label: string,
): boolean | null {
  const candidate = value[key];
  if (candidate === undefined) {
    return null;
  }
  if (typeof candidate !== "boolean") {
    throw new Error(`${label} 必须是 true 或 false。`);
  }
  return candidate;
}

export function readOptionalFrontmatterInteger(
  value: AssistantMarkdownFrontmatter,
  key: string,
  label: string,
): number | null {
  const candidate = value[key];
  if (candidate === undefined) {
    return null;
  }
  if (typeof candidate !== "number" || !Number.isInteger(candidate)) {
    throw new Error(`${label} 必须是整数。`);
  }
  return candidate;
}

export function readOptionalFrontmatterObject(
  value: AssistantMarkdownFrontmatter,
  key: string,
  label: string,
): AssistantMarkdownFrontmatterObject | null {
  const candidate = value[key];
  if (candidate === undefined) {
    return null;
  }
  if (typeof candidate !== "object" || Array.isArray(candidate) || candidate === null) {
    throw new Error(`${label} 必须是对象。`);
  }
  return candidate;
}

export function readOptionalFrontmatterString(
  value: AssistantMarkdownFrontmatter,
  key: string,
  label: string,
): string | null {
  const candidate = value[key];
  if (candidate === undefined) {
    return null;
  }
  if (typeof candidate !== "string") {
    throw new Error(`${label} 必须是文本。`);
  }
  return candidate;
}

export function readRequiredFrontmatterString(
  value: AssistantMarkdownFrontmatter,
  key: string,
  label: string,
): string {
  const candidate = readOptionalFrontmatterString(value, key, label);
  if (!candidate?.trim()) {
    throw new Error(`${label} 不能为空。`);
  }
  return candidate;
}

function parseFrontmatterLines(lines: string[]): AssistantMarkdownFrontmatter {
  const frontmatter: AssistantMarkdownFrontmatter = {};
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (line.startsWith("  ")) {
      index = parseNestedFrontmatterLine(frontmatter, lines, index);
      continue;
    }

    if (line.startsWith(" ")) {
      throw new Error(`frontmatter 第 ${index + 1} 行缩进无效。`);
    }

    index = parseRootFrontmatterLine(frontmatter, lines, index);
  }
  return frontmatter;
}

function parseRootFrontmatterLine(
  frontmatter: AssistantMarkdownFrontmatter,
  lines: string[],
  index: number,
) {
  const line = lines[index] ?? "";
  const { key, rawValue } = splitFrontmatterLine(line, `frontmatter 第 ${index + 1} 行`);
  if (key in frontmatter) {
    throw new Error(`frontmatter 字段 ${key} 重复定义。`);
  }

  const parsed = parseFrontmatterValue(rawValue, lines, index, 0, `frontmatter.${key}`);
  frontmatter[key] = parsed.value;
  return parsed.nextIndex;
}

function parseNestedFrontmatterLine(
  frontmatter: AssistantMarkdownFrontmatter,
  lines: string[],
  index: number,
) {
  const line = lines[index] ?? "";
  const sectionKey = findLatestObjectKey(frontmatter);
  if (!sectionKey) {
    throw new Error("frontmatter 中存在未归属的缩进行。");
  }

  const section = frontmatter[sectionKey];
  if (typeof section !== "object" || Array.isArray(section) || section === null) {
    throw new Error(`frontmatter.${sectionKey} 不是对象，不能继续缩进。`);
  }

  const { key, rawValue } = splitFrontmatterLine(line.trimStart(), `frontmatter.${sectionKey}`);
  if (key in section) {
    throw new Error(`frontmatter.${sectionKey}.${key} 重复定义。`);
  }

  const parsed = parseFrontmatterValue(rawValue, lines, index, 2, `frontmatter.${sectionKey}.${key}`);
  if (typeof parsed.value === "object") {
    throw new Error(`frontmatter.${sectionKey}.${key} 不支持继续嵌套。`);
  }
  section[key] = parsed.value;
  return parsed.nextIndex;
}

function parseFrontmatterValue(
  rawValue: string,
  lines: string[],
  index: number,
  currentIndent: number,
  label: string,
): {
  nextIndex: number;
  value: FrontmatterScalar | AssistantMarkdownFrontmatterObject;
} {
  const normalizedValue = rawValue.trim();
  if (isFrontmatterBlockScalarMarker(normalizedValue)) {
    return parseFrontmatterBlockValue(lines, index + 1, currentIndent + 2, normalizedValue, label);
  }
  if (!normalizedValue && hasIndentedChildLine(lines[index + 1] ?? "", currentIndent + 2)) {
    return { nextIndex: index + 1, value: {} };
  }
  return {
    nextIndex: index + 1,
    value: parseScalarValue(normalizedValue, label),
  };
}

function splitFrontmatterLine(line: string, label: string) {
  const separatorIndex = line.indexOf(":");
  if (separatorIndex <= 0) {
    throw new Error(`${label} 缺少 key: value 结构。`);
  }

  const key = line.slice(0, separatorIndex).trim();
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(key)) {
    throw new Error(`${label} 的字段名无效。`);
  }

  return {
    key,
    rawValue: line.slice(separatorIndex + 1),
  };
}

function parseScalarValue(rawValue: string, label: string): FrontmatterScalar {
  if (rawValue === "true") {
    return true;
  }
  if (rawValue === "false") {
    return false;
  }
  if (/^-?\d+$/.test(rawValue)) {
    return Number.parseInt(rawValue, 10);
  }
  if (rawValue.startsWith("\"") && rawValue.endsWith("\"")) {
    try {
      return JSON.parse(rawValue) as string;
    } catch {
      throw new Error(`${label} 里的双引号字符串格式无效。`);
    }
  }
  if (rawValue.startsWith("'") && rawValue.endsWith("'")) {
    return rawValue.slice(1, -1);
  }
  return rawValue;
}

function findLatestObjectKey(frontmatter: AssistantMarkdownFrontmatter) {
  const keys = Object.keys(frontmatter);
  const lastKey = keys.at(-1);
  if (!lastKey) {
    return null;
  }
  return lastKey;
}
