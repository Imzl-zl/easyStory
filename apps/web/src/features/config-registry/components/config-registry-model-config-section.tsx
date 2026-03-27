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
      description="不填写时继续沿用全局或凭证默认。这里仅编辑当前配置自己的覆写字段。"
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
        使用自定义模型配置
      </label>
      {value !== null ? (
        <div className="grid gap-3 md:grid-cols-2">
          <TextField
            label="Provider"
            name="model-provider"
            value={readString(model.provider)}
            onChange={(nextValue) => updateModel({ provider: nextValue })}
          />
          <TextField
            label="Model Name"
            name="model-name"
            value={readString(model.name)}
            onChange={(nextValue) => updateModel({ name: nextValue })}
          />
          <TextField
            label="Temperature"
            inputMode="decimal"
            name="model-temperature"
            value={readNumericString(model.temperature)}
            onChange={(nextValue) => updateModel({ temperature: parseNullableNumber(nextValue) ?? 0.7 })}
          />
          <TextField
            label="Max Tokens"
            inputMode="numeric"
            name="model-max-tokens"
            value={readNumericString(model.max_tokens)}
            onChange={(nextValue) => updateModel({ max_tokens: parseNullableNumber(nextValue) ?? 4000 })}
          />
          <TextField
            label="Top P"
            inputMode="decimal"
            name="model-top-p"
            value={topPValue}
            onChange={(nextValue) => updateModel({ top_p: parseNullableNumber(nextValue) })}
          />
          <TextField
            label="Required Capabilities"
            name="model-capabilities"
            placeholder="例如：stream, tool_use"
            value={capabilities}
            onChange={(nextValue) => updateModel({ required_capabilities: splitCommaSeparated(nextValue) })}
          />
          <TextField
            label="Frequency Penalty"
            inputMode="decimal"
            name="model-frequency-penalty"
            value={frequencyPenaltyValue}
            onChange={(nextValue) => updateModel({ frequency_penalty: parseNullableNumber(nextValue) })}
          />
          <TextField
            label="Presence Penalty"
            inputMode="decimal"
            name="model-presence-penalty"
            value={presencePenaltyValue}
            onChange={(nextValue) => updateModel({ presence_penalty: parseNullableNumber(nextValue) })}
          />
          <TextField
            label="Stop Sequences"
            name="model-stop"
            placeholder="例如：END, STOP"
            value={stopSequences}
            onChange={(nextValue) => updateModel({ stop: splitCommaSeparated(nextValue) })}
          />
        </div>
      ) : null}
      {value !== null ? (
        <JsonTextAreaField
          emptyValue={buildDefaultModelConfig()}
          helpText="如果需要手工保留额外模型字段，可直接编辑这段 JSON。"
          label="模型 JSON"
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
