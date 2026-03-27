"use client";

import { useState } from "react";
import type { Dispatch, SetStateAction } from "react";
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
  const [hasVisitedTemplateMode, setHasVisitedTemplateMode] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const handleModeChange = (nextMode: IncubatorMode) => {
    setMode(nextMode);
    setFeedback(null);
    if (nextMode === "template") {
      setHasVisitedTemplateMode(true);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeaderShell
        actions={<Link className="ink-button-secondary" href="/workspace/lobby">返回项目大厅</Link>}
        description="先把模糊想法聊开，再把已经确定的内容整理成项目草稿。聊顺了再创建项目，不用一上来就填完整设定。"
        eyebrow="创作启动台"
        footer={<ModeTabs mode={mode} onModeChange={handleModeChange} />}
        title="和 AI 一起想故事"
      />
      {feedback ? <FeedbackBanner feedback={feedback} /> : null}
      <section
        aria-labelledby="incubator-tab-chat"
        hidden={mode !== "chat"}
        id="incubator-panel-chat"
        role="tabpanel"
      >
        <ChatModeContent setFeedback={setFeedback} />
      </section>
      {hasVisitedTemplateMode || mode === "template" ? (
        <section
          aria-labelledby="incubator-tab-template"
          hidden={mode !== "template"}
          id="incubator-panel-template"
          role="tabpanel"
        >
          <TemplateModeContent onSwitchToChat={() => handleModeChange("chat")} setFeedback={setFeedback} />
        </section>
      ) : null}
    </div>
  );
}

function ChatModeContent({
  setFeedback,
}: {
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
}) {
  const chatModel = useIncubatorChatModel(setFeedback);

  return <ChatModePanel model={chatModel} />;
}

function TemplateModeContent({
  onSwitchToChat,
  setFeedback,
}: {
  onSwitchToChat: () => void;
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
}) {
  const templateModel = useIncubatorTemplateModel(setFeedback);

  return <TemplateModePanel model={templateModel} onSwitchToChat={onSwitchToChat} />;
}

function ModeTabs({
  mode,
  onModeChange,
}: {
  mode: IncubatorMode;
  onModeChange: (mode: IncubatorMode) => void;
}) {
  return (
    <nav aria-label="创作启动模式" className="flex flex-wrap gap-2" role="tablist">
      {INCUBATOR_MODE_OPTIONS.map((option) => (
        <button
          aria-controls={`incubator-panel-${option.id}`}
          aria-selected={mode === option.id}
          className="ink-tab"
          data-active={mode === option.id}
          id={`incubator-tab-${option.id}`}
          key={option.id}
          onClick={() => onModeChange(option.id)}
          role="tab"
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
