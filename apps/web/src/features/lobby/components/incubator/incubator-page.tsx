"use client";

import Link from "next/link";
import { useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";

import { ChatModePanel } from "@/features/lobby/components/incubator/incubator-chat-panel";
import type { FeedbackState } from "@/features/lobby/components/incubator/incubator-feedback-support";
import { useIncubatorChatModel } from "@/features/lobby/components/incubator/incubator-page-model";
import {
  INCUBATOR_MODE_OPTIONS,
  type IncubatorMode,
} from "@/features/lobby/components/incubator/incubator-page-support";
import { TemplateModePanel } from "@/features/lobby/components/incubator/incubator-panels";
import { useIncubatorTemplateModel } from "@/features/lobby/components/incubator/incubator-template-model";

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
    <div className="incubator-root">
      {/* 顶部导航 — 极简到几乎隐形 */}
      <IncubatorTopBar mode={mode} onModeChange={handleModeChange} />

      {/* 反馈横幅 */}
      {feedback ? <FeedbackBanner feedback={feedback} /> : null}

      {/* 主内容区 */}
      <main className="incubator-stage">
        <section
          aria-labelledby="incubator-tab-chat"
          className="incubator-panel"
          hidden={mode !== "chat"}
          id="incubator-panel-chat"
          role="tabpanel"
        >
          <ChatModeContent setFeedback={setFeedback} />
        </section>
        {hasVisitedTemplateMode || mode === "template" ? (
          <section
            aria-labelledby="incubator-tab-template"
            className="incubator-panel"
            hidden={mode !== "template"}
            id="incubator-panel-template"
            role="tabpanel"
          >
            <TemplateModeContent
              onSwitchToChat={() => handleModeChange("chat")}
              setFeedback={setFeedback}
            />
          </section>
        ) : null}
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Top Bar — 极致压缩                                                */
/* ------------------------------------------------------------------ */

function IncubatorTopBar({
  mode,
  onModeChange,
}: Readonly<{
  mode: IncubatorMode;
  onModeChange: (mode: IncubatorMode) => void;
}>) {
  return (
    <header className="incubator-topbar">
      <div className="incubator-topbar-left">
        <Link className="incubator-back" href="/workspace/lobby">
          <svg aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path d="M15 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>书架</span>
        </Link>
      </div>

      <nav aria-label="创作启动模式" className="incubator-mode-switch" role="tablist">
        {INCUBATOR_MODE_OPTIONS.map((option) => (
          <button
            aria-controls={`incubator-panel-${option.id}`}
            aria-selected={mode === option.id}
            className={`incubator-mode-btn ${mode === option.id ? "active" : ""}`}
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
    </header>
  );
}

/* ------------------------------------------------------------------ */
/*  Feedback Banner                                                   */
/* ------------------------------------------------------------------ */

function FeedbackBanner({ feedback }: Readonly<{ feedback: FeedbackState }>) {
  const isDanger = feedback.tone === "danger";
  return (
    <div className={`incubator-feedback ${isDanger ? "danger" : "info"}`}>
      {feedback.message}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Content Wrappers                                                  */
/* ------------------------------------------------------------------ */

function ChatModeContent({
  setFeedback,
}: Readonly<{
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
}>) {
  const chatModel = useIncubatorChatModel(setFeedback);
  return <ChatModePanel model={chatModel} />;
}

function TemplateModeContent({
  onSwitchToChat,
  setFeedback,
}: Readonly<{
  onSwitchToChat: () => void;
  setFeedback: Dispatch<SetStateAction<FeedbackState | null>>;
}>) {
  const templateModel = useIncubatorTemplateModel(setFeedback);
  return <TemplateModePanel model={templateModel} onSwitchToChat={onSwitchToChat} />;
}
