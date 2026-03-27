"use client";

import Link from "next/link";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { PreparationStatusPanel } from "@/features/project/components/preparation-status-panel";
import { StudioStaleChapterPanel } from "@/features/studio/components/studio-stale-chapter-panel";
import {
  listStudioPanelOptions,
  resolveStudioChapterListState,
  type StudioChapterListState,
  type StudioPanelKey,
} from "@/features/studio/components/studio-page-support";
import type { ChapterSummary } from "@/lib/api/types";

type StudioPageHeaderProps = {
  activePanel: StudioPanelKey;
  isPending: boolean;
  onSelectPanel: (panel: StudioPanelKey) => void;
  projectId: string;
  projectName: string;
  projectStatus: string | null;
};

type StudioChapterNavigatorProps = {
  chapters: ChapterSummary[];
  errorMessage: string | null;
  isLoading: boolean;
  isPending: boolean;
  onSelectChapter: (chapterNumber: number) => void;
  onToggleVersionPanel: () => void;
  selectedChapterNumber: number | null;
  versionPanelOpen: boolean;
};

type StudioSidebarCardsProps = {
  onFocusStaleChapter: (chapterNumber: number) => void;
  projectId: string;
  staleChapters: ChapterSummary[];
};

export function StudioPageHeader({
  activePanel,
  isPending,
  onSelectPanel,
  projectId,
  projectName,
  projectStatus,
}: Readonly<StudioPageHeaderProps>) {
  return (
    <section className="panel-shell p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--accent-ink)]">工作室</p>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-serif text-3xl font-semibold text-[var(--text-primary)]">
              {projectName}
            </h1>
            {projectStatus ? <StatusBadge status={projectStatus} /> : null}
          </div>
          <p className="max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
            在这里维护项目设定、前置资产和章节正文，保持创作上下文集中而清晰。
          </p>
        </div>
        <Link
          className="ink-button-secondary"
          href={`/workspace/project/${projectId}/engine`}
        >
          前往执行器
        </Link>
      </div>
      <StudioPageTabs
        activePanel={activePanel}
        isPending={isPending}
        onSelectPanel={onSelectPanel}
      />
    </section>
  );
}

export function StudioChapterNavigator({
  chapters,
  errorMessage,
  isLoading,
  isPending,
  onSelectChapter,
  onToggleVersionPanel,
  selectedChapterNumber,
  versionPanelOpen,
}: Readonly<StudioChapterNavigatorProps>) {
  const listState = resolveStudioChapterListState({ chapters, errorMessage, isLoading });

  return (
    <section className="panel-shell space-y-4 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--accent-ink)]">章节导航</p>
          <h2 className="font-serif text-xl font-semibold text-[var(--text-primary)]">
            章节面板
          </h2>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            先选章节，再进入正文编辑和版本面板。
          </p>
        </div>
        <button
          className="ink-button-secondary"
          disabled={isPending || isLoading || chapters.length === 0}
          onClick={onToggleVersionPanel}
          type="button"
        >
          {versionPanelOpen ? "关闭版本面板" : "打开版本面板"}
        </button>
      </div>
      <StudioChapterNavigatorBody
        chapters={chapters}
        errorMessage={errorMessage}
        isPending={isPending}
        listState={listState}
        onSelectChapter={onSelectChapter}
        selectedChapterNumber={selectedChapterNumber}
      />
    </section>
  );
}

function StudioPageTabs({
  activePanel,
  isPending,
  onSelectPanel,
}: Pick<StudioPageHeaderProps, "activePanel" | "isPending" | "onSelectPanel">) {
  return (
    <nav
      aria-label="工作室标签"
      className="mt-6 flex flex-wrap gap-2 border-t border-[var(--line-soft)] pt-5"
    >
      {listStudioPanelOptions().map((item) => (
        <button
          key={item.key}
          className="ink-tab"
          data-active={activePanel === item.key}
          disabled={isPending}
          onClick={() => onSelectPanel(item.key)}
          type="button"
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}

function StudioChapterNavigatorBody({
  chapters,
  errorMessage,
  isPending,
  listState,
  onSelectChapter,
  selectedChapterNumber,
}: {
  chapters: ChapterSummary[];
  errorMessage: string | null;
  isPending: boolean;
  listState: StudioChapterListState;
  onSelectChapter: (chapterNumber: number) => void;
  selectedChapterNumber: number | null;
}) {
  return (
    <>
      {errorMessage ? (
        <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
          {errorMessage}
        </div>
      ) : null}

      {listState === "loading" ? (
        <p className="text-sm text-[var(--text-secondary)]">正在加载章节列表...</p>
      ) : null}

      {listState === "error" ? (
        <EmptyState
          title="章节列表加载失败"
          description="请稍后重试，或检查当前项目是否可正常读取章节内容。"
        />
      ) : null}

      <StudioChapterContent
        chapters={chapters}
        isPending={isPending}
        listState={listState}
        onSelectChapter={onSelectChapter}
        selectedChapterNumber={selectedChapterNumber}
      />
    </>
  );
}

function StudioChapterContent({
  chapters,
  isPending,
  listState,
  onSelectChapter,
  selectedChapterNumber,
}: {
  chapters: ChapterSummary[];
  isPending: boolean;
  listState: StudioChapterListState;
  onSelectChapter: (chapterNumber: number) => void;
  selectedChapterNumber: number | null;
}) {
  if (listState === "empty") {
    return (
      <EmptyState
        title="当前还没有章节"
        description="启动工作流后，章节内容会在这里生成。"
      />
    );
  }
  if (listState !== "ready") {
    return null;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {chapters.map((chapter) => (
        <button
          key={chapter.content_id}
          className="ink-tab flex items-center gap-2"
          data-active={chapter.chapter_number === selectedChapterNumber}
          disabled={isPending}
          onClick={() => onSelectChapter(chapter.chapter_number)}
          type="button"
        >
          <span>{chapter.chapter_number}. {chapter.title}</span>
          <StatusBadge status={chapter.status} />
        </button>
      ))}
    </div>
  );
}

export function StudioSidebarCards({
  onFocusStaleChapter,
  projectId,
  staleChapters,
}: Readonly<StudioSidebarCardsProps>) {
  return (
    <aside className="space-y-4">
      <PreparationStatusPanel projectId={projectId} />
      {staleChapters.length > 0 ? (
        <StudioStaleChapterPanel
          projectId={projectId}
          staleChapters={staleChapters}
          onFocusChapter={onFocusStaleChapter}
        />
      ) : null}
    </aside>
  );
}
