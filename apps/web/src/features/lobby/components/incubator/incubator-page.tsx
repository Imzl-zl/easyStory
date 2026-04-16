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
    <div className="flex h-full min-h-0 flex-col gap-2.5 overflow-y-auto lg:overflow-hidden">
      <IncubatorHero mode={mode} onModeChange={handleModeChange} />
      {feedback ? <FeedbackBanner feedback={feedback} /> : null}
      <StageShell>
        <section
          aria-labelledby="incubator-tab-chat"
          className="flex-1 min-w-0 min-h-0"
          hidden={mode !== "chat"}
          id="incubator-panel-chat"
          role="tabpanel"
        >
          <ChatModeContent setFeedback={setFeedback} />
        </section>
        {hasVisitedTemplateMode || mode === "template" ? (
          <section
            aria-labelledby="incubator-tab-template"
            className="flex-1 min-w-0 min-h-0"
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
      </StageShell>
    </div>
  );
}

function IncubatorHero({
  mode,
  onModeChange,
}: Readonly<{
  mode: IncubatorMode;
  onModeChange: (mode: IncubatorMode) => void;
}>) {
  return (
    <section className="hero-card flex flex-col gap-3 px-4 py-3 md:px-5 md:py-3.5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link className="inline-flex w-fit items-center gap-2 text-accent-primary text-[12px] font-semibold" href="/workspace/lobby">
              返回书架
            </Link>
            <span className="inline-flex items-center rounded-pill bg-accent-soft px-2.5 py-1 text-[10.5px] font-semibold tracking-[0.08em] text-accent-primary">
              项目起稿
            </span>
          </div>
          <h1 className="mt-2 max-w-[720px] font-serif text-[clamp(1.45rem,2vw,2rem)] leading-[1.08]">
            先把故事方向聊清，再开始写。
          </h1>
          <p className="mt-1 max-w-[780px] text-[12px] leading-5 text-text-secondary">
            {mode === "chat"
              ? "AI 会跟着你的描述整理项目草稿，先把题材、角色和冲突说出来。"
              : "适合你已经有方向，只想顺着模板把关键设定一次补齐。"}
          </p>
        </div>
        <ModeSwitch mode={mode} onModeChange={onModeChange} />
      </div>
      <div className="flex flex-wrap items-center gap-2.5 text-[11px] leading-5 text-text-secondary">
        <span className={`inline-flex items-center rounded-pill px-2.5 py-1 font-medium ${mode === "chat" ? "bg-accent-soft text-accent-primary" : "bg-muted text-accent-secondary"}`}>
          {mode === "chat" ? "当前模式：AI 聊天" : "当前模式：模板创建"}
        </span>
        <p className="min-w-0 flex-1">
          聊清方向后直接生成草稿。
        </p>
      </div>
    </section>
  );
}

function ModeSwitch({
  mode,
  onModeChange,
}: Readonly<{
  mode: IncubatorMode;
  onModeChange: (mode: IncubatorMode) => void;
}>) {
  return (
    <nav
      aria-label="创作启动模式"
      className="inline-flex max-w-full flex-wrap items-center gap-1 rounded-2xl bg-muted shadow-sm p-1"
      role="tablist"
    >
      {INCUBATOR_MODE_OPTIONS.map((option) => (
        <button
          aria-controls={`incubator-panel-${option.id}`}
          aria-selected={mode === option.id}
          className={`inline-flex min-w-[124px] items-center justify-center rounded-2xl px-3 py-2 text-[12px] font-medium transition-all duration-fast ${mode === option.id ? "bg-surface text-text-primary shadow-sm" : "text-text-secondary hover:bg-surface-hover"}`}
          id={`incubator-tab-${option.id}`}
          key={option.id}
          onClick={() => onModeChange(option.id)}
          role="tab"
          type="button"
        >
          <span>{option.label}</span>
        </button>
      ))}
    </nav>
  );
}

function StageShell({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <section className="hero-card flex min-h-0 flex-1 overflow-hidden">
      <div className="flex flex-1 min-h-0 overflow-hidden bg-glass backdrop-blur-sm p-2.5 md:p-3.5">
        {children}
      </div>
    </section>
  );
}

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

function FeedbackBanner({ feedback }: Readonly<{ feedback: FeedbackState }>) {
  return (
    <div className={`rounded-2xl px-4 py-2.5 text-[12.5px] leading-relaxed ${feedback.tone === "danger" ? "bg-accent-danger/10 text-accent-danger" : "bg-accent-primary/10 text-accent-primary"}`}>
      {feedback.message}
    </div>
  );
}
