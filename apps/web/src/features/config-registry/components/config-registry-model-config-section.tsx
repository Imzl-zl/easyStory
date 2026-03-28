"use client";

import { useState } from "react";

import type { ConfigRegistryObject } from "@/lib/api/types";

import { FormSection, TextField } from "./config-registry-form-fields";
import {
  buildDefaultModelConfig,
  patchModelConfig,
  validateJsonObject,
} from "./config-registry-form-support";
import { JsonTextAreaField } from "./config-registry-json-field";

export function ModelConfigSection({
  onChange,
  onErrorChange,
  resetToken,
  value,
}: Readonly<{
  onChange: (value: ConfigRegistryObject | null) => void;
  onErrorChange: (message: string | null) => void;
  resetToken?: number | string;
  value: ConfigRegistryObject | null;
}>) {
  const model = value ?? buildDefaultModelConfig();
  const [jsonSyncVersion, setJsonSyncVersion] = useState(0);
  const updateModel = (patch: Partial<ConfigRegistryObject>) => {
    if (value === null) {
      return;
    }
    onErrorChange(null);
    setJsonSyncVersion((current) => current + 1);
    onChange(patchModelConfig(value, patch));
  };
  const topPValue = readNumericString(model.top_p);
  const frequencyPenaltyValue = readNumericString(model.frequency_penalty);
  const presencePenaltyValue = readNumericString(model.presence_penalty);
  const stopSequences = Array.isArray(model.stop) ? model.stop.join(", ") : "";
  const capabilities = Array.isArray(model.required_capabilities)
    ? model.required_capabilities.join(", ")
    : "";

  return (
    <FormSection
      title="模型配置"
      description="需要覆盖默认模型设置时再填写。"
    >
      <label className="flex items-center gap-3 text-sm text-[var(--text-primary)]">
        <input
          checked={value !== null}
          type="checkbox"
          onChange={(event) => {
            if (!event.target.checked) {
              onErrorChange(null);
              setJsonSyncVersion((current) => current + 1);
              onChange(null);
              return;
            }
            onErrorChange(null);
            setJsonSyncVersion((current) => current + 1);
            onChange(model);
          }}
        />
        单独设置模型
      </label>
      {value !== null ? (
        <div className="grid gap-3 md:grid-cols-2">
          <TextField
            label="服务来源"
            name="model-provider"
            value={readString(model.provider)}
            onChange={(nextValue) => updateModel({ provider: nextValue })}
          />
          <TextField
            label="模型名称"
            name="model-name"
            value={readString(model.name)}
            onChange={(nextValue) => updateModel({ name: nextValue })}
          />
          <TextField
            label="发散程度"
            inputMode="decimal"
            name="model-temperature"
            value={readNumericString(model.temperature)}
            onChange={(nextValue) => updateModel({ temperature: parseNullableNumber(nextValue) ?? 0.7 })}
          />
          <TextField
            label="单次回复上限"
            inputMode="numeric"
            name="model-max-tokens"
            value={readNumericString(model.max_tokens)}
            onChange={(nextValue) => updateModel({ max_tokens: parseNullableNumber(nextValue) ?? 4000 })}
          />
          <TextField
            label="采样范围"
            inputMode="decimal"
            name="model-top-p"
            value={topPValue}
            onChange={(nextValue) => updateModel({ top_p: parseNullableNumber(nextValue) })}
          />
          <TextField
            label="附加能力"
            name="model-capabilities"
            placeholder="例如：流式回复、工具调用"
            value={capabilities}
            onChange={(nextValue) => updateModel({ required_capabilities: splitCommaSeparated(nextValue) })}
          />
          <TextField
            label="重复抑制"
            inputMode="decimal"
            name="model-frequency-penalty"
            value={frequencyPenaltyValue}
            onChange={(nextValue) => updateModel({ frequency_penalty: parseNullableNumber(nextValue) })}
          />
          <TextField
            label="新意倾向"
            inputMode="decimal"
            name="model-presence-penalty"
            value={presencePenaltyValue}
            onChange={(nextValue) => updateModel({ presence_penalty: parseNullableNumber(nextValue) })}
          />
          <TextField
            label="停止词"
            name="model-stop"
            placeholder="例如：结束、停止"
            value={stopSequences}
            onChange={(nextValue) => updateModel({ stop: splitCommaSeparated(nextValue) })}
          />
        </div>
      ) : null}
      {value !== null ? (
        <JsonTextAreaField
          emptyValue={buildDefaultModelConfig()}
          helpText="其他字段可在下方完整配置中补充。"
          label="完整模型配置"
          minHeightClassName="min-h-32"
          parseValue={validateJsonObject}
          syncKey={`${resetToken ?? 0}:${jsonSyncVersion}`}
          value={value}
          onChange={onChange}
          onErrorChange={onErrorChange}
        />
      ) : null}
    </FormSection>
  );
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function readNumericString(value: unknown): string {
  return typeof value === "number" ? String(value) : "";
}

function splitCommaSeparated(value: string): string[] {
  const seen = new Set<string>();
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => {
      if (!item || seen.has(item)) {
        return false;
      }
      seen.add(item);
      return true;
    });
}

function parseNullableNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
