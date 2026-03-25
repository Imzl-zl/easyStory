"use client";

import type { Dispatch, SetStateAction } from "react";
import type { UseMutationResult } from "@tanstack/react-query";

import { IncubatorPreview } from "@/features/lobby/components/incubator-preview";
import {
  MAX_INCUBATOR_CONVERSATION_LENGTH,
  type ChatFormState,
} from "@/features/lobby/components/incubator-page-support";
import type { ProjectIncubatorConversationDraft } from "@/lib/api/types";

type ChatModePanelProps = {
  model: {
    form: ChatFormState;
    setForm: Dispatch<SetStateAction<ChatFormState>>;
    draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, void>;
    isDraftStale: boolean;
  };
};

export function ChatModePanel({ model }: ChatModePanelProps) {
  const canSubmit =
    model.form.conversationText.trim().length > 0 &&
    model.form.provider.trim().length > 0 &&
    !model.draftMutation.isPending;

  return (
    <div className="grid gap-6 xl:grid-cols-[0.84fr_1.16fr]">
      <section className="panel-muted space-y-4 p-5">
        <div className="space-y-1">
          <h3 className="font-serif text-lg font-semibold">自由描述</h3>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            适合先把故事意图整段说清楚，再交给后端抽取设定草稿。
          </p>
        </div>
        <label className="block">
          <span className="label-text">Provider</span>
          <input
            className="ink-input"
            value={model.form.provider}
            onChange={(event) => setChatFormField(model.setForm, "provider", event.target.value)}
          />
        </label>
        <label className="block">
          <span className="label-text">模型名（可选）</span>
          <input
            className="ink-input"
            value={model.form.modelName}
            onChange={(event) => setChatFormField(model.setForm, "modelName", event.target.value)}
          />
        </label>
        <label className="block">
          <span className="label-text">创作意图</span>
          <textarea
            className="ink-textarea"
            maxLength={MAX_INCUBATOR_CONVERSATION_LENGTH}
            rows={10}
            value={model.form.conversationText}
            onChange={(event) =>
              setChatFormField(model.setForm, "conversationText", event.target.value)
            }
          />
        </label>
        <p className="text-xs text-[var(--text-secondary)]">
          {model.form.conversationText.length} / {MAX_INCUBATOR_CONVERSATION_LENGTH}
        </p>
        <button
          className="ink-button"
          disabled={!canSubmit}
          onClick={() => model.draftMutation.mutate()}
          type="button"
        >
          {model.draftMutation.isPending ? "提取中..." : "提取设定草稿"}
        </button>
      </section>
      <IncubatorPreview
        title="自由描述草稿预览"
        description="后端会返回设定完整度与建议继续补充的问题，便于后续进 Studio。"
        emptyMessage="输入创作意图、Provider 后点击“提取设定草稿”。"
        completeness={model.draftMutation.data?.setting_completeness}
        followUpQuestions={model.draftMutation.data?.follow_up_questions}
        setting={model.draftMutation.data?.project_setting}
        staleMessage={
          model.isDraftStale
            ? "你已修改自由描述或模型参数，当前预览已过期，请重新提取设定草稿。"
            : null
        }
      />
    </div>
  );
}

function setChatFormField<K extends keyof ChatFormState>(
  setForm: Dispatch<SetStateAction<ChatFormState>>,
  field: K,
  value: ChatFormState[K],
) {
  setForm((current) => ({ ...current, [field]: value }));
}
