"use client";

import { useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import Link from "next/link";

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
    <div className="flex flex-col gap-1.5 lg:h-[calc(100vh-3rem)] lg:min-h-[calc(100vh-3rem)] lg:overflow-hidden">
      <IncubatorPageHeader mode={mode} onModeChange={handleModeChange} />
      {feedback ? <FeedbackBanner feedback={feedback} /> : null}
      <section
        aria-labelledby="incubator-tab-chat"
        className="min-h-0 flex-1"
        hidden={mode !== "chat"}
        id="incubator-panel-chat"
        role="tabpanel"
      >
        <ChatModeContent setFeedback={setFeedback} />
      </section>
      {hasVisitedTemplateMode || mode === "template" ? (
        <section
          aria-labelledby="incubator-tab-template"
          className="min-h-0 flex-1"
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

function IncubatorPageHeader({
  mode,
  onModeChange,
}: {
  mode: IncubatorMode;
  onModeChange: (mode: IncubatorMode) => void;
}) {
  const modeSummary = mode === "chat" ? "AI 聊天" : "模板创建";

  return (
    <section className="panel-shell px-3 py-2 md:px-4 xl:px-5">
      <div className="flex flex-col gap-1.5 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <Link className="ink-button-secondary h-8 px-3 text-[13px]" href="/workspace/lobby">
            返回项目大厅
          </Link>
          <div className="hidden h-4 w-px bg-[var(--line-soft)] xl:block" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <h1 className="text-[0.97rem] font-semibold text-[var(--text-primary)] md:text-[1.02rem]">
                创建项目
              </h1>
              <span className="rounded-full bg-[rgba(46,111,106,0.08)] px-2 py-0.5 text-[10.5px] font-medium text-[var(--accent-ink)]">
                {modeSummary}
              </span>
            </div>
            <p className="mt-0.5 text-[11px] leading-5 text-[var(--text-secondary)]">
              先聊想法，再整理成项目草稿。
            </p>
          </div>
        </div>
        <ModeTabs mode={mode} onModeChange={onModeChange} />
      </div>
    </section>
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
    <nav
      aria-label="创作启动模式"
      className="flex flex-wrap items-center gap-1 rounded-full bg-[rgba(248,243,235,0.88)] p-1"
      role="tablist"
    >
      {INCUBATOR_MODE_OPTIONS.map((option) => (
        <button
          aria-controls={`incubator-panel-${option.id}`}
          aria-selected={mode === option.id}
          className="ink-tab h-8 px-2.5 text-[12px]"
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
    <div className={`rounded-xl px-3 py-2 text-[12.5px] leading-5 ${className}`}>{feedback.message}</div>
  );
}
