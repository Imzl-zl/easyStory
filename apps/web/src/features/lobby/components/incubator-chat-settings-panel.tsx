"use client";

import Link from "next/link";

import { AppSelect } from "@/components/ui/app-select";
import {
  prefersBufferedOutput,
  type IncubatorCredentialState,
} from "@/features/lobby/components/incubator-chat-credential-support";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator-page-model";
import {
  buildChatSettingsSummaryItems,
  normalizeMaxOutputTokensInput,
  syncProviderSelection,
  updateIncubatorChatSetting,
} from "@/features/lobby/components/incubator-chat-settings-support";

export function ChatAdvancedSettings({ model }: { model: IncubatorChatModel }) {
  const summaryItems = buildChatSettingsSummaryItems(model);

  return (
    <details className="overflow-hidden rounded-[16px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.76)]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-1.5 text-[12.5px] font-medium text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] focus-visible:ring-inset">
        <span className="min-w-0 flex-1">
          <span className="block">模型与连接</span>
          <span className="mt-1 flex flex-wrap gap-1">
            {summaryItems.map((item) => (
              <span
                className="rounded-full bg-[rgba(248,243,235,0.96)] px-1.5 py-0.5 text-[10px] font-normal leading-4 text-[var(--text-secondary)]"
                key={item}
              >
                {item}
              </span>
            ))}
          </span>
        </span>
        <span className="shrink-0 rounded-full bg-[rgba(248,243,235,0.92)] px-2 py-0.5 text-[10.5px] font-normal text-[var(--text-secondary)]">
          设置
        </span>
      </summary>
      <div className="border-t border-[var(--line-soft)] px-3 py-2">
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

function AdvancedSettingsForm({ model }: { model: IncubatorChatModel }) {
  const currentOption = model.credentialOptions.find((option) => option.provider === model.settings.provider) ?? null;
  const helperMaxOutputTokens = currentOption?.defaultMaxOutputTokens ?? 4096;

  return (
    <div className="space-y-2">
      <p className="text-[11px] leading-5 text-[var(--text-secondary)]">
        仅对当前聊天生效。当前连接默认回复上限为 {helperMaxOutputTokens}，想让长回答更完整时再调高。
      </p>
      {prefersBufferedOutput(currentOption) ? (
        <p className="rounded-[14px] bg-[rgba(58,124,165,0.08)] px-3 py-2 text-[11px] leading-5 text-[var(--accent-info)]">
          当前这条连接更适合用“生成后整体显示”，通常会比边写边显示更稳定。
        </p>
      ) : null}
      <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_minmax(0,0.92fr)]">
        <ProviderSelectField model={model} />
        <TextSettingField
          label="模型名称"
          name="modelName"
          placeholder="例如：gpt-4.1"
          value={model.settings.modelName}
          onChange={(value) => updateIncubatorChatSetting(model, "modelName", value)}
        />
        <TextSettingField
          label="单次回复上限"
          name="maxOutputTokens"
          placeholder="4096"
          value={model.settings.maxOutputTokens}
          onChange={(value) => updateIncubatorChatSetting(
            model,
            "maxOutputTokens",
            normalizeMaxOutputTokensInput(value),
          )}
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
        className="ink-input min-h-[2.4rem] min-w-0 px-3 py-1.5 text-[12.5px] leading-5"
        inputMode={name === "maxOutputTokens" ? "numeric" : undefined}
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
    <div className="rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-2.5 py-2 md:col-span-2">
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
    <label className="flex items-start gap-2.5 rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-2.5 py-2 md:col-span-2">
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
