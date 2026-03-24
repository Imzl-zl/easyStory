"use client";

import { useMemo, useTransition } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/ui/empty-state";
import { StatusBadge } from "@/components/ui/status-badge";
import { ChapterEditor } from "@/features/studio/components/chapter-editor";
import { PreparationStatusPanel } from "@/features/studio/components/preparation-status-panel";
import { ProjectSettingEditor } from "@/features/studio/components/project-setting-editor";
import { StoryAssetEditor } from "@/features/studio/components/story-asset-editor";
import { StudioStaleChapterPanel } from "@/features/studio/components/studio-stale-chapter-panel";
import {
  listStaleChapters,
  resolveSelectedChapterNumber,
} from "@/features/studio/components/studio-page-support";
import { getErrorMessage } from "@/lib/api/client";
import { listChapters } from "@/lib/api/content";
import { checkProjectSetting, getProject } from "@/lib/api/projects";

const PANEL_OPTIONS = [
  { key: "setting", label: "设定" },
  { key: "outline", label: "大纲" },
  { key: "opening-plan", label: "开篇设计" },
  { key: "chapter", label: "章节" },
] as const;

type StudioPageProps = {
  projectId: string;
};

export function StudioPage({ projectId }: StudioPageProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const panel = searchParams.get("panel") ?? "setting";
  const versionPanelOpen = searchParams.get("versionPanel") === "1";

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const completenessQuery = useQuery({
    queryKey: ["setting-check", projectId],
    queryFn: () => checkProjectSetting(projectId),
  });

  const chaptersQuery = useQuery({
    queryKey: ["chapters", projectId],
    queryFn: () => listChapters(projectId),
  });
  const staleChapters = useMemo(() => listStaleChapters(chaptersQuery.data), [chaptersQuery.data]);

  const selectedChapterNumber = useMemo(() => {
    return resolveSelectedChapterNumber(chaptersQuery.data, searchParams.get("chapter"));
  }, [chaptersQuery.data, searchParams]);

  const updateParams = (patches: Record<string, string | null>) => {
    startTransition(() => {
      const next = new URLSearchParams(searchParams.toString());
      Object.entries(patches).forEach(([key, value]) => {
        if (value === null) {
          next.delete(key);
          return;
        }
        next.set(key, value);
      });
      router.replace(`${pathname}?${next.toString()}`);
    });
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[260px_1fr]">
      <aside className="panel-shell space-y-6 p-5">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.24em] text-[var(--accent-ink)]">Studio</p>
          <h1 className="font-serif text-2xl font-semibold">
            {projectQuery.data?.name ?? "正在加载项目..."}
          </h1>
          {projectQuery.data ? <StatusBadge status={projectQuery.data.status} /> : null}
        </div>

        <div className="space-y-2">
          {PANEL_OPTIONS.map((item) => (
            <button
              key={item.key}
              className="ink-tab w-full justify-between"
              data-active={panel === item.key}
              disabled={isPending}
              onClick={() => updateParams({ panel: item.key })}
            >
              <span>{item.label}</span>
              <span className="text-xs uppercase tracking-[0.16em]">Panel</span>
            </button>
          ))}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">章节导航</h2>
            <button
              className="ink-button-secondary"
              disabled={isPending}
              onClick={() =>
                updateParams({ panel: "chapter", versionPanel: versionPanelOpen ? null : "1" })
              }
            >
              {versionPanelOpen ? "关闭版本" : "打开版本"}
            </button>
          </div>
          <div className="space-y-2">
            {chaptersQuery.data?.map((chapter) => (
              <button
                key={chapter.content_id}
                className="ink-tab w-full justify-between"
                data-active={chapter.chapter_number === selectedChapterNumber}
                onClick={() =>
                  updateParams({
                    panel: "chapter",
                    chapter: String(chapter.chapter_number),
                  })
                }
              >
                <span>{chapter.chapter_number}. {chapter.title}</span>
                <StatusBadge status={chapter.status} />
              </button>
            ))}
          </div>
          {staleChapters.length > 0 ? (
            <StudioStaleChapterPanel
              projectId={projectId}
              staleChapters={staleChapters}
              onFocusChapter={(chapterNumber) =>
                updateParams({
                  panel: "chapter",
                  chapter: String(chapterNumber),
                })
              }
            />
          ) : null}
        </div>

        <PreparationStatusPanel projectId={projectId} />

        <Link className="ink-button-secondary w-full justify-center" href={`/workspace/project/${projectId}/engine`}>
          前往 Engine
        </Link>
      </aside>

      <div className="space-y-4">
        {projectQuery.isLoading ? <p className="text-sm text-[var(--text-secondary)]">正在加载项目...</p> : null}
        {projectQuery.error ? (
          <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">
            {getErrorMessage(projectQuery.error)}
          </div>
        ) : null}

        {panel === "setting" ? (
          <ProjectSettingEditor
            completeness={completenessQuery.data}
            initialSetting={projectQuery.data?.project_setting ?? null}
            projectId={projectId}
          />
        ) : null}

        {panel === "outline" ? <StoryAssetEditor assetType="outline" projectId={projectId} /> : null}

        {panel === "opening-plan" ? (
          <StoryAssetEditor assetType="opening_plan" projectId={projectId} />
        ) : null}

        {panel === "chapter" ? (
          <ChapterEditor
            chapterNumber={selectedChapterNumber}
            projectId={projectId}
            versionPanelOpen={versionPanelOpen}
          />
        ) : null}

        {panel === "chapter" && chaptersQuery.data?.length === 0 ? (
          <EmptyState
            title="当前还没有章节"
            description="章节内容来自当前工作流生成。先进入 Engine 启动工作流，再回到 Studio 编辑与确认。"
          />
        ) : null}
      </div>
    </div>
  );
}
