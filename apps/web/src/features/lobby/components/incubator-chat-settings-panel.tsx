"use client";

import Link from "next/link";

import { AppSelect } from "@/components/ui/app-select";
import type { IncubatorCredentialState } from "@/features/lobby/components/incubator-chat-credential-support";
import { resolveChatOutputModeLabel } from "@/features/lobby/components/incubator-chat-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator-page-model";

export function ChatAdvancedSettings({ model }: { model: IncubatorChatModel }) {
  const summaryItems = buildChatSettingsSummaryItems(model);

  return (
    <details className="overflow-hidden rounded-[16px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.76)]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-[13px] font-medium text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] focus-visible:ring-inset">
        <span className="min-w-0">
          <span className="block">模型与连接</span>
          <span className="mt-1 flex flex-wrap gap-1">
            {summaryItems.map((item) => (
              <span
                className="rounded-full bg-[rgba(248,243,235,0.96)] px-2 py-0.5 text-[10.5px] font-normal leading-4 text-[var(--text-secondary)]"
                key={item}
              >
                {item}
              </span>
            ))}
          </span>
        </span>
        <span className="shrink-0 rounded-full bg-[rgba(248,243,235,0.92)] px-2.5 py-1 text-[11px] font-normal text-[var(--text-secondary)]">
          更多
        </span>
      </summary>
      <div className="border-t border-[var(--line-soft)] px-3 py-2.5">
        {model.credentialState === "ready" ? (
          <AdvancedSettingsForm model={model} />
        ) : (
          <CredentialSettingsEmptyState
            credentialSettingsHref={model.credentialSettingsHref}
            credentialState={model.credentialState}
          />
        )}
      </div>
    </details>
  );
}

export function updateIncubatorChatSetting<K extends keyof IncubatorChatModel["settings"]>(
  model: IncubatorChatModel,
  field: K,
  value: IncubatorChatModel["settings"][K],
) {
  model.setSettings((current) => ({ ...current, [field]: value }));
}

function AdvancedSettingsForm({ model }: { model: IncubatorChatModel }) {
  return (
    <div className="space-y-2.5">
      <p className="text-[11.5px] leading-5 text-[var(--text-secondary)]">
        仅对当前聊天生效。
      </p>
      <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,0.92fr)]">
        <ProviderSelectField model={model} />
        <TextSettingField
          label="模型名称"
          name="modelName"
          placeholder="例如：gpt-4.1"
          value={model.settings.modelName}
          onChange={(value) => updateIncubatorChatSetting(model, "modelName", value)}
        />
        <OutputModeField model={model} />
        <SystemCredentialPoolField model={model} />
      </div>
    </div>
  );
}

function ProviderSelectField({ model }: { model: IncubatorChatModel }) {
  const currentOption = model.credentialOptions.find((option) => option.provider === model.settings.provider)
    ?? model.credentialOptions[0]
    ?? null;
  const selectedProvider = model.settings.provider || model.credentialOptions[0]?.provider;

  return (
    <div className="block min-w-0" title={currentOption?.displayLabel ?? ""}>
      <span className="label-text">模型连接</span>
      <AppSelect
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

function TextSettingField({
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
      <input
        autoComplete="off"
        className="ink-input min-h-[2.5rem] min-w-0 px-3 py-2 text-[13px] leading-5"
        name={name}
        placeholder={placeholder}
        spellCheck={false}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function OutputModeField({ model }: { model: IncubatorChatModel }) {
  return (
    <div className="rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-3 py-2 md:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[12px] font-medium text-[var(--text-primary)]">回复显示方式</p>
          <p className="text-[11px] leading-4 text-[var(--text-secondary)]">仅对当前聊天生效</p>
        </div>
        <div
          aria-label="回复方式"
          className="grid min-w-0 grid-cols-2 gap-1 rounded-full bg-[rgba(255,255,255,0.8)] p-1"
          role="group"
        >
          <OutputModeButton
            active={model.settings.streamOutput}
            label="边写边显示"
            onClick={() => updateIncubatorChatSetting(model, "streamOutput", true)}
          />
          <OutputModeButton
            active={!model.settings.streamOutput}
            label="生成后整体显示"
            onClick={() => updateIncubatorChatSetting(model, "streamOutput", false)}
          />
        </div>
      </div>
    </div>
  );
}

function SystemCredentialPoolField({ model }: { model: IncubatorChatModel }) {
  return (
    <label className="flex items-start gap-2.5 rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-3 py-2 md:col-span-2">
      <input
        checked={model.settings.allowSystemCredentialPool}
        className="mt-0.5 size-4 shrink-0 accent-[var(--accent-ink)]"
        onChange={(event) =>
          updateIncubatorChatSetting(model, "allowSystemCredentialPool", event.target.checked)
        }
        type="checkbox"
      />
      <span className="min-w-0">
        <span className="block text-[12px] font-medium text-[var(--text-primary)]">
          创建项目后沿用默认模型连接
        </span>
        <span className="mt-0.5 block text-[11px] leading-4 text-[var(--text-secondary)]">
          仅影响创建后的项目。
        </span>
      </span>
    </label>
  );
}

function OutputModeButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      aria-pressed={active}
      className={`rounded-full px-3 py-1.5 text-[12px] leading-4 transition ${
        active
          ? "bg-[rgba(46,111,106,0.14)] font-medium text-[var(--accent-ink)] shadow-[0_6px_12px_rgba(46,111,106,0.08)]"
          : "text-[var(--text-secondary)] hover:bg-[rgba(255,255,255,0.96)] hover:text-[var(--text-primary)]"
      } focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] focus-visible:ring-inset`}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

function syncProviderSelection(model: IncubatorChatModel, provider: string) {
  const option = model.credentialOptions.find((item) => item.provider === provider);
  model.setSettings((current) => ({
    ...current,
    modelName: option?.defaultModel ?? "",
    provider,
  }));
}

function buildChatSettingsSummaryItems(model: IncubatorChatModel) {
  if (model.credentialState === "loading") {
    return ["正在读取模型连接"];
  }
  if (model.credentialState === "error") {
    return ["模型连接读取失败"];
  }
  if (model.credentialState === "empty") {
    return ["暂无可用模型连接"];
  }
  const option = model.credentialOptions.find((item) => item.provider === model.settings.provider)
    ?? model.credentialOptions[0];
  if (!option) {
    return ["请选择模型连接"];
  }
  const modelName = model.settings.modelName.trim() || option.defaultModel || "跟随连接默认模型";
  return [
    stripDefaultModelSuffix(option),
    modelName,
    resolveChatOutputModeLabel(model.settings.streamOutput),
  ];
}

function stripDefaultModelSuffix(option: IncubatorChatModel["credentialOptions"][number]) {
  if (!option.defaultModel) {
    return option.displayLabel;
  }
  const suffix = ` · ${option.defaultModel}`;
  return option.displayLabel.endsWith(suffix)
    ? option.displayLabel.slice(0, -suffix.length)
    : option.displayLabel;
}

function CredentialSettingsEmptyState({
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
    <div className="rounded-[14px] bg-[rgba(248,243,235,0.92)] px-3 py-2.5 text-[12px] leading-5 text-[var(--text-secondary)]">
      <p>{message}</p>
      {credentialState === "loading" ? null : (
        <Link
          className="mt-2 inline-flex text-[12px] font-medium text-[var(--accent-ink)] underline-offset-4 hover:underline"
          href={credentialSettingsHref}
        >
          前往模型连接
        </Link>
      )}
    </div>
  );
}
