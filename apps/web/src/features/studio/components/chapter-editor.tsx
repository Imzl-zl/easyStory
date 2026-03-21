"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { EmptyState } from "@/components/ui/empty-state";
import { SectionCard } from "@/components/ui/section-card";
import { StatusBadge } from "@/components/ui/status-badge";
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

  if (!hasChapter) {
    return (
      <EmptyState
        title="还没有章节可编辑"
        description="先在左侧选择已有章节，或在 Engine 中启动工作流生成章节任务。"
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
  versionPanelOpen,
  versions,
}: {
  projectId: string;
  chapterNumber: number;
  detail?: Awaited<ReturnType<typeof getChapter>>;
  detailLoading: boolean;
  detailError: unknown;
  versionPanelOpen: boolean;
  versions?: Awaited<ReturnType<typeof listChapterVersions>>;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(detail?.title ?? "");
  const [contentText, setContentText] = useState(detail?.content_text ?? "");
  const [changeSummary, setChangeSummary] = useState(detail?.change_summary ?? "");
  const [feedback, setFeedback] = useState<string | null>(null);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["chapters", projectId] });
    queryClient.invalidateQueries({ queryKey: ["chapter-detail", projectId, chapterNumber] });
    queryClient.invalidateQueries({ queryKey: ["chapter-versions", projectId, chapterNumber] });
  };

  const saveMutation = useMutation({
    mutationFn: () =>
      saveChapter(projectId, chapterNumber, {
        title,
        content_text: contentText,
        change_summary: changeSummary || undefined,
      }),
    onSuccess: () => {
      setFeedback("章节草稿已保存。");
      refresh();
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  const approveMutation = useMutation({
    mutationFn: () => approveChapter(projectId, chapterNumber),
    onSuccess: () => {
      setFeedback("章节已确认。");
      refresh();
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
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
    onSuccess: () => {
      setFeedback("版本面板已更新。");
      refresh();
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <SectionCard
        title={`Chapter ${chapterNumber}`}
        description="章节正文默认以草稿和确认两种主动作推进，后续版本由右侧版本面板管理。"
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
        {detailLoading ? <p className="text-sm text-[var(--text-secondary)]">正在加载章节...</p> : null}
        {detailError ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
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
          {feedback ? (
            <div className="rounded-2xl bg-[rgba(58,124,165,0.1)] px-4 py-3 text-sm text-[var(--accent-info)]">
              {feedback}
            </div>
          ) : null}
        </div>
      </SectionCard>

      {versionPanelOpen ? (
        <aside className="panel-shell fan-panel space-y-4 p-5">
          <div className="space-y-1">
            <h3 className="font-serif text-lg font-semibold">Version Panel</h3>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">
              当前只保留版本列表、最佳版本标记与回滚入口。
            </p>
          </div>
          {versions === undefined ? <p className="text-sm text-[var(--text-secondary)]">正在加载版本...</p> : null}
          {versions?.map((version) => (
            <article key={version.version_number} className="panel-muted space-y-3 p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge status={version.is_current ? "active" : "archived"} label={`v${version.version_number}`} />
                  {version.is_best ? <StatusBadge status="approved" label="best" /> : null}
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  {new Date(version.created_at).toLocaleString("zh-CN")}
                </p>
              </div>
              <p className="text-sm leading-6 text-[var(--text-secondary)]">
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
