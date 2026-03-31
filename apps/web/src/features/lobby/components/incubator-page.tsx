"use client";

import Link from "next/link";
import { useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";

import { ChatModePanel } from "@/features/lobby/components/incubator-chat-panel";
import type { FeedbackState } from "@/features/lobby/components/incubator-feedback-support";
import { useIncubatorChatModel } from "@/features/lobby/components/incubator-page-model";
import {
  INCUBATOR_MODE_OPTIONS,
  type IncubatorMode,
} from "@/features/lobby/components/incubator-page-support";
import { TemplateModePanel } from "@/features/lobby/components/incubator-panels";
import { useIncubatorTemplateModel } from "@/features/lobby/components/incubator-template-model";

import styles from "./incubator-page.module.css";

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
    <div className={styles.page}>
      <IncubatorHero mode={mode} onModeChange={handleModeChange} />
      {feedback ? <FeedbackBanner feedback={feedback} /> : null}
      <StageShell mode={mode} stageCopy={stageCopy}>
        <section
          aria-labelledby="incubator-tab-chat"
          className={styles.stagePanel}
          hidden={mode !== "chat"}
          id="incubator-panel-chat"
          role="tabpanel"
        >
          <ChatModeContent setFeedback={setFeedback} />
        </section>
        {hasVisitedTemplateMode || mode === "template" ? (
          <section
            aria-labelledby="incubator-tab-template"
            className={styles.stagePanel}
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
    <section className={styles.hero}>
      <div className={styles.heroMain}>
        <Link className={styles.backLink} href="/workspace/lobby">
          返回书架
        </Link>
        <p className={styles.eyebrow}>项目起稿</p>
        <h1 className={styles.heroTitle}>先把想法变成可写的作品，再开始创作。</h1>
        <p className={styles.heroDescription}>
          easyStory 的起稿流程不再像填后台表单，而是像跟编辑一起把故事轮廓整理清楚。
        </p>
        <div className={styles.noteGrid}>
          {STARTER_NOTES.map((item) => (
            <article className={styles.noteCard} key={item}>
              <p>{item}</p>
            </article>
          ))}
        </div>
      </div>
      <aside className={styles.modeDock}>
        <div>
          <p className={styles.modeEyebrow}>启动方式</p>
          <p className={styles.modeLead}>选择更适合你此刻状态的起稿路径。</p>
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
    <nav aria-label="创作启动模式" className={styles.modeGrid} role="tablist">
      {INCUBATOR_MODE_OPTIONS.map((option) => (
        <button
          aria-controls={`incubator-panel-${option.id}`}
          aria-selected={mode === option.id}
          className={styles.modeCard}
          data-active={mode === option.id}
          id={`incubator-tab-${option.id}`}
          key={option.id}
          onClick={() => onModeChange(option.id)}
          role="tab"
          type="button"
        >
          <span className={styles.modeCardLabel}>{option.label}</span>
          <span className={styles.modeCardDetail}>{option.description}</span>
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
    <section className={styles.stage}>
      <div className={styles.stageHeader}>
        <div>
          <p className={styles.stageLabel}>{stageCopy.label}</p>
          <h2 className={styles.stageTitle}>{stageCopy.title}</h2>
          <p className={styles.stageDescription}>{stageCopy.description}</p>
        </div>
        <div className={styles.stageHint} data-mode={mode}>
          {mode === "chat" ? "先聊，再整理草稿" : "按模板补足缺失信息"}
        </div>
      </div>
      <div className={styles.stageBody}>{children}</div>
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
    <div className={styles.feedbackBanner} data-tone={feedback.tone}>
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
