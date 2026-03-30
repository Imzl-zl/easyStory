"use client";

import type { JsonValue } from "@/lib/api/contracts/base";

export type AssistantYamlScalar = boolean | number | string | null;
export interface AssistantYamlObject {
  [key: string]: AssistantYamlValue;
}
export type AssistantYamlValue = AssistantYamlScalar | AssistantYamlObject | AssistantYamlValue[];

type StackItem = {
  indent: number;
  object: AssistantYamlObject;
};

export function parseAssistantYamlDocument(
  source: string,
  rootKey: string,
): AssistantYamlObject {
  const significantLines = source
    .replaceAll("\r\n", "\n")
    .split("\n")
    .filter((line) => line.trim() && !line.trimStart().startsWith("#"));

  if (significantLines.length === 0) {
    throw new Error(`文件不能为空，且必须以 ${rootKey}: 开头。`);
  }
  if (significantLines[0].trim() !== `${rootKey}:`) {
    throw new Error(`文件需要以 ${rootKey}: 开头。`);
  }

  const root: AssistantYamlObject = {};
  const stack: StackItem[] = [{ indent: 0, object: root }];

  significantLines.slice(1).forEach((line, index) => {
    const indent = countLeadingSpaces(line);
    if (indent === 0 || indent % 2 !== 0) {
      throw new Error(`第 ${index + 2} 行缩进无效。`);
    }

    while (stack.length > 0 && stack.at(-1)!.indent >= indent) {
      stack.pop();
    }
    const parent = stack.at(-1)?.object;
    if (!parent) {
      throw new Error(`第 ${index + 2} 行层级无效。`);
    }

    const { key, rawValue } = splitYamlLine(line.trimStart(), `第 ${index + 2} 行`);
    if (key in parent) {
      throw new Error(`字段 ${key} 重复定义。`);
    }

    if (!rawValue.trim()) {
      const nestedObject: AssistantYamlObject = {};
      parent[key] = nestedObject;
      stack.push({ indent, object: nestedObject });
      return;
    }

    parent[key] = parseYamlScalar(rawValue.trim(), key);
  });

  return root;
}

export function assertYamlKeys(
  value: AssistantYamlObject,
  allowedKeys: readonly string[],
  label: string,
) {
  const unknownKey = Object.keys(value).find((key) => !allowedKeys.includes(key));
  if (unknownKey) {
    throw new Error(`${label} 不支持字段 ${unknownKey}。`);
  }
}

export function readOptionalYamlArray(
  value: AssistantYamlObject,
  key: string,
  label: string,
): AssistantYamlValue[] | null {
  const candidate = value[key];
  if (candidate === undefined) {
    return null;
  }
  if (!Array.isArray(candidate)) {
    throw new Error(`${label} 必须是数组。`);
  }
  return candidate;
}

export function readOptionalYamlBoolean(
  value: AssistantYamlObject,
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

export function readOptionalYamlInteger(
  value: AssistantYamlObject,
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

export function readOptionalYamlObject(
  value: AssistantYamlObject,
  key: string,
  label: string,
): AssistantYamlObject | null {
  const candidate = value[key];
  if (candidate === undefined) {
    return null;
  }
  if (typeof candidate !== "object" || Array.isArray(candidate) || candidate === null) {
    throw new Error(`${label} 必须是对象。`);
  }
  return candidate;
}

export function readRequiredYamlObject(
  value: AssistantYamlObject,
  key: string,
  label: string,
): AssistantYamlObject {
  const candidate = readOptionalYamlObject(value, key, label);
  if (candidate === null) {
    throw new Error(`${label} 不能为空。`);
  }
  return candidate;
}

export function readOptionalYamlString(
  value: AssistantYamlObject,
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

export function readRequiredYamlString(
  value: AssistantYamlObject,
  key: string,
  label: string,
): string {
  const candidate = readOptionalYamlString(value, key, label);
  if (!candidate?.trim()) {
    throw new Error(`${label} 不能为空。`);
  }
  return candidate;
}

export function validateJsonRecord(
  value: AssistantYamlObject,
  label: string,
): Record<string, JsonValue> {
  return value as Record<string, JsonValue>;
}

export function validateStringRecord(
  value: AssistantYamlObject,
  label: string,
): Record<string, string> {
  const entries = Object.entries(value);
  if (entries.some(([, item]) => typeof item !== "string")) {
    throw new Error(`${label} 需要填写“名称: 内容”的对象格式。`);
  }
  return value as Record<string, string>;
}

function countLeadingSpaces(line: string) {
  let count = 0;
  while (count < line.length && line[count] === " ") {
    count += 1;
  }
  return count;
}

function splitYamlLine(line: string, label: string) {
  const separatorIndex = line.indexOf(":");
  if (separatorIndex <= 0) {
    throw new Error(`${label} 缺少 key: value 结构。`);
  }

  return {
    key: line.slice(0, separatorIndex).trim(),
    rawValue: line.slice(separatorIndex + 1),
  };
}

function parseYamlScalar(rawValue: string, label: string): AssistantYamlValue {
  if (rawValue === "true") {
    return true;
  }
  if (rawValue === "false") {
    return false;
  }
  if (rawValue === "null") {
    return null;
  }
  if (/^-?\d+$/.test(rawValue)) {
    return Number.parseInt(rawValue, 10);
  }
  if (rawValue === "[]") {
    return [];
  }
  if (rawValue.startsWith("{") || rawValue.startsWith("[")) {
    try {
      return JSON.parse(rawValue) as AssistantYamlValue;
    } catch {
      throw new Error(`${label} 的 JSON 结构无效。`);
    }
  }
  if (rawValue.startsWith("\"") && rawValue.endsWith("\"")) {
    try {
      return JSON.parse(rawValue) as string;
    } catch {
      throw new Error(`${label} 的双引号字符串格式无效。`);
    }
  }
  if (rawValue.startsWith("'") && rawValue.endsWith("'")) {
    return rawValue.slice(1, -1);
  }
  return rawValue;
}
