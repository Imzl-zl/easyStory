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

const STARTER_NOTES = [
  "先用对话把题材、角色和冲突说清。",
  "再把草稿整理成真正可写的项目设定。",
  "所有配置都服务于这部作品，而不是独立后台流程。",
] as const;

type IncubatorStageCopy = {
  label: string;
  title: string;
  description: string;
};

export function IncubatorPage() {
  const [mode, setMode] = useState<IncubatorMode>("chat");
  const [hasVisitedTemplateMode, setHasVisitedTemplateMode] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const stageCopy = buildStageCopy(mode);

  const handleModeChange = (nextMode: IncubatorMode) => {
    setMode(nextMode);
    setFeedback(null);
    if (nextMode === "template") {
      setHasVisitedTemplateMode(true);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <IncubatorHero mode={mode} onModeChange={handleModeChange} />
      {feedback ? <FeedbackBanner feedback={feedback} /> : null}
      <StageShell mode={mode} stageCopy={stageCopy}>
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
    <section className="hero-card grid gap-5.5 p-6 [grid-template-columns:minmax(0,1.2fr)_minmax(280px,360px)]">
      <div className="grid gap-4">
        <Link className="inline-flex w-fit items-center gap-2 text-[var(--accent-primary)] text-[13px] font-semibold" href="/workspace/lobby">
          返回书架
        </Link>
        <p className="label-overline">项目起稿</p>
        <h1 className="max-w-[820px] font-serif text-[clamp(2rem,4vw,3.8rem)] leading-tight">先把想法变成可写的作品，再开始创作。</h1>
        <p className="text-[var(--text-secondary)] text-sm leading-relaxed">
          easyStory 的起稿流程不再像填后台表单，而是像跟编辑一起把故事轮廓整理清楚。
        </p>
        <div className="grid gap-3 [grid-template-columns:repeat(3,minmax(0,1fr))]">
          {STARTER_NOTES.map((item) => (
            <article className="min-h-[108px] p-4.5 rounded-5 bg-gradient-to-b from-[rgba(247,241,231,0.92)] to-[rgba(251,248,242,0.82)]" key={item}>
              <p className="text-[var(--text-primary)] text-sm leading-relaxed">{item}</p>
            </article>
          ))}
        </div>
      </div>
      <aside className="grid content-start gap-4 p-5 rounded-[22px] bg-[rgba(244,239,231,0.86)]">
        <div>
          <p className="label-overline">启动方式</p>
          <p className="text-[var(--text-secondary)] text-sm leading-relaxed">选择更适合你此刻状态的起稿路径。</p>
        </div>
        <ModeCards mode={mode} onModeChange={onModeChange} />
      </aside>
    </section>
  );
}

function ModeCards({
  mode,
  onModeChange,
}: Readonly<{
  mode: IncubatorMode;
  onModeChange: (mode: IncubatorMode) => void;
}>) {
  return (
    <nav aria-label="创作启动模式" className="grid gap-3" role="tablist">
      {INCUBATOR_MODE_OPTIONS.map((option) => (
        <button
          aria-controls={`incubator-panel-${option.id}`}
          aria-selected={mode === option.id}
          className={`grid gap-2 p-4 border border-[rgba(61,61,61,0.08)] rounded-[18px] bg-[rgba(255,255,255,0.72)] text-left transition-all ${mode === option.id ? "border-[rgba(90,122,107,0.36)] bg-[rgba(255,255,255,0.96)] -translate-y-px" : ""}`}
          id={`incubator-tab-${option.id}`}
          key={option.id}
          onClick={() => onModeChange(option.id)}
          role="tab"
          type="button"
        >
          <span className="text-[15px] font-semibold">{option.label}</span>
          <span className="text-[var(--text-secondary)] text-[13px] leading-relaxed">{option.description}</span>
        </button>
      ))}
    </nav>
  );
}

function StageShell({
  children,
  mode,
  stageCopy,
}: Readonly<{
  children: ReactNode;
  mode: IncubatorMode;
  stageCopy: IncubatorStageCopy;
}>) {
  return (
    <section className="hero-card flex flex-col min-h-[calc(100vh-240px)]">
      <div className="flex justify-between gap-5 px-6 py-5.5 border-b border-[rgba(61,61,61,0.08)] bg-gradient-to-b from-[rgba(250,246,237,0.92)] to-[rgba(255,255,255,0.9)]">
        <div>
          <p className="label-overline">{stageCopy.label}</p>
          <h2 className="mt-2.5 font-serif text-7 font-semibold leading-tight">{stageCopy.title}</h2>
          <p className="text-[var(--text-secondary)] text-sm leading-relaxed">{stageCopy.description}</p>
        </div>
        <div className={`inline-flex items-center h-fit min-h-9 px-4 rounded-full text-xs font-semibold ${mode === "chat" ? "bg-[rgba(90,122,107,0.09)] text-[var(--accent-primary)]" : "bg-[rgba(139,115,85,0.1)] text-[var(--accent-secondary)]"}`}>
          {mode === "chat" ? "先聊，再整理草稿" : "按模板补足缺失信息"}
        </div>
      </div>
      <div className="flex flex-1 min-h-0 p-4 bg-gradient-to-b from-[rgba(255,255,255,0.9)] to-[rgba(248,243,235,0.86)]">{children}</div>
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
    <div className={`px-4 py-3.5 rounded-[18px] text-[13px] leading-relaxed ${feedback.tone === "danger" ? "bg-[rgba(196,90,90,0.12)] text-[var(--accent-danger)]" : "bg-[rgba(90,154,170,0.14)] text-[var(--accent-ink)]"}`}>
      {feedback.message}
    </div>
  );
}

function buildStageCopy(mode: IncubatorMode): IncubatorStageCopy {
  if (mode === "chat") {
    return {
      description: "用自然语言把题材、角色和冲突逐步说清，系统会同步整理成项目草稿。",
      label: "对话起稿",
      title: "像跟编辑聊故事一样，把项目先说出来。",
    };
  }

  return {
    description: "适合你已经知道题材方向，只需要顺着模板把关键空位填完整的场景。",
    label: "模板起稿",
    title: "用模板把必要信息一次补齐。",
  };
}
