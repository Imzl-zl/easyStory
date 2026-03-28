"use client";

import { useMemo, useTransition } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { ChapterEditor } from "@/features/studio/components/chapter-editor";
import { ProjectSettingEditor } from "@/features/studio/components/project-setting-editor";
import { StoryAssetEditor } from "@/features/studio/components/story-asset-editor";
import {
  buildStudioPathWithParams,
  listStaleChapters,
  resolveStudioChapterListState,
  resolveStudioPanel,
  resolveSelectedChapterNumber,
} from "@/features/studio/components/studio-page-support";
import {
  StudioChapterNavigator,
  StudioPageHeader,
  StudioSidebarCards,
} from "@/features/studio/components/studio-page-sections";
import { getErrorMessage } from "@/lib/api/client";
import { listChapters } from "@/lib/api/content";
import { checkProjectSetting, getProject } from "@/lib/api/projects";

type StudioPageProps = {
  projectId: string;
};

export function StudioPage({ projectId }: StudioPageProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const currentSearch = searchParams.toString();
  const panel = resolveStudioPanel(searchParams.get("panel"));
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
  const chapterErrorMessage = chaptersQuery.error ? getErrorMessage(chaptersQuery.error) : null;
  const chapterListState = resolveStudioChapterListState({
    chapters: chaptersQuery.data,
    errorMessage: chapterErrorMessage,
    isLoading: chaptersQuery.isLoading,
  });
  const staleChapters = useMemo(() => listStaleChapters(chaptersQuery.data), [chaptersQuery.data]);

  const selectedChapterNumber = useMemo(() => {
    return resolveSelectedChapterNumber(chaptersQuery.data, searchParams.get("chapter"));
  }, [chaptersQuery.data, searchParams]);

  const updateParams = (patches: Record<string, string | null>) => {
    startTransition(() => {
      router.replace(buildStudioPathWithParams(pathname, currentSearch, patches));
    });
  };

  return (
    <div className="space-y-6">
      <StudioPageHeader
        activePanel={panel}
        isPending={isPending}
        onSelectPanel={(nextPanel) =>
          updateParams({
            panel: nextPanel === "setting" ? null : nextPanel,
          })
        }
        projectId={projectId}
        projectName={projectQuery.data?.name ?? "正在加载项目…"}
        projectStatus={projectQuery.data?.status ?? null}
      />

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          {projectQuery.isLoading ? (
            <p aria-live="polite" className="text-sm text-[var(--text-secondary)]" role="status">
              正在加载项目…
            </p>
          ) : null}
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
            <div className="space-y-4">
              <StudioChapterNavigator
                chapters={chaptersQuery.data ?? []}
                errorMessage={chapterErrorMessage}
                isLoading={chaptersQuery.isLoading}
                isPending={isPending}
                onSelectChapter={(chapterNumber) =>
                  updateParams({
                    chapter: String(chapterNumber),
                    panel: "chapter",
                  })
                }
                onToggleVersionPanel={() =>
                  updateParams({
                    panel: "chapter",
                    versionPanel: versionPanelOpen ? null : "1",
                  })
                }
                selectedChapterNumber={selectedChapterNumber}
                versionPanelOpen={versionPanelOpen}
              />
              {chapterListState === "ready" ? (
                <ChapterEditor
                  chapterNumber={selectedChapterNumber}
                  projectId={projectId}
                  versionPanelOpen={versionPanelOpen}
                />
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="xl:sticky xl:top-6 xl:self-start">
          <StudioSidebarCards
            onFocusStaleChapter={(chapterNumber) =>
              updateParams({
                chapter: String(chapterNumber),
                panel: "chapter",
              })
            }
            projectId={projectId}
            staleChapters={staleChapters}
          />
        </div>
      </div>
    </div>
  );
}
