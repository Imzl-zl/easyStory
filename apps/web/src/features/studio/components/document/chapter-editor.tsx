"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { showAppNotice } from "@/components/ui/app-notice";
import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { ChapterImpactPanel } from "@/features/studio/components/document/chapter-impact-panel";
import { ChapterStaleNotice } from "@/features/studio/components/document/chapter-stale-notice";
import {
  buildChapterMutationFeedback,
  invalidateChapterQueries,
} from "@/features/studio/components/document/chapter-editor-support";
import { getErrorMessage } from "@/lib/api/client";
import {
  approveChapter,
  clearBestVersion,
  getChapter,
  listChapterVersions,
  markBestVersion,
  rollbackChapterVersion,
  saveChapter,
} from "@/lib/api/content";
import type { ChapterImpactSummary } from "@/lib/api/types";
type ChapterEditorProps = {
  projectId: string;
  chapterNumber: number | null;
  versionPanelOpen: boolean;
};

export function ChapterEditor({
  projectId,
  chapterNumber,
  versionPanelOpen,
}: ChapterEditorProps) {
  const hasChapter = chapterNumber !== null;
  const [lastImpactState, setLastImpactState] = useState<{
    chapterNumber: number | null;
    impact: ChapterImpactSummary | null;
    projectId: string;
  }>({
    projectId,
    chapterNumber,
    impact: null,
  });

  const detailQuery = useQuery({
    queryKey: ["chapter-detail", projectId, chapterNumber],
    queryFn: () => getChapter(projectId, chapterNumber ?? 1),
    enabled: hasChapter,
  });
  const versionsQuery = useQuery({
    queryKey: ["chapter-versions", projectId, chapterNumber],
    queryFn: () => listChapterVersions(projectId, chapterNumber ?? 1),
    enabled: hasChapter && versionPanelOpen,
  });
  const formKey = detailQuery.data
    ? `${detailQuery.data.content_id}:${detailQuery.data.current_version_number}`
    : `chapter-${chapterNumber}`;
  const lastImpact =
    lastImpactState.projectId === projectId && lastImpactState.chapterNumber === chapterNumber
      ? lastImpactState.impact
      : null;

  if (!hasChapter) {
    return (
      <EmptyState
        title="还没有章节可编辑"
        description="选择章节或启动工作流。"
      />
    );
  }

  return (
    <ChapterEditorForm
      key={formKey}
      chapterNumber={chapterNumber}
      detail={detailQuery.data}
      detailError={detailQuery.error}
      detailLoading={detailQuery.isLoading}
      lastImpact={lastImpact}
      onImpactChange={(impact) =>
        setLastImpactState({
          projectId,
          chapterNumber,
          impact,
        })
      }
      projectId={projectId}
      versionPanelOpen={versionPanelOpen}
      versions={versionsQuery.data}
    />
  );
}

function ChapterEditorForm({
  projectId,
  chapterNumber,
  detail,
  detailLoading,
  detailError,
  lastImpact,
  onImpactChange,
  versionPanelOpen,
  versions,
}: {
  projectId: string;
  chapterNumber: number;
  detail?: Awaited<ReturnType<typeof getChapter>>;
  detailLoading: boolean;
  detailError: unknown;
  lastImpact: ChapterImpactSummary | null;
  onImpactChange: (impact: ChapterImpactSummary | null) => void;
  versionPanelOpen: boolean;
  versions?: Awaited<ReturnType<typeof listChapterVersions>>;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(detail?.title ?? "");
  const [contentText, setContentText] = useState(detail?.content_text ?? "");
  const [changeSummary, setChangeSummary] = useState(detail?.change_summary ?? "");
  const noticeTitle = `第 ${chapterNumber} 章`;

  const saveMutation = useMutation({
    mutationFn: () =>
      saveChapter(projectId, chapterNumber, {
        title,
        content_text: contentText,
        change_summary: changeSummary || undefined,
      }),
    onSuccess: (result) => {
      const message = buildChapterMutationFeedback("save", result.impact);
      onImpactChange(result.impact);
      showAppNotice({
        content: message,
        title: noticeTitle,
        tone: "success",
      });
      invalidateChapterQueries(queryClient, projectId, chapterNumber);
    },
    onError: (error) => {
      onImpactChange(null);
      showAppNotice({
        content: getErrorMessage(error),
        title: noticeTitle,
        tone: "danger",
      });
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => approveChapter(projectId, chapterNumber),
    onSuccess: () => {
      showAppNotice({
        content: "章节已确认。",
        title: noticeTitle,
        tone: "success",
      });
      invalidateChapterQueries(queryClient, projectId, chapterNumber);
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: noticeTitle,
        tone: "danger",
      }),
  });

  const versionMutation = useMutation({
    mutationFn: async ({
      versionNumber,
      action,
      isBest,
    }: {
      versionNumber: number;
      action: "mark" | "clear" | "rollback";
      isBest: boolean;
    }) => {
      if (action === "rollback") {
        return rollbackChapterVersion(projectId, chapterNumber, versionNumber);
      }
      if (action === "mark") {
        return markBestVersion(projectId, chapterNumber, versionNumber);
      }
      return clearBestVersion(projectId, chapterNumber, versionNumber);
    },
    onSuccess: (result, variables) => {
      if (variables.action === "rollback" && "impact" in result) {
        const message = buildChapterMutationFeedback("rollback", result.impact);
        onImpactChange(result.impact);
        showAppNotice({
          content: message,
          title: noticeTitle,
          tone: "success",
        });
        invalidateChapterQueries(queryClient, projectId, chapterNumber);
        return;
      }
      showAppNotice({
        content: variables.action === "mark" ? "已标记为最佳版本。" : "已取消最佳版本。",
        title: noticeTitle,
        tone: "success",
      });
      invalidateChapterQueries(queryClient, projectId, chapterNumber);
    },
    onError: (error, variables) => {
      if (variables.action === "rollback") {
        onImpactChange(null);
      }
      showAppNotice({
        content: getErrorMessage(error),
        title: noticeTitle,
        tone: "danger",
      });
    },
  });

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <SectionCard
        title={`Chapter ${chapterNumber}`}
        action={
          <div className="flex flex-wrap gap-2">
            {detail ? <StatusBadge status={detail.status} /> : null}
            <button className="ink-button-secondary" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
              {saveMutation.isPending ? "保存中..." : "保存草稿"}
            </button>
            <button className="ink-button" disabled={approveMutation.isPending} onClick={() => approveMutation.mutate()}>
              {approveMutation.isPending ? "确认中..." : "确认"}
            </button>
          </div>
        }
      >
        {detailLoading ? <p className="text-sm text-text-secondary">正在加载章节...</p> : null}
        {detailError ? (
          <div className="rounded-2xl bg-accent-danger/10 px-4 py-3 text-sm text-accent-danger">
            {getErrorMessage(detailError)}
          </div>
        ) : null}

        <div className="space-y-4">
          <label className="block space-y-2">
            <span className="label-text">标题</span>
            <input className="ink-input" value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className="block space-y-2">
            <span className="label-text">变更说明</span>
            <input
              className="ink-input"
              value={changeSummary}
              onChange={(event) => setChangeSummary(event.target.value)}
            />
          </label>
          <label className="block space-y-2">
            <span className="label-text">正文</span>
            <textarea
              className="ink-textarea min-h-[420px]"
              value={contentText}
              onChange={(event) => setContentText(event.target.value)}
            />
          </label>
          {detail?.status === "stale" ? (
            <ChapterStaleNotice chapterNumber={chapterNumber} projectId={projectId} />
          ) : null}
          {lastImpact ? <ChapterImpactPanel impact={lastImpact} /> : null}
        </div>
      </SectionCard>

      {versionPanelOpen ? (
        <aside className="panel-shell fan-panel space-y-4 p-5">
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">版本面板</h3>
            <p className="text-sm leading-6 text-text-secondary">
              当前只保留版本列表、最佳版本标记与回滚入口。
            </p>
          </div>
          {versions === undefined ? <p className="text-sm text-text-secondary">正在加载版本...</p> : null}
          {versions?.map((version) => (
            <article key={version.version_number} className="panel-muted space-y-3 p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge status={version.is_current ? "active" : "archived"} label={`v${version.version_number}`} />
                  {version.is_best ? <StatusBadge status="approved" label="best" /> : null}
                </div>
                <p className="text-xs text-text-secondary">
                  {new Date(version.created_at).toLocaleString("zh-CN")}
                </p>
              </div>
              <p className="text-sm leading-6 text-text-secondary">
                {version.change_summary ?? "没有变更说明。"}
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  className="ink-button-secondary"
                  disabled={versionMutation.isPending}
                  onClick={() =>
                    versionMutation.mutate({
                      versionNumber: version.version_number,
                      action: "rollback",
                      isBest: version.is_best,
                    })
                  }
                >
                  回滚到此版本
                </button>
                <button
                  className="ink-button-secondary"
                  disabled={versionMutation.isPending}
                  onClick={() =>
                    versionMutation.mutate({
                      versionNumber: version.version_number,
                      action: version.is_best ? "clear" : "mark",
                      isBest: version.is_best,
                    })
                  }
                >
                  {version.is_best ? "取消最佳" : "标记最佳"}
                </button>
              </div>
            </article>
          ))}
        </aside>
      ) : null}
    </div>
  );
}
