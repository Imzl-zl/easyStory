"use client";

import type { UseMutationResult } from "@tanstack/react-query";
import { Button, Input } from "@arco-design/web-react";

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
    <section className="panel-shell space-y-2.5 p-3">
      <ActionCardHeader draft={draft} />
      <ProjectNameField projectName={projectName} onProjectNameChange={onProjectNameChange} />
      <ActionButtons
        canCreate={canCreate}
        canSyncDraft={canSyncDraft}
        createMutation={createMutation}
        draft={draft}
        draftMutation={draftMutation}
        onSyncDraft={onSyncDraft}
      />
      {draft ? (
        <DraftGuidanceCard
          canCompleteWithAi={canCompleteWithAi}
          draft={draft}
          isCompletingWithAi={isCompletingWithAi}
          onCompleteWithAi={() => void onCompleteWithAi()}
        />
      ) : null}
      <p className="text-[11px] leading-5 text-[var(--text-secondary)]">
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
    return <PlaceholderCard message={buildPlaceholderMessage(hasUserMessage)} />;
  }
  return (
    <div className="space-y-2.5">
      {sections.length > 0 ? <SectionIndexCard sections={sections} /> : null}
      {draft.follow_up_questions.length > 0 ? <QuestionListCard questions={draft.follow_up_questions} /> : null}
      {sections.map((section, index) => (
        <SettingSectionCard index={index} key={section.title} section={section} />
      ))}
    </div>
  );
}

function ActionCardHeader({ draft }: { draft: ProjectIncubatorConversationDraft | null }) {
  return (
    <div className="space-y-1.5">
      <div className="space-y-1">
        <p className="text-[10px] tracking-[0.16em] text-[var(--accent-ink)]">项目草稿</p>
        <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">草稿预览</h2>
        <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
          整理结果会显示在这里。
        </p>
      </div>
      {draft ? <DraftStatusRow draft={draft} /> : null}
    </div>
  );
}

function DraftStatusRow({ draft }: { draft: ProjectIncubatorConversationDraft }) {
  const guidance = buildDraftGuidance(draft);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge label={guidance.statusLabel} status={draft.setting_completeness.status} />
      <span className="text-xs leading-5 text-[var(--text-secondary)]">
        {buildSettingIssueSummary(draft.setting_completeness)}
      </span>
    </div>
  );
}

function ProjectNameField({
  onProjectNameChange,
  projectName,
}: {
  onProjectNameChange: (value: string) => void;
  projectName: string;
}) {
  return (
    <label className="block">
      <span className="label-text">项目名称</span>
      <Input
        allowClear
        autoComplete="off"
        className="w-full"
        name="projectName"
        placeholder="例如：林昭的玄幻故事…"
        size="default"
        value={projectName}
        onChange={(value) => onProjectNameChange(value)}
      />
    </label>
  );
}

function ActionButtons({
  canCreate,
  canSyncDraft,
  createMutation,
  draft,
  draftMutation,
  onSyncDraft,
}: {
  canCreate: boolean;
  canSyncDraft: boolean;
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draft: ProjectIncubatorConversationDraft | null;
  draftMutation: IncubatorConversationDraftMutation;
  onSyncDraft: () => Promise<void>;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <Button
        disabled={!canSyncDraft}
        long
        shape="round"
        size="default"
        type="secondary"
        onClick={() => void onSyncDraft()}
      >
        {draftMutation.isPending ? "整理中…" : draft ? "重新整理草稿" : "整理草稿"}
      </Button>
      <Button
        disabled={!canCreate}
        long
        shape="round"
        size="default"
        type="primary"
        onClick={() => createMutation.mutate()}
      >
        {createMutation.isPending ? "创建中…" : "创建项目"}
      </Button>
    </div>
  );
}

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

function QuestionListCard({ questions }: { questions: string[] }) {
  return (
    <section className="panel-muted space-y-2 p-3">
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">待补充信息</h3>
      <ul className="space-y-2 text-[13px] leading-5 text-[var(--text-secondary)]">
        {questions.map((question) => (
          <li className="rounded-xl bg-[rgba(255,255,255,0.72)] px-3 py-1.5" key={question}>
            {question}
          </li>
        ))}
      </ul>
    </section>
  );
}

function SectionIndexCard({ sections }: { sections: SettingPreviewSection[] }) {
  return (
    <section className="panel-muted space-y-2 p-3">
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">草稿目录</h3>
      <nav aria-label="项目方案目录" className="grid gap-1.5">
        {sections.map((section, index) => (
          <a
            className="flex items-center justify-between rounded-xl bg-[rgba(255,255,255,0.72)] px-3 py-1.5 text-[12.5px] text-[var(--text-primary)] transition hover:bg-[rgba(255,255,255,0.96)]"
            href={`#incubator-section-${index}`}
            key={section.title}
          >
            <span className="min-w-0 truncate">{section.title}</span>
            <span className="text-xs text-[var(--text-secondary)]">查看</span>
          </a>
        ))}
      </nav>
    </section>
  );
}

function SettingSectionCard({ index, section }: { index: number; section: SettingPreviewSection }) {
  return (
    <section className="panel-shell space-y-2 p-3 scroll-mt-4" id={`incubator-section-${index}`}>
      <header className="space-y-1">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">{section.title}</h3>
        <p className="text-[12px] leading-5 text-[var(--text-secondary)]">
          当前已整理内容
        </p>
      </header>
      <dl className="grid gap-2">
        {section.items.map((item) => (
          <div className="panel-muted space-y-1 p-2.5" key={`${section.title}-${item.label}`}>
            <dt className="text-[11px] tracking-[0.12em] text-[var(--text-secondary)]">{item.label}</dt>
            <dd className="break-words text-[13px] leading-5 text-[var(--text-primary)]">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function PlaceholderCard({ message }: { message: string }) {
  return (
    <section className="panel-muted space-y-2 p-3">
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">暂无草稿</h3>
      <p className="text-[13px] leading-5 text-[var(--text-secondary)]">{message}</p>
    </section>
  );
}

function NoticeCard({ message, tone }: { message: string; tone: "danger" | "warning" }) {
  const className = tone === "danger"
    ? "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]"
    : "bg-[rgba(183,121,31,0.14)] text-[var(--accent-warning)]";
  return <div className={`rounded-[14px] px-3 py-2 text-[12.5px] leading-5 ${className}`}>{message}</div>;
}

function buildPlaceholderMessage(hasUserMessage: boolean) {
  if (hasUserMessage) {
    return "发送消息后，可整理当前聊天并生成草稿。";
  }
  return "先在右侧聊想法，再整理草稿。";
}

function resolveDraftErrorMessage(error: unknown) {
  const message = getErrorMessage(error);
  if (message === "LLM 输出不是合法 JSON") {
    return "这次整理失败，请调整表达后重试。";
  }
  return message;
}
