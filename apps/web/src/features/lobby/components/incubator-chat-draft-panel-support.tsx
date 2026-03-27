"use client";

import type { UseMutationResult } from "@tanstack/react-query";

import { StatusBadge } from "@/components/ui/status-badge";
import { getErrorMessage } from "@/lib/api/client";
import type { ProjectDetail, ProjectIncubatorConversationDraft } from "@/lib/api/types";

import { buildSettingIssueSummary, type SettingPreviewSection } from "./incubator-page-support";

export type ActionCardProps = {
  canCreate: boolean;
  canSyncDraft: boolean;
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draft: ProjectIncubatorConversationDraft | undefined;
  draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, string>;
  isDraftStale: boolean;
  onProjectNameChange: (value: string) => void;
  onSyncDraft: () => Promise<void>;
  projectName: string;
};

export function ActionCard({
  canCreate,
  canSyncDraft,
  createMutation,
  draft,
  draftMutation,
  isDraftStale,
  onProjectNameChange,
  onSyncDraft,
  projectName,
}: ActionCardProps) {
  return (
    <section className="panel-shell space-y-4 p-5">
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
      <p className="text-xs leading-6 text-[var(--text-secondary)]">
        创建后仍可在工作室继续补设定、生成大纲和推进章节。
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
  draft: ProjectIncubatorConversationDraft | undefined;
  hasUserMessage: boolean;
  sections: SettingPreviewSection[];
}) {
  if (!draft) return <PlaceholderCard message={buildPlaceholderMessage(hasUserMessage)} />;
  return (
    <>
      {draft.follow_up_questions.length > 0 ? <QuestionListCard questions={draft.follow_up_questions} /> : null}
      {sections.length > 0 ? <SectionIndexCard sections={sections} /> : null}
      {sections.map((section, index) => <SettingSectionCard index={index} key={section.title} section={section} />)}
    </>
  );
}

function ActionCardHeader({ draft }: { draft: ProjectIncubatorConversationDraft | undefined }) {
  return (
    <>
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent-ink)]">项目草稿</p>
        <h2 className="font-serif text-xl font-semibold text-[var(--text-primary)]">项目草稿</h2>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          把聊天里已经明确的信息整理成设定草稿，确认后再创建项目。
        </p>
      </div>
      {draft ? <DraftStatusRow draft={draft} /> : null}
    </>
  );
}

function DraftStatusRow({ draft }: { draft: ProjectIncubatorConversationDraft }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge status={draft.setting_completeness.status} />
      <span className="text-sm text-[var(--text-secondary)]">
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
      <input
        autoComplete="off"
        className="ink-input"
        name="projectName"
        placeholder="例如：林昭的玄幻故事…"
        value={projectName}
        onChange={(event) => onProjectNameChange(event.target.value)}
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
  draft: ProjectIncubatorConversationDraft | undefined;
  draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, string>;
  onSyncDraft: () => Promise<void>;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <button className="ink-button-secondary" disabled={!canSyncDraft} onClick={() => void onSyncDraft()} type="button">
        {draftMutation.isPending ? "整理中…" : draft ? "重新整理草稿" : "整理成项目草稿"}
      </button>
      <button className="ink-button" disabled={!canCreate} onClick={() => createMutation.mutate()} type="button">
        {createMutation.isPending ? "创建中…" : "创建项目"}
      </button>
    </div>
  );
}

function NoticeList({
  createMutation,
  draftMutation,
  isDraftStale,
}: {
  createMutation: UseMutationResult<ProjectDetail, unknown, void>;
  draftMutation: UseMutationResult<ProjectIncubatorConversationDraft, unknown, string>;
  isDraftStale: boolean;
}) {
  return (
    <>
      {isDraftStale ? <NoticeCard message="聊天内容已经更新，先重新整理草稿再创建会更稳。" tone="warning" /> : null}
      {draftMutation.error ? <NoticeCard message={resolveDraftErrorMessage(draftMutation.error)} tone="danger" /> : null}
      {createMutation.error ? <NoticeCard message={getErrorMessage(createMutation.error)} tone="danger" /> : null}
    </>
  );
}

function QuestionListCard({ questions }: { questions: string[] }) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <h3 className="font-serif text-lg font-semibold text-[var(--text-primary)]">待补问题</h3>
      <ul className="space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
        {questions.map((question) => (
          <li className="rounded-2xl bg-[rgba(255,255,255,0.52)] px-4 py-3" key={question}>
            {question}
          </li>
        ))}
      </ul>
    </section>
  );
}

function SectionIndexCard({ sections }: { sections: SettingPreviewSection[] }) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <h3 className="font-serif text-lg font-semibold text-[var(--text-primary)]">草稿目录</h3>
      <nav aria-label="项目草稿目录" className="flex flex-wrap gap-2">
        {sections.map((section, index) => (
          <a className="ink-tab" href={`#incubator-section-${index}`} key={section.title}>
            {section.title}
          </a>
        ))}
      </nav>
    </section>
  );
}

function SettingSectionCard({ index, section }: { index: number; section: SettingPreviewSection }) {
  return (
    <section className="panel-shell space-y-4 p-5 scroll-mt-6" id={`incubator-section-${index}`}>
      <header className="space-y-1">
        <h3 className="font-serif text-lg font-semibold text-[var(--text-primary)]">{section.title}</h3>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">这里展示当前聊天里已经比较明确的设定内容。</p>
      </header>
      <dl className="grid gap-3">
        {section.items.map((item) => (
          <div className="panel-muted space-y-1 p-4" key={`${section.title}-${item.label}`}>
            <dt className="text-xs uppercase tracking-[0.18em] text-[var(--text-secondary)]">{item.label}</dt>
            <dd className="text-sm leading-6 text-[var(--text-primary)]">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function buildPlaceholderMessage(hasUserMessage: boolean) {
  return hasUserMessage
    ? "聊天已经有内容了，点击“整理成项目草稿”就能把信息收拢起来。"
    : "先和 AI 聊出方向，再把关键信息整理成项目草稿。";
}

function PlaceholderCard({ message }: { message: string }) {
  return (
    <section className="panel-muted space-y-3 p-5">
      <h3 className="font-serif text-lg font-semibold text-[var(--text-primary)]">等待草稿成形</h3>
      <p className="text-sm leading-6 text-[var(--text-secondary)]">{message}</p>
    </section>
  );
}

function NoticeCard({ message, tone }: { message: string; tone: "danger" | "warning" }) {
  const className = tone === "danger"
    ? "bg-[rgba(178,65,46,0.12)] text-[var(--accent-danger)]"
    : "bg-[rgba(183,121,31,0.14)] text-[var(--accent-warning)]";
  return <div className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{message}</div>;
}

function resolveDraftErrorMessage(error: unknown) {
  const message = getErrorMessage(error);
  if (message === "LLM 输出不是合法 JSON") {
    return "这次还没整理出可用草稿，AI 返回的内容不是可解析的设定格式。";
  }
  return message;
}
