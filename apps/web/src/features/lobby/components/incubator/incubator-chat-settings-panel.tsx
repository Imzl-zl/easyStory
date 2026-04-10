"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Tag } from "@arco-design/web-react";
import { useQuery } from "@tanstack/react-query";

import { AppSelect } from "@/components/ui/app-select";
import { renderFloatingPanel, useFloatingPanelStyle } from "@/components/ui/floating-panel-support";
import { listMyAssistantAgents, listMyAssistantHooks, listMyAssistantSkills } from "@/lib/api/assistant";
import { buildAssistantSkillSelectOptions } from "@/features/shared/assistant/assistant-skill-select-options";
import { buildIncubatorReasoningDraftFields } from "@/features/shared/assistant/assistant-chat-support";
import {
  normalizeAssistantThinkingBudgetInput,
  normalizeAssistantReasoningDraft,
  resolveAssistantReasoningControl,
} from "@/features/shared/assistant/assistant-reasoning-support";

import { prefersBufferedOutput } from "@/features/shared/assistant/assistant-credential-support";
import { ChatCapabilitiesPanel } from "@/features/lobby/components/incubator/incubator-chat-capabilities-panel";
import {
  CredentialSettingsEmptyState,
  OutputModeField,
  SystemCredentialPoolField,
  TextSettingField,
} from "@/features/lobby/components/incubator/incubator-chat-settings-fields";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator/incubator-page-model";
import {
  buildChatSettingsSummaryItemsWithSkill,
  normalizeMaxOutputTokensInput,
  updateIncubatorChatSetting,
} from "@/features/lobby/components/incubator/incubator-chat-settings-support";
import {
  INCUBATOR_NO_AGENT_ID,
  INCUBATOR_NO_AGENT_LABEL,
  INCUBATOR_NO_SKILL_ID,
  INCUBATOR_NO_SKILL_LABEL,
  resolveIncubatorAgentId,
  resolveIncubatorAgentLabel,
  resolveIncubatorHookIds,
  resolveIncubatorSkillLabel,
  resolveIncubatorSkillId,
} from "@/features/lobby/components/incubator/incubator-chat-support";

export function ChatAdvancedSettings({ model }: { model: IncubatorChatModel }) {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const agentQuery = useQuery({
    queryKey: ["assistant-agents", "chat-selector"],
    queryFn: listMyAssistantAgents,
  });
  const skillQuery = useQuery({
    queryKey: ["assistant-skills", "chat-selector"],
    queryFn: listMyAssistantSkills,
  });
  const hookQuery = useQuery({
    queryKey: ["assistant-hooks", "chat-selector"],
    queryFn: listMyAssistantHooks,
  });
  const agentOptions = useMemo(
    () => [
      { label: INCUBATOR_NO_AGENT_LABEL, value: INCUBATOR_NO_AGENT_ID },
      ...(agentQuery.data ?? [])
        .filter((item) => item.enabled)
        .map((item) => ({ label: item.name, value: item.id })),
    ],
    [agentQuery.data],
  );
  const skillOptions = useMemo(
    () =>
      buildAssistantSkillSelectOptions(skillQuery.data ?? [], {
        leadingOptions: [{ label: INCUBATOR_NO_SKILL_LABEL, value: INCUBATOR_NO_SKILL_ID }],
      }),
    [skillQuery.data],
  );
  const selectedTargetLabel = resolveIncubatorAgentId(model.settings.agentId)
    ? resolveIncubatorAgentLabel(agentOptions, model.settings.agentId)
    : resolveIncubatorSkillId(model.settings.skillId)
      ? resolveIncubatorSkillLabel(skillOptions, model.settings.skillId)
      : null;
  const summaryItems = buildChatSettingsSummaryItemsWithSkill(model, selectedTargetLabel);
  const hookOptions = useMemo(
    () =>
      (hookQuery.data ?? [])
        .filter((item) => item.enabled)
        .map((item) => ({
          description: item.description?.trim() || buildHookEventCopy(item.event),
          label: item.name,
          value: item.id,
        })),
    [hookQuery.data],
  );
  const panelStyle = useFloatingPanelStyle(isOpen, triggerRef, {
    align: "right",
    maxHeight: 640,
    preferredWidth: 576,
    side: "bottom",
    zIndex: 160,
  });

  useEffect(() => {
    if (!agentQuery.data || !resolveIncubatorAgentId(model.settings.agentId)) {
      return;
    }
    const hasCurrentAgent = agentQuery.data.some(
      (item) => item.enabled && item.id === model.settings.agentId,
    );
    if (!hasCurrentAgent) {
      updateIncubatorChatSetting(model, "agentId", INCUBATOR_NO_AGENT_ID);
    }
  }, [agentQuery.data, model, model.settings.agentId]);

  useEffect(() => {
    if (resolveIncubatorAgentId(model.settings.agentId)) {
      return;
    }
    if (!skillQuery.data || model.settings.skillId === INCUBATOR_NO_SKILL_ID) {
      return;
    }
    const hasCurrentSkill = skillQuery.data.some(
      (item) => item.enabled && item.id === model.settings.skillId,
    );
    if (!hasCurrentSkill) {
      updateIncubatorChatSetting(model, "skillId", INCUBATOR_NO_SKILL_ID);
    }
  }, [model, model.settings.skillId, skillQuery.data]);

  useEffect(() => {
    if (!hookQuery.data) {
      return;
    }
    const enabledHookIds = new Set(hookQuery.data.filter((item) => item.enabled).map((item) => item.id));
    const nextHookIds = resolveIncubatorHookIds(model.settings.hookIds)
      .filter((item) => enabledHookIds.has(item));
    if (JSON.stringify(nextHookIds) === JSON.stringify(resolveIncubatorHookIds(model.settings.hookIds))) {
      return;
    }
    updateIncubatorChatSetting(model, "hookIds", nextHookIds);
  }, [hookQuery.data, model, model.settings.hookIds]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node;
      const targetElement = target instanceof HTMLElement ? target : target.parentElement;
      if (targetElement?.closest(".arco-trigger, .arco-select-popup")) {
        return;
      }
      if (triggerRef.current?.contains(target) || panelRef.current?.contains(target)) {
        return;
      }
      setIsOpen(false);
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen]);

  const popup = isOpen && panelStyle
    ? renderFloatingPanel(
      <div
        className="overflow-hidden rounded-[18px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.98)] shadow-[0_18px_38px_rgba(58,45,29,0.12)]"
        ref={panelRef}
        style={panelStyle}
      >
        <div className="border-b border-[var(--line-soft)] bg-[rgba(248,243,235,0.88)] px-3 py-2.5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[12px] font-medium text-[var(--text-primary)]">模型与连接</p>
              <p className="mt-0.5 text-[10.5px] leading-4 text-[var(--text-secondary)]">
                只在需要时展开，不再长期占聊天区高度。
              </p>
            </div>
            <button
              aria-label="收起模型与连接设置"
              className="rounded-full px-2 py-0.5 text-[10px] leading-4 text-[var(--text-secondary)] transition hover:bg-[rgba(255,255,255,0.72)]"
              type="button"
              onClick={() => setIsOpen(false)}
            >
              收起
            </button>
          </div>
        </div>
        <div className="overflow-y-auto px-3 py-2" style={{ maxHeight: panelStyle.maxHeight }}>
          {model.credentialState === "ready" ? (
            <AdvancedSettingsForm
              agentOptions={agentOptions}
              agentQueryError={agentQuery.error}
              hookOptions={hookOptions}
              hookQueryError={hookQuery.error}
              model={model}
              skillOptions={skillOptions}
              skillQueryError={skillQuery.error}
            />
          ) : (
            <CredentialSettingsEmptyState
              credentialSettingsHref={model.credentialSettingsHref}
              credentialState={model.credentialState}
            />
          )}
        </div>
      </div>,
    )
    : null;

  return (
    <div className="shrink-0">
      <button
        aria-expanded={isOpen}
        className="list-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] focus-visible:ring-inset"
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen((current) => !current)}
      >
        <SettingsCollapseHeader summaryItems={summaryItems} />
      </button>
      {popup}
    </div>
  );
}

function SettingsCollapseHeader({ summaryItems }: { summaryItems: string[] }) {
  const visibleItems = summaryItems.slice(0, 2);
  const hiddenCount = Math.max(summaryItems.length - visibleItems.length, 0);

  return (
    <div className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-[rgba(101,92,82,0.12)] bg-[rgba(255,255,255,0.82)] px-2.5 py-1.5">
      <span className="text-[11px] font-medium text-[var(--text-primary)]">模型与连接</span>
      <div className="hidden items-center gap-1 sm:flex">
        {visibleItems.map((item) => (
          <Tag
            bordered={false}
            className="!m-0 !rounded-full !bg-[rgba(248,243,235,0.96)] !px-2 !py-0.5 !text-[10px] !leading-4 !text-[var(--text-secondary)]"
            key={item}
            size="small"
          >
            {item}
          </Tag>
        ))}
        {hiddenCount > 0 ? (
          <Tag
            bordered={false}
            className="!m-0 !rounded-full !bg-[rgba(248,243,235,0.96)] !px-2 !py-0.5 !text-[10px] !leading-4 !text-[var(--text-secondary)]"
            size="small"
          >
            +{hiddenCount}
          </Tag>
        ) : null}
      </div>
      <span className="rounded-full bg-[rgba(248,243,235,0.92)] px-1.5 py-0.5 text-[10px] leading-4 text-[var(--text-secondary)]">
        设置
      </span>
    </div>
  );
}

function AdvancedSettingsForm({
  agentOptions,
  agentQueryError,
  hookOptions,
  hookQueryError,
  model,
  skillOptions,
  skillQueryError,
}: {
  agentOptions: { label: string; value: string }[];
  agentQueryError: unknown;
  hookOptions: { label: string; value: string; description?: string }[];
  hookQueryError: unknown;
  model: IncubatorChatModel;
  skillOptions: { label: string; value: string }[];
  skillQueryError: unknown;
}) {
  const currentOption = model.credentialOptions.find((option) => option.provider === model.settings.provider) ?? null;
  const helperMaxOutputTokens = currentOption?.defaultMaxOutputTokens ?? null;

  return (
    <div className="space-y-3">
      <ChatCapabilitiesPanel
        agentOptions={agentOptions}
        agentQueryError={agentQueryError}
        hookOptions={hookOptions}
        hookQueryError={hookQueryError}
        model={model}
        skillOptions={skillOptions}
        skillQueryError={skillQueryError}
      />

      <section className="space-y-3 rounded-[16px] border border-[rgba(101,92,82,0.1)] bg-[rgba(255,255,255,0.74)] px-3 py-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[12px] font-medium text-[var(--text-primary)]">回复细节</p>
            <p className="mt-1 text-[11px] leading-5 text-[var(--text-secondary)]">
              {helperMaxOutputTokens == null
                ? "留空时不显式覆写单次回复上限，交给当前连接或上游模型默认处理。"
                : `留空时不显式覆写单次回复上限；当前连接声明的默认上限为 ${helperMaxOutputTokens}。`}
            </p>
          </div>
          {prefersBufferedOutput(currentOption) ? (
            <span className="rounded-full bg-[rgba(58,124,165,0.08)] px-2.5 py-1 text-[10.5px] text-[var(--accent-info)]">
              当前连接更适合生成后整体显示
            </span>
          ) : null}
        </div>
        <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.92fr)]">
          <TextSettingField
            label="模型名称"
            name="modelName"
            placeholder="例如：gpt-4.1"
            value={model.settings.modelName}
            onChange={(value) =>
              model.setSettings((current) => {
                const normalized = normalizeAssistantReasoningDraft(
                  buildIncubatorReasoningDraftFields(current),
                  resolveAssistantReasoningControl({
                    apiDialect: model.selectedCredential?.apiDialect ?? null,
                    modelName: value,
                  }),
                );
                return {
                  ...current,
                  modelName: value,
                  reasoningEffort: normalized.reasoningEffort,
                  thinkingBudget: normalized.thinkingBudget,
                  thinkingLevel: normalized.thinkingLevel,
                };
              })}
          />
          <TextSettingField
            label="单次回复上限"
            name="maxOutputTokens"
            placeholder={helperMaxOutputTokens == null ? "留空跟随连接/上游默认" : String(helperMaxOutputTokens)}
            value={model.settings.maxOutputTokens}
            onChange={(value) =>
              updateIncubatorChatSetting(model, "maxOutputTokens", normalizeMaxOutputTokensInput(value))
            }
          />
          <IncubatorReasoningField model={model} />
          <OutputModeField model={model} />
          <SystemCredentialPoolField model={model} />
        </div>
      </section>
    </div>
  );
}

function buildHookEventCopy(event: "before_assistant_response" | "after_assistant_response") {
  return event === "before_assistant_response" ? "回复前先处理" : "回复后自动处理";
}

function IncubatorReasoningField({ model }: { model: IncubatorChatModel }) {
  const control = resolveAssistantReasoningControl({
    apiDialect: model.selectedCredential?.apiDialect ?? null,
    modelName: model.settings.modelName || model.selectedCredential?.defaultModel,
  });
  const updateReasoning = (updater: (current: IncubatorChatModel["settings"]) => IncubatorChatModel["settings"]) =>
    model.setSettings((current) => {
      const next = updater(current);
      const normalized = normalizeAssistantReasoningDraft(
        buildIncubatorReasoningDraftFields(next),
        control,
      );
      return {
        ...next,
        reasoningEffort: normalized.reasoningEffort,
        thinkingBudget: normalized.thinkingBudget,
        thinkingLevel: normalized.thinkingLevel,
      };
    });

  if (control.kind === "none") {
    return (
      <div className="rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-3 py-2.5 text-[11px] leading-5 text-[var(--text-secondary)]">
        {control.description}
      </div>
    );
  }
  if (control.kind === "gemini_budget") {
    return (
      <div className="space-y-2 rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-3 py-2.5">
        <div>
          <p className="text-[12px] font-medium text-[var(--text-primary)]">{control.title}</p>
          <p className="mt-0.5 text-[11px] leading-5 text-[var(--text-secondary)]">{control.description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ReasoningChoiceButton
            active={model.settings.thinkingBudget === ""}
            label="跟随默认"
            onClick={() => updateReasoning((current) => ({ ...current, thinkingBudget: "" }))}
          />
          {control.allowDisable ? (
            <ReasoningChoiceButton
              active={model.settings.thinkingBudget === "0"}
              label="关闭思考"
              onClick={() => updateReasoning((current) => ({ ...current, thinkingBudget: "0" }))}
            />
          ) : null}
          {control.allowDynamic ? (
            <ReasoningChoiceButton
              active={model.settings.thinkingBudget === "-1"}
              label="动态思考"
              onClick={() => updateReasoning((current) => ({ ...current, thinkingBudget: "-1" }))}
            />
          ) : null}
        </div>
        <TextSettingField
          label="思考预算"
          name="thinkingBudget"
          placeholder={control.placeholder}
          value={model.settings.thinkingBudget}
          onChange={(value) =>
            updateReasoning((current) => ({
              ...current,
              thinkingBudget: normalizeAssistantThinkingBudgetInput(value),
            }))}
        />
      </div>
    );
  }

  const value = control.kind === "openai" ? model.settings.reasoningEffort : model.settings.thinkingLevel;
  return (
    <div className="space-y-2 rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.88)] px-3 py-2.5">
      <label className="text-[12px] font-medium text-[var(--text-primary)]">{control.title}</label>
      <AppSelect
        ariaLabel={control.title}
        className="min-w-0"
        density="default"
        options={control.options}
        value={value}
        onChange={(nextValue) =>
          updateReasoning((current) => ({
            ...current,
            ...(control.kind === "openai"
              ? { reasoningEffort: nextValue }
              : { thinkingLevel: nextValue }),
          }))}
      />
      <p className="text-[11px] leading-5 text-[var(--text-secondary)]">{control.description}</p>
    </div>
  );
}

function ReasoningChoiceButton({
  active,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className={`rounded-full border px-3 py-1 text-[11px] transition ${
        active
          ? "border-[rgba(46,111,106,0.22)] bg-[rgba(46,111,106,0.1)] text-[var(--accent-ink)]"
          : "border-[rgba(101,92,82,0.1)] bg-white text-[var(--text-secondary)]"
      }`}
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  );
}
