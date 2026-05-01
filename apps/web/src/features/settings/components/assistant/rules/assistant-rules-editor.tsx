"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
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
    <section
      className="rounded-lg"
      style={{
        background: "var(--bg-canvas)",
        border: "1px solid var(--line-soft)",
      }}
    >
      {/* Section Header */}
      <div className="px-4 pt-4 pb-3 flex items-center justify-between" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <div>
          <h2 className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
          </h2>
          <p className="mt-0.5 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
            {scope === "user" ? "适用于所有对话的默认长期规则" : "仅适用于当前项目的长期规则"}
          </p>
        </div>
        {headerAction}
      </div>

      {/* Content */}
      <div className="px-4 py-4">
        {query.isLoading && !query.data ? (
          <p className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>正在加载规则...</p>
        ) : null}
        {query.error ? (
          <div className="rounded-md px-3.5 py-2.5 text-[13px]" style={{ background: "var(--accent-danger-soft)", color: "var(--accent-danger)" }}>
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
    </section>
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
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(draft);
      }}
    >
      {/* Enable Toggle */}
      <label
        className="flex items-start gap-3 rounded-md px-3 py-2.5 cursor-pointer transition-colors"
        style={{ background: "var(--bg-canvas)", border: "1px solid var(--line-medium)" }}
      >
        <input
          checked={draft.enabled}
          className="mt-0.5 size-3.5 accent-[var(--accent-primary)]"
          onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
          type="checkbox"
        />
        <span className="space-y-0.5">
          <span className="block text-[12px] font-medium" style={{ color: "var(--text-primary)" }}>
            在每次聊天时自动带上这份规则
          </span>
          <span className="block text-[11px]" style={{ color: "var(--text-tertiary)" }}>
            会在基础对话要求上叠加这份长期规则
          </span>
        </span>
      </label>

      {/* Rule Content */}
      <div className="space-y-2">
        <label
          className="block text-[12px] font-medium"
          style={{ color: "var(--text-secondary)" }}
          htmlFor={buildAssistantRuleFieldId(scope)}
        >
          规则内容
        </label>
        <textarea
          className="w-full rounded-md px-3 py-2.5 text-[12px] resize-y transition-colors focus:outline-none"
          style={{
            background: "var(--bg-canvas)",
            color: "var(--text-primary)",
            border: "1px solid var(--line-medium)",
            minHeight: "120px",
          }}
          id={buildAssistantRuleFieldId(scope)}
          onChange={(event) => setDraft({ ...draft, content: event.target.value })}
          placeholder="例如：&#10;1. 先给结论，再展开。&#10;2. 不要让我先填一堆表单。&#10;3. 如果信息不足，每次只追问一个关键问题。"
          value={draft.content}
        />
        <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          写入口吻偏好和固定要求
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium transition-colors"
          disabled={isPending || !isDirty}
          style={{
            background: isDirty ? "var(--accent-primary)" : "var(--line-soft)",
            color: isDirty ? "var(--text-on-accent)" : "var(--text-tertiary)",
          }}
          type="submit"
        >
          {isPending ? "保存中..." : "保存规则"}
        </button>
        <button
          className="h-8 px-4 rounded-md text-[12px] font-medium"
          disabled={isPending || !isDirty}
          onClick={() => {
            onResetFeedback();
            setDraft(toAssistantRuleDraft(profile));
          }}
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)", border: "1px solid var(--line-medium)" }}
          type="button"
        >
          还原
        </button>
      </div>
    </form>
  );
}
