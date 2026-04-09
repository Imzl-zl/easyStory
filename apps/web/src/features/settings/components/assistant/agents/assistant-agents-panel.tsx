"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { SectionCard } from "@/components/ui/section-card";
import {
  createMyAssistantAgent,
  deleteMyAssistantAgent,
  getMyAssistantAgent,
  listMyAssistantAgents,
  listMyAssistantSkills,
  updateMyAssistantAgent,
} from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";
import {
  buildAssistantSkillSelectOptions,
} from "@/features/shared/assistant/assistant-skill-select-options";

import { AssistantAgentEditor } from "@/features/settings/components/assistant/agents/assistant-agent-editor";
import {
  buildAssistantAgentListDescription,
  buildAssistantAgentPayload,
  type AssistantAgentDraft,
} from "@/features/settings/components/assistant/agents/assistant-agents-support";

type AssistantAgentsPanelProps = {
  onDirtyChange?: (isDirty: boolean) => void;
};

const CREATE_MODE_KEY = "__create__";

export function AssistantAgentsPanel({ onDirtyChange }: AssistantAgentsPanelProps) {
  const queryClient = useQueryClient();
  const [requestedSelection, setRequestedSelection] = useState<string | null>(null);
  const [editorDirty, setEditorDirty] = useState(false);
  const listQuery = useQuery({
    queryKey: ["assistant-agents", "me"],
    queryFn: listMyAssistantAgents,
  });
  const skillListQuery = useQuery({
    queryKey: ["assistant-skills", "agent-options"],
    queryFn: listMyAssistantSkills,
  });
  const orderedAgents = useMemo(() => listQuery.data ?? [], [listQuery.data]);
  const selection = useMemo(() => {
    if (requestedSelection === CREATE_MODE_KEY) {
      return CREATE_MODE_KEY;
    }
    if (requestedSelection && orderedAgents.some((item) => item.id === requestedSelection)) {
      return requestedSelection;
    }
    if (listQuery.isLoading) {
      return null;
    }
    return orderedAgents[0]?.id ?? CREATE_MODE_KEY;
  }, [listQuery.isLoading, orderedAgents, requestedSelection]);
  const detailQuery = useQuery({
    queryKey: ["assistant-agent", selection],
    queryFn: () => getMyAssistantAgent(selection ?? ""),
    enabled: Boolean(selection) && selection !== CREATE_MODE_KEY,
  });
  const createMutation = useMutation({
    mutationFn: (draft: AssistantAgentDraft) => createMyAssistantAgent(buildAssistantAgentPayload(draft)),
    onSuccess: async (detail) => {
      showAppNotice({ title: "Agents", content: "新的 Agent 已创建。", tone: "success" });
      setRequestedSelection(detail.id);
      await queryClient.invalidateQueries({ queryKey: ["assistant-agents", "me"] });
      await queryClient.invalidateQueries({ queryKey: ["assistant-agent", detail.id] });
    },
    onError: (error) => {
      showAppNotice({ title: "Agents", content: getErrorMessage(error), tone: "danger" });
    },
  });
  const updateMutation = useMutation({
    mutationFn: (draft: AssistantAgentDraft) =>
      updateMyAssistantAgent(selection ?? "", buildAssistantAgentPayload(draft)),
    onSuccess: async (detail) => {
      showAppNotice({ title: "Agents", content: "Agent 已保存。", tone: "success" });
      await queryClient.invalidateQueries({ queryKey: ["assistant-agents", "me"] });
      await queryClient.invalidateQueries({ queryKey: ["assistant-agent", detail.id] });
    },
    onError: (error) => {
      showAppNotice({ title: "Agents", content: getErrorMessage(error), tone: "danger" });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (agentId: string) => deleteMyAssistantAgent(agentId),
    onSuccess: async () => {
      showAppNotice({ title: "Agents", content: "Agent 已删除。", tone: "success" });
      setRequestedSelection(null);
      await queryClient.invalidateQueries({ queryKey: ["assistant-agents", "me"] });
    },
    onError: (error) => {
      showAppNotice({ title: "Agents", content: getErrorMessage(error), tone: "danger" });
    },
  });
  const isPending = createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;
  const selectedDetail = selection === CREATE_MODE_KEY ? null : detailQuery.data ?? null;
  const showCreateEditor = selection === CREATE_MODE_KEY;
  const enabledAgentCount = orderedAgents.filter((agent) => agent.enabled).length;
  const showGettingStarted = showCreateEditor && orderedAgents.length === 0;
  const skillOptions = useMemo(
    () =>
      buildAssistantSkillSelectOptions(skillListQuery.data ?? [], {
        defaultDescription: "系统内置",
        disabledDescription: "已停用，但 Agent 仍可继续绑定使用",
        includeDisabled: true,
        includeSystemDefault: true,
      }),
    [skillListQuery.data],
  );
  const skillLabelMap = useMemo(
    () => new Map(skillOptions.map((option) => [option.value, option.label])),
    [skillOptions],
  );

  useEffect(() => {
    onDirtyChange?.(editorDirty);
    return () => onDirtyChange?.(false);
  }, [editorDirty, onDirtyChange]);

  return (
    <SectionCard
      description="你的角色配置文件。想固定助手风格时，再把常用组合整理成自己的 AGENT.md。"
      title="Agents"
    >
      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="space-y-3 rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.68)] p-4 xl:sticky xl:top-6 xl:self-start">
          <div className="space-y-1 rounded-[18px] bg-[rgba(248,243,235,0.78)] px-4 py-3">
            <p className="text-sm font-medium text-[var(--text-primary)]">我的 Agents</p>
            <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
              已启用 {enabledAgentCount} 个，共 {orderedAgents.length} 个。
            </p>
          </div>
          <button
            className="ink-button w-full justify-center"
            disabled={isPending}
            type="button"
            onClick={() => attemptSelect(CREATE_MODE_KEY, editorDirty, setRequestedSelection)}
          >
            新建 Agent
          </button>
          <div className="space-y-2 xl:max-h-[28rem] xl:overflow-y-auto xl:pr-1">
            {orderedAgents.map((agent) => (
              <button
                className="ink-tab w-full justify-start rounded-[20px] px-4 py-3 text-left"
                data-active={selection === agent.id}
                key={agent.id}
                type="button"
                onClick={() => attemptSelect(agent.id, editorDirty, setRequestedSelection)}
              >
                <span className="flex flex-col items-start gap-1">
                  <span className="text-sm font-medium text-[var(--text-primary)]">{agent.name}</span>
                  <span className="text-[12px] leading-5 text-[var(--text-secondary)]">
                    {buildAssistantAgentListDescription(agent, skillLabelMap.get(agent.skill_id) ?? null)}
                  </span>
                </span>
              </button>
            ))}
            {listQuery.isLoading ? (
              <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在读取你的 Agents...</div>
            ) : null}
            {listQuery.error ? (
              <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
                {getErrorMessage(listQuery.error)}
              </div>
            ) : null}
            {showGettingStarted ? (
              <div className="rounded-2xl bg-[rgba(248,243,235,0.84)] px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
                右侧已经放好一份起步模板。你也可以切到“按文件编辑”，直接按 AGENT.md 的格式来写。
              </div>
            ) : null}
          </div>
        </aside>
        <div className="space-y-4">
          {listQuery.isLoading && !selection ? (
            <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在准备 Agents...</div>
          ) : null}
          {showCreateEditor ? (
            <AssistantAgentEditor
              key={CREATE_MODE_KEY}
              detail={null}
              isPending={isPending}
              mode="create"
              skillErrorMessage={skillListQuery.error ? getErrorMessage(skillListQuery.error) : null}
              skillOptions={skillOptions}
              onDirtyChange={setEditorDirty}
              onSubmit={(draft) => createMutation.mutate(draft)}
            />
          ) : null}
          {!showCreateEditor && detailQuery.isLoading && selection ? (
            <div className="panel-muted px-4 py-5 text-sm text-[var(--text-secondary)]">正在加载 Agent...</div>
          ) : null}
          {!showCreateEditor && detailQuery.error ? (
            <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
              {getErrorMessage(detailQuery.error)}
            </div>
          ) : null}
          {!showCreateEditor && selectedDetail ? (
            <AssistantAgentEditor
              key={`${selectedDetail.id}:${selectedDetail.updated_at ?? ""}`}
              detail={selectedDetail}
              isPending={isPending}
              mode="edit"
              skillErrorMessage={skillListQuery.error ? getErrorMessage(skillListQuery.error) : null}
              skillOptions={skillOptions}
              onDelete={() => deleteMutation.mutate(selectedDetail.id)}
              onDirtyChange={setEditorDirty}
              onSubmit={(draft) => updateMutation.mutate(draft)}
            />
          ) : null}
        </div>
      </div>
    </SectionCard>
  );
}

function attemptSelect(
  nextSelection: string,
  isDirty: boolean,
  setSelection: (value: string) => void,
) {
  if (isDirty) {
    showAppNotice({
      title: "Agents",
      content: "当前 Agent 还有未保存的改动，请先保存或还原。",
      tone: "warning",
    });
    return;
  }
  setSelection(nextSelection);
}
