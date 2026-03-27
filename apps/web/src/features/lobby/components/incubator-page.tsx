"use client";

import { useState } from "react";
import Link from "next/link";

import { PageHeaderShell } from "@/components/ui/page-header-shell";
import { ChatModePanel } from "@/features/lobby/components/incubator-chat-panel";
import { type FeedbackState } from "@/features/lobby/components/incubator-feedback-support";
import { useIncubatorChatModel } from "@/features/lobby/components/incubator-page-model";
import {
  INCUBATOR_MODE_OPTIONS,
  type IncubatorMode,
} from "@/features/lobby/components/incubator-page-support";
import { useIncubatorTemplateModel } from "@/features/lobby/components/incubator-template-model";
import { TemplateModePanel } from "@/features/lobby/components/incubator-panels";

export function IncubatorPage() {
  const [mode, setMode] = useState<IncubatorMode>("chat");
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const templateModel = useIncubatorTemplateModel(setFeedback);
  const chatModel = useIncubatorChatModel(setFeedback);

  return (
    <div className="space-y-6">
      <PageHeaderShell
        actions={<Link className="ink-button-secondary" href="/workspace/lobby">返回项目大厅</Link>}
        description="别先填表，先把模糊想法聊出来。聊天负责发散，右侧草稿负责收敛，确认后再创建项目。"
        eyebrow="创作启动台"
        footer={<ModeTabs mode={mode} onModeChange={(nextMode) => { setMode(nextMode); setFeedback(null); }} />}
        title="和 AI 一起想故事"
      />
      {feedback ? <FeedbackBanner feedback={feedback} /> : null}
      {mode === "chat" ? (
        <ChatModePanel model={chatModel} />
      ) : (
        <TemplateModePanel model={templateModel} onSwitchToChat={() => setMode("chat")} />
      )}
    </div>
  );
}

function ModeTabs({
  mode,
  onModeChange,
}: {
  mode: IncubatorMode;
  onModeChange: (mode: IncubatorMode) => void;
}) {
  return (
    <nav aria-label="创作启动模式" className="flex flex-wrap gap-2">
      {INCUBATOR_MODE_OPTIONS.map((option) => (
        <button
          className="ink-tab"
          data-active={mode === option.id}
          key={option.id}
          onClick={() => onModeChange(option.id)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </nav>
  );
}

function FeedbackBanner({ feedback }: { feedback: FeedbackState }) {
  const className =
    feedback.tone === "danger"
      ? "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]"
      : "bg-[rgba(58,124,165,0.1)] text-[var(--accent-info)]";

  return (
    <div className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{feedback.message}</div>
  );
}
