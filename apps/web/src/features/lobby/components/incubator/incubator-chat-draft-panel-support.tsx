"use client";

import type { UseMutationResult } from "@tanstack/react-query";
import { Input } from "@arco-design/web-react";

import { StatusBadge } from "@/components/ui/status-badge";
import { getErrorMessage } from "@/lib/api/client";
import type { ProjectDetail, ProjectIncubatorConversationDraft } from "@/lib/api/types";

import { DraftGuidanceCard } from "@/features/lobby/components/incubator/incubator-chat-draft-guidance";
import type { IncubatorConversationDraftMutation } from "@/features/lobby/components/incubator/incubator-page-model-support";
import { buildDraftGuidance } from "@/features/lobby/components/incubator/incubator-chat-draft-support";
import { buildSettingIssueSummary, type SettingPreviewSection } from "@/features/lobby/components/incubator/incubator-page-support";

export type ActionCardProps = {
  canCreate: boolean;
  canCompleteWithAi: boolean;
  canSyncDraft: boolean;
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draft: ProjectIncubatorConversationDraft | null;
  draftMutation: IncubatorConversationDraftMutation;
  isDraftStale: boolean;
  isCompletingWithAi: boolean;
  onCompleteWithAi: () => Promise<void>;
  onProjectNameChange: (value: string) => void;
  onSyncDraft: () => Promise<void>;
  projectName: string;
};

/* ------------------------------------------------------------------ */
/*  Action Card — 顶部操作区                                          */
/* ------------------------------------------------------------------ */

export function ActionCard({
  canCreate,
  canCompleteWithAi,
  canSyncDraft,
  createMutation,
  draft,
  draftMutation,
  isDraftStale,
  isCompletingWithAi,
  onCompleteWithAi,
  onProjectNameChange,
  onSyncDraft,
  projectName,
}: Readonly<ActionCardProps>) {
  return (
    <section className="action-card">
      <div className="action-card-header">
        <span className="action-card-title">项目草稿</span>
        {draft ? <DraftStatusBadge draft={draft} /> : null}
      </div>

      <div className="project-name-field">
        <label htmlFor="incubator-project-name">项目名称</label>
        <Input
          allowClear
          autoComplete="off"
          id="incubator-project-name"
          name="projectName"
          placeholder="例如：林昭的玄幻故事…"
          value={projectName}
          onChange={(value) => onProjectNameChange(value)}
        />
      </div>

      <div className="action-buttons">
        <button
          className="ink-button-secondary"
          disabled={!canSyncDraft}
          type="button"
          onClick={() => void onSyncDraft()}
        >
          {draftMutation.isPending ? "整理中…" : draft ? "重新整理" : "整理草稿"}
        </button>
        <button
          className="ink-button"
          disabled={!canCreate}
          type="button"
          onClick={() => createMutation.mutate()}
        >
          {createMutation.isPending ? "创建中…" : "创建项目"}
        </button>
      </div>

      {draft ? (
        <DraftGuidanceCard
          canCompleteWithAi={canCompleteWithAi}
          draft={draft}
          isCompletingWithAi={isCompletingWithAi}
          onCompleteWithAi={() => void onCompleteWithAi()}
        />
      ) : null}

      <p className="action-notice">
        只缺建议项时也能继续创建项目，后面照样可以用 AI 生成大纲。
      </p>

      <NoticeList
        createMutation={createMutation}
        draftMutation={draftMutation}
        isDraftStale={isDraftStale}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Draft Body — 草稿内容区                                           */
/* ------------------------------------------------------------------ */

export function DraftBody({
  draft,
  hasUserMessage,
  sections,
}: {
  draft: ProjectIncubatorConversationDraft | null;
  hasUserMessage: boolean;
  sections: SettingPreviewSection[];
}) {
  if (!draft) {
    return (
      <div className="draft-empty">
        <div className="draft-empty-icon">
          <svg aria-hidden="true" fill="none" height="24" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" width="24">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <p className="draft-empty-title">暂无草稿</p>
        <p className="draft-empty-body">
          {buildPlaceholderMessage(hasUserMessage)}
        </p>
      </div>
    );
  }

  return (
    <div className="draft-body">
      {sections.length > 0 ? <SectionIndexCard sections={sections} /> : null}
      {draft.follow_up_questions.length > 0 ? <QuestionListCard questions={draft.follow_up_questions} /> : null}
      {sections.map((section, index) => (
        <SettingSectionCard index={index} key={section.title} section={section} />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Draft Status Badge                                                */
/* ------------------------------------------------------------------ */

function DraftStatusBadge({ draft }: { draft: ProjectIncubatorConversationDraft }) {
  const guidance = buildDraftGuidance(draft);
  const statusClass = draft.setting_completeness.issues.length === 0 ? "complete" :
    draft.setting_completeness.status === "warning" ? "partial" : "draft";
  return (
    <span className={`action-card-status ${statusClass}`}>
      {guidance.statusLabel}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Notice List                                                       */
/* ------------------------------------------------------------------ */

function NoticeList({
  createMutation,
  draftMutation,
  isDraftStale,
}: {
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draftMutation: IncubatorConversationDraftMutation;
  isDraftStale: boolean;
}) {
  return (
    <>
      {isDraftStale ? <NoticeCard message="聊天内容已更新，请先重新整理草稿。" tone="warning" /> : null}
      {draftMutation.error ? <NoticeCard message={resolveDraftErrorMessage(draftMutation.error)} tone="danger" /> : null}
      {createMutation.error ? <NoticeCard message={getErrorMessage(createMutation.error)} tone="danger" /> : null}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Question List Card                                                */
/* ------------------------------------------------------------------ */

function QuestionListCard({ questions }: { questions: string[] }) {
  return (
    <section className="question-list">
      <h3 className="question-list-title">待补充信息</h3>
      {questions.map((question) => (
        <div className="question-item" key={question}>
          {question}
        </div>
      ))}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Section Index Card                                                */
/* ------------------------------------------------------------------ */

function SectionIndexCard({ sections }: { sections: SettingPreviewSection[] }) {
  return (
    <section className="section-index">
      <h3 className="section-index-title">草稿目录</h3>
      <nav aria-label="项目方案目录" className="section-index-list">
        {sections.map((section) => (
          <a className="section-index-item" href={`#incubator-section-${section.title}`} key={section.title}>
            <span>{section.title}</span>
            <span>查看</span>
          </a>
        ))}
      </nav>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Setting Section Card                                              */
/* ------------------------------------------------------------------ */

function SettingSectionCard({ index, section }: { index: number; section: SettingPreviewSection }) {
  return (
    <section className="setting-section" id={`incubator-section-${index}`}>
      <header>
        <h3 className="setting-section-title">{section.title}</h3>
        <p className="setting-section-subtitle">当前已整理内容</p>
      </header>
      <dl>
        {section.items.map((item) => (
          <div className="setting-item" key={`${section.title}-${item.label}`}>
            <dt className="setting-item-label">{item.label}</dt>
            <dd className="setting-item-value">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Notice Card                                                       */
/* ------------------------------------------------------------------ */

function NoticeCard({ message, tone }: { message: string; tone: "danger" | "warning" }) {
  return (
    <div className={`notice-card ${tone}`}>
      {message}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function buildPlaceholderMessage(hasUserMessage: boolean) {
  if (hasUserMessage) {
    return "发送消息后，可整理当前聊天并生成草稿。";
  }
  return "先在左侧聊想法，再整理草稿。";
}

function resolveDraftErrorMessage(error: unknown) {
  const message = getErrorMessage(error);
  if (message === "LLM 输出不是合法 JSON") {
    return "这次整理失败，请调整表达后重试。";
  }
  return message;
}
