"use client";

import Link from "next/link";

import { AppSelect } from "@/components/ui/app-select";

import type { IncubatorCredentialState } from "./incubator-chat-credential-support";
import type { IncubatorChatModel } from "./incubator-page-model";
import {
  syncProviderSelection,
  updateIncubatorChatSetting,
} from "./incubator-chat-settings-support";
import {
  resolveIncubatorAgentId,
  resolveIncubatorHookIds,
  resolveIncubatorSkillId,
  toggleIncubatorHookId,
} from "./incubator-chat-support";

export function AgentSelectField({
  model,
  options,
}: {
  model: IncubatorChatModel;
  options: { label: string; value: string }[];
}) {
  return (
    <div className="block min-w-0">
      <span className="label-text">当前 Agent</span>
      <AppSelect
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
      <span className="label-text">当前 Skill</span>
      <AppSelect
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
        <span className="text-sm font-medium text-[var(--text-primary)]">自动动作</span>
        <span className="text-[11px] leading-5 text-[var(--text-secondary)]">仅对当前聊天生效</span>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {hookOptions.map((hook) => {
          const active = selectedHookIds.includes(hook.value);
          return (
            <button
              aria-pressed={active}
              className={`rounded-[16px] border px-3 py-2 text-left transition ${
                active
                  ? "border-[rgba(46,111,106,0.22)] bg-[rgba(46,111,106,0.1)]"
                  : "border-[rgba(101,92,82,0.1)] bg-[rgba(255,255,255,0.82)] hover:border-[rgba(46,111,106,0.16)] hover:bg-[rgba(248,243,235,0.88)]"
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
                <span className={`mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border ${
                  active
                    ? "border-[rgba(46,111,106,0.28)] bg-[rgba(46,111,106,0.14)] text-[var(--accent-ink)]"
                    : "border-[rgba(101,92,82,0.16)] bg-[rgba(255,255,255,0.88)] text-transparent"
                }`}>
                  ✓
                </span>
                <span className="min-w-0">
                  <span className="block text-[12px] font-medium text-[var(--text-primary)]">{hook.label}</span>
                  {hook.description ? (
                    <span className="mt-0.5 block text-[11px] leading-5 text-[var(--text-secondary)]">
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

export function OutputModeField({ model }: { model: IncubatorChatModel }) {
  return (
    <div className="rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-2.5 py-2">
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

export function SystemCredentialPoolField({ model }: { model: IncubatorChatModel }) {
  return (
    <label className="flex items-start gap-2.5 rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-2.5 py-2">
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
