"use client";

import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { listMyAssistantAgents, listMyAssistantHooks, listMyAssistantSkills } from "@/lib/api/assistant";
import { buildAssistantSkillSelectOptions } from "@/features/shared/assistant/assistant-skill-select-options";

import { prefersBufferedOutput } from "./incubator-chat-credential-support";
import { ChatCapabilitiesPanel } from "./incubator-chat-capabilities-panel";
import {
  CredentialSettingsEmptyState,
  OutputModeField,
  SystemCredentialPoolField,
  TextSettingField,
} from "./incubator-chat-settings-fields";
import type { IncubatorChatModel } from "./incubator-page-model";
import {
  buildChatSettingsSummaryItemsWithSkill,
  normalizeMaxOutputTokensInput,
  updateIncubatorChatSetting,
} from "./incubator-chat-settings-support";
import {
  INCUBATOR_CHAT_SKILL_ID,
  INCUBATOR_NO_AGENT_ID,
  INCUBATOR_NO_AGENT_LABEL,
  resolveIncubatorAgentId,
  resolveIncubatorAgentLabel,
  resolveIncubatorHookIds,
  resolveIncubatorSkillLabel,
  resolveIncubatorSkillId,
} from "./incubator-chat-support";

export function ChatAdvancedSettings({ model }: { model: IncubatorChatModel }) {
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
        defaultDescription: "系统内置",
      }),
    [skillQuery.data],
  );
  const selectedTargetLabel = resolveIncubatorAgentId(model.settings.agentId)
    ? resolveIncubatorAgentLabel(agentOptions, model.settings.agentId)
    : resolveIncubatorSkillLabel(skillOptions, model.settings.skillId);
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
    if (!skillQuery.data || model.settings.skillId === INCUBATOR_CHAT_SKILL_ID) {
      return;
    }
    const hasCurrentSkill = skillQuery.data.some(
      (item) => item.enabled && item.id === model.settings.skillId,
    );
    if (!hasCurrentSkill) {
      updateIncubatorChatSetting(model, "skillId", INCUBATOR_CHAT_SKILL_ID);
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
    </details>
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
  const helperMaxOutputTokens = currentOption?.defaultMaxOutputTokens ?? 4096;

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
              当前连接默认回复上限为 {helperMaxOutputTokens}，想让长回答更完整时再调高。
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
            onChange={(value) => updateIncubatorChatSetting(model, "modelName", value)}
          />
          <TextSettingField
            label="单次回复上限"
            name="maxOutputTokens"
            placeholder="4096"
            value={model.settings.maxOutputTokens}
            onChange={(value) =>
              updateIncubatorChatSetting(model, "maxOutputTokens", normalizeMaxOutputTokensInput(value))
            }
          />
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
