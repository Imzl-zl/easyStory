"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { SectionCard } from "@/components/ui/section-card";
import {
  getMyAssistantRules,
  getProjectAssistantRules,
  updateMyAssistantRules,
  updateProjectAssistantRules,
} from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";
import type { AssistantRuleProfile, AssistantRuleScope } from "@/lib/api/types";

import {
  buildAssistantRuleFieldId,
  buildAssistantRuleFormKey,
  isAssistantRuleDirty,
  toAssistantRuleDraft,
  type AssistantRuleDraft,
} from "@/features/settings/components/assistant/rules/assistant-rules-support";

type AssistantRulesEditorProps = {
  headerAction?: React.ReactNode;
  onDirtyChange?: (isDirty: boolean) => void;
  projectId?: string | null;
  scope: AssistantRuleScope;
  title: string;
};

export function AssistantRulesEditor({
  scope,
  projectId = null,
  title,
  headerAction,
  onDirtyChange,
}: AssistantRulesEditorProps) {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["assistant-rules", scope, projectId],
    queryFn: () => (scope === "user" ? getMyAssistantRules() : getProjectAssistantRules(projectId ?? "")),
  });
  const mutation = useMutation({
    mutationFn: (nextDraft: AssistantRuleDraft) =>
      scope === "user"
        ? updateMyAssistantRules(nextDraft)
        : updateProjectAssistantRules(projectId ?? "", nextDraft),
    onSuccess: async () => {
      const message = scope === "user" ? "个人规则已保存。" : "项目规则已保存。";
      setFeedback(message);
      showAppNotice({
        content: message,
        title: scope === "user" ? "个人长期规则" : "项目长期规则",
        tone: "success",
      });
      await queryClient.invalidateQueries({ queryKey: ["assistant-rules", scope, projectId] });
    },
    onError: (error) => {
      const message = getErrorMessage(error);
      setFeedback(message);
      showAppNotice({
        content: message,
        tone: "danger",
      });
    },
  });
  const formKey = useMemo(
    () => buildAssistantRuleFormKey(query.data),
    [query.data],
  );

  useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);

  return (
    <SectionCard action={headerAction} title={title}>
      <div className="space-y-4">
        {query.isLoading && !query.data ? (
          <div className="panel-muted px-4 py-5 text-sm text-text-secondary">正在加载规则...</div>
        ) : null}
        {query.error ? (
          <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
            {getErrorMessage(query.error)}
          </div>
        ) : null}
        {query.data ? (
          <AssistantRulesForm
            key={formKey}
            isPending={mutation.isPending}
            profile={query.data}
            scope={scope}
            onDirtyChange={onDirtyChange}
            onResetFeedback={() => setFeedback(null)}
            onSubmit={(nextDraft) => {
              setFeedback(null);
              mutation.mutate(nextDraft);
            }}
          />
        ) : null}
      </div>
    </SectionCard>
  );
}

function AssistantRulesForm({
  isPending,
  profile,
  scope,
  onDirtyChange,
  onResetFeedback,
  onSubmit,
}: {
  isPending: boolean;
  profile: AssistantRuleProfile;
  scope: AssistantRuleScope;
  onDirtyChange?: (isDirty: boolean) => void;
  onResetFeedback: () => void;
  onSubmit: (draft: AssistantRuleDraft) => void;
}) {
  const [draft, setDraft] = useState<AssistantRuleDraft>(() => toAssistantRuleDraft(profile));
  const isDirty = isAssistantRuleDirty(draft, profile);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  return (
    <form
      className="panel-muted space-y-10 p-10"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(draft);
      }}
    >
      <label className="flex items-start gap-3 rounded-2xl bg-glass-heavy px-4 py-3 cursor-pointer">
        <span className="flex items-start gap-3">
          <input
            checked={draft.enabled}
            className="mt-1 size-4 accent-accent-primary"
            onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
            type="checkbox"
          />
          <span className="space-y-1">
            <span className="block text-[13px] font-medium text-text-primary">
              在每次聊天时自动带上这份规则
            </span>
            <span className="block text-[12px] leading-5 text-text-secondary">
              会在基础对话要求上叠加这份长期规则。
            </span>
          </span>
        </span>
      </label>

      <div className="space-y-3">
        <label className="text-sm font-medium text-text-primary" htmlFor={buildAssistantRuleFieldId(scope)}>
          规则内容
        </label>
        <textarea
          className="ink-textarea min-h-48"
          id={buildAssistantRuleFieldId(scope)}
          onChange={(event) => setDraft({ ...draft, content: event.target.value })}
          placeholder="例如：\n1. 先给结论，再展开。\n2. 不要让我先填一堆表单。\n3. 如果信息不足，每次只追问一个关键问题。"
          value={draft.content}
        />
        <p className="text-[12px] leading-5 text-text-secondary">
          写入口吻偏好和固定要求。
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <button className="ink-button" disabled={isPending || !isDirty} type="submit">
          {isPending ? "保存中..." : "保存规则"}
        </button>
        <button
          className="ink-button-secondary"
          disabled={isPending || !isDirty}
          onClick={() => {
            onResetFeedback();
            setDraft(toAssistantRuleDraft(profile));
          }}
          type="button"
        >
          还原
        </button>
      </div>
    </form>
  );
}
