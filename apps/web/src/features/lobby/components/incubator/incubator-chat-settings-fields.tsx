"use client";

import Link from "next/link";
import { Checkbox, Input, Radio } from "@arco-design/web-react";

import { AppSelect } from "@/components/ui/app-select";

import type { IncubatorCredentialState } from "@/features/shared/assistant/assistant-credential-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator/incubator-page-model";
import {
  syncProviderSelection,
  updateIncubatorChatSetting,
} from "@/features/lobby/components/incubator/incubator-chat-settings-support";
import {
  resolveIncubatorAgentId,
  resolveIncubatorHookIds,
  resolveIncubatorSkillId,
  toggleIncubatorHookId,
} from "@/features/lobby/components/incubator/incubator-chat-support";

export function AgentSelectField({
  model,
  options,
}: {
  model: IncubatorChatModel;
  options: { label: string; value: string }[];
}) {
  return (
    <div className="block min-w-0">
      <span className="label-text">Agent</span>
      <AppSelect
        ariaLabel="Agent"
        className="min-w-0"
        density="default"
        options={options}
        value={resolveIncubatorAgentId(model.settings.agentId)}
        onChange={(value) => updateIncubatorChatSetting(model, "agentId", value)}
      />
    </div>
  );
}

export function SkillSelectField({
  model,
  options,
  disabled = false,
}: {
  model: IncubatorChatModel;
  disabled?: boolean;
  options: { label: string; value: string }[];
}) {
  return (
    <div className="block min-w-0">
      <span className="label-text">Skill</span>
      <AppSelect
        ariaLabel="Skill"
        className="min-w-0"
        density="default"
        disabled={disabled}
        options={options}
        value={resolveIncubatorSkillId(model.settings.skillId)}
        onChange={(value) => updateIncubatorChatSetting(model, "skillId", value)}
      />
    </div>
  );
}

export function ProviderSelectField({ model }: { model: IncubatorChatModel }) {
  const currentOption = model.credentialOptions.find((option) => option.provider === model.settings.provider)
    ?? model.credentialOptions[0]
    ?? null;
  const selectedProvider = model.settings.provider || model.credentialOptions[0]?.provider;

  return (
    <div className="block min-w-0" title={currentOption?.displayLabel ?? ""}>
      <span className="label-text">模型连接</span>
      <AppSelect
        ariaLabel="模型连接"
        className="min-w-0"
        density="default"
        options={model.credentialOptions.map((option) => ({
          label: option.displayLabel,
          value: option.provider,
        }))}
        value={selectedProvider}
        onChange={(value) => syncProviderSelection(model, value)}
      />
    </div>
  );
}

export function HookSelectionField({
  hookOptions,
  model,
}: {
  hookOptions: { label: string; value: string; description?: string }[];
  model: IncubatorChatModel;
}) {
  const selectedHookIds = resolveIncubatorHookIds(model.settings.hookIds);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-text-primary">自动动作</span>
        <span className="text-[11px] leading-5 text-text-secondary">仅对当前聊天生效</span>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {hookOptions.map((hook) => {
          const active = selectedHookIds.includes(hook.value);
          return (
            <button
              aria-pressed={active}
              className={`rounded-2xl px-3 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 focus-visible:ring-offset-2 focus-visible:ring-offset-glass-heavy ${
                active
                  ? "bg-accent-primary/10 shadow-sm"
                  : "bg-glass shadow-xs hover:bg-glass-heavy hover:shadow-sm"
              }`}
              key={hook.value}
              type="button"
              onClick={() =>
                updateIncubatorChatSetting(
                  model,
                  "hookIds",
                  toggleIncubatorHookId(selectedHookIds, hook.value),
                )}
            >
              <span className="flex items-start gap-3">
                <span className={`mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full ${
                  active
                    ? "bg-accent-primary-muted text-accent-primary"
                    : "bg-muted text-transparent"
                }`}>
                  ✓
                </span>
                <span className="min-w-0">
                  <span className="block text-[12px] font-medium text-text-primary">{hook.label}</span>
                  {hook.description ? (
                    <span className="mt-0.5 block text-[11px] leading-5 text-text-secondary">
                      {hook.description}
                    </span>
                  ) : null}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function TextSettingField({
  label,
  name,
  onChange,
  placeholder,
  value,
}: {
  label: string;
  name: string;
  onChange: (value: string) => void;
  placeholder?: string;
  value: string;
}) {
  return (
    <label className="block min-w-0">
      <span className="label-text">{label}</span>
      <Input
        allowClear
        autoComplete="off"
        className="w-full"
        inputMode={name === "maxOutputTokens" ? "numeric" : undefined}
        maxLength={name === "maxOutputTokens" ? 7 : undefined}
        name={name}
        placeholder={placeholder}
        size="default"
        spellCheck={false}
        value={value}
        onChange={(nextValue) => onChange(nextValue)}
      />
    </label>
  );
}

export function OutputModeField({ model }: { model: IncubatorChatModel }) {
  return (
    <div className="rounded-2xl bg-glass shadow-glass px-3 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[12px] font-medium text-text-primary">回复显示方式</p>
          <p className="text-[11px] leading-4 text-text-secondary">仅对当前聊天生效</p>
        </div>
        <Radio.Group
          aria-label="回复方式"
          mode="fill"
          size="small"
          type="button"
          value={model.settings.streamOutput ? "stream" : "buffered"}
          onChange={(value) => updateIncubatorChatSetting(model, "streamOutput", value === "stream")}
        >
          <Radio value="stream">边写边显示</Radio>
          <Radio value="buffered">生成后整体显示</Radio>
        </Radio.Group>
      </div>
    </div>
  );
}

export function SystemCredentialPoolField({ model }: { model: IncubatorChatModel }) {
  return (
    <div className="rounded-2xl bg-glass shadow-glass px-3 py-2.5">
      <Checkbox
        checked={model.settings.allowSystemCredentialPool}
        onChange={(checked) => updateIncubatorChatSetting(model, "allowSystemCredentialPool", checked)}
      >
        <span className="block min-w-0">
          <span className="block text-[12px] font-medium text-text-primary">
            创建项目后沿用默认模型连接
          </span>
          <span className="mt-0.5 block text-[11px] leading-4 text-text-secondary">
            仅影响创建后的项目。
          </span>
        </span>
      </Checkbox>
    </div>
  );
}

export function CredentialSettingsEmptyState({
  credentialSettingsHref,
  credentialState,
}: {
  credentialSettingsHref: string;
  credentialState: IncubatorCredentialState;
}) {
  const message = credentialState === "loading"
    ? "正在读取模型连接。"
    : credentialState === "error"
      ? "模型连接读取失败，请前往模型连接检查。"
      : "当前没有可用模型连接，请先启用。";

  return (
    <div className="rounded-2xl bg-glass-heavy px-3 py-2.5 text-[12px] leading-5 text-text-secondary">
      <p>{message}</p>
      {credentialState === "loading" ? null : (
        <Link
          className="mt-2 inline-flex text-[12px] font-medium text-accent-primary underline-offset-4 hover:underline"
          href={credentialSettingsHref}
        >
          前往模型连接
        </Link>
      )}
    </div>
  );
}
