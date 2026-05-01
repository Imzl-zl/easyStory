"use client";

import { useDeferredValue, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Link from "next/link";
import { showAppNotice } from "@/components/ui/app-notice";
import { createAnalysis, deleteAnalysis, getAnalysis, listAnalyses } from "@/lib/api/analysis";
import { getErrorMessage } from "@/lib/api/client";
import type { AnalysisDetail, AnalysisSummary } from "@/lib/api/types";

import { LabCreatePanel } from "./lab-create-panel";
import { LabDeleteConfirmDialog } from "./lab-delete-confirm-dialog";
import { LabDetailPanel } from "./lab-detail-panel";
import { LabSidebar } from "./lab-sidebar";
import {
  buildLabAnalysisSummary,
  buildLabAnalysisListOptions,
  buildLabAnalysisQueryKey,
  buildLabCreatePayload,
  createInitialLabAnalysisFilterState,
  createInitialLabAnalysisFormState,
  formatLabAnalysisTitle,
  hasActiveLabAnalysisListOptions,
  matchesLabAnalysisListOptions,
  prependLabAnalysisSummary,
  removeLabAnalysisSummary,
  resolveActiveLabAnalysisId,
  resolveNextLabSelectedIdAfterDelete,
} from "./lab-support";

type LabPageProps = {
  projectId: string;
};

type DeleteAnalysisMutationVariables = {
  analysisId: string;
  analysisTitle: string;
};

export function LabPage({ projectId }: LabPageProps) {
  const queryClient = useQueryClient();
  const [filterState, setFilterState] = useState(createInitialLabAnalysisFilterState);
  const [formState, setFormState] = useState(createInitialLabAnalysisFormState);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pendingDeleteAnalysis, setPendingDeleteAnalysis] = useState<AnalysisSummary | AnalysisDetail | null>(null);
  const listOptions = useLabListOptions(filterState);
  const listQueryKey = buildLabAnalysisQueryKey(projectId, listOptions);
  const listQuery = useQuery({ queryKey: listQueryKey, queryFn: () => listAnalyses(projectId, listOptions) });
  const analyses = listQuery.data ?? [];
  const activeId = resolveActiveLabAnalysisId(analyses, selectedId);
  const detailQuery = useQuery({
    queryKey: ["analysis-detail", projectId, activeId],
    queryFn: () => getAnalysis(projectId, activeId as string),
    enabled: Boolean(activeId),
  });
  const hasActiveFilters = hasActiveLabAnalysisListOptions(listOptions);
  const createMutation = useCreateAnalysisMutation({
    activeId,
    formState,
    listOptions,
    listQueryKey,
    projectId,
    queryClient,
    setFormState,
    setSelectedId,
  });
  const deleteMutation = useDeleteAnalysisMutation({
    activeId,
    analyses,
    listQueryKey,
    projectId,
    queryClient,
    setPendingDeleteAnalysis,
    setSelectedId,
  });

  return (
    <div className="flex flex-col gap-5">
      <LabHero
        activeTitle={detailQuery.data ? formatLabAnalysisTitle(detailQuery.data) : null}
        analysesCount={analyses.length}
        hasActiveFilters={hasActiveFilters}
        projectId={projectId}
      />
      <div className="hero-card grid gap-4.5 p-4.5 [grid-template-columns:1fr] xl:[grid-template-columns:minmax(260px,320px)_minmax(0,1fr)_minmax(300px,360px)]">
        <aside className="min-w-0">
          <LabSidebar
            activeId={activeId}
            analyses={analyses}
            errorMessage={listQuery.error ? getErrorMessage(listQuery.error) : null}
            filters={filterState}
            isLoading={listQuery.isLoading}
            isPending={deleteMutation.isPending}
            onFilterChange={(patch) => setFilterState((current) => ({ ...current, ...patch }))}
            onSelect={setSelectedId}
          />
        </aside>
        <section className="min-w-0">
          <LabDetailPanel
            activeId={activeId}
            analysis={detailQuery.data}
            errorMessage={detailQuery.error ? getErrorMessage(detailQuery.error) : null}
            hasActiveFilters={hasActiveFilters}
            isDeletePending={deleteMutation.isPending}
            isLoading={detailQuery.isLoading}
            onRequestDelete={setPendingDeleteAnalysis}
          />
        </section>
        <aside className="min-w-0">
          <LabCreatePanel
            formState={formState}
            isPending={createMutation.isPending}
            onFieldChange={(patch) => setFormState((current) => ({ ...current, ...patch }))}
            onSubmit={() => createMutation.mutate()}
          />
        </aside>
      </div>
      {pendingDeleteAnalysis ? (
        <LabDeleteConfirmDialog
          analysisTitle={pendingDeleteAnalysis.source_title ?? pendingDeleteAnalysis.analysis_type}
          analysisType={pendingDeleteAnalysis.analysis_type}
          generatedSkillKey={pendingDeleteAnalysis.generated_skill_key}
          isPending={deleteMutation.isPending}
          onClose={() => setPendingDeleteAnalysis(null)}
          onConfirm={() =>
            deleteMutation.mutate({
              analysisId: pendingDeleteAnalysis.id,
              analysisTitle: pendingDeleteAnalysis.source_title ?? pendingDeleteAnalysis.analysis_type,
            })
          }
        />
      ) : null}
    </div>
  );
}

function LabHero({
  activeTitle,
  analysesCount,
  hasActiveFilters,
  projectId,
}: Readonly<{
  activeTitle: string | null;
  analysesCount: number;
  hasActiveFilters: boolean;
  projectId: string;
}>) {
  return (
    <section className="hero-card grid gap-4.5 p-6">
      <div>
        <p className="label-overline">分析实验室</p>
        <h1 className="max-w-[900px] font-serif text-[clamp(2rem,4vw,3.6rem)] leading-tight">把灵感拆解、文风判断和结构分析留在项目语境里。</h1>
      </div>
      <div className="grid gap-3 [grid-template-columns:repeat(3,minmax(0,1fr))]">
        <article className="grid gap-2.5 min-h-[110px] p-4.5 rounded-2xl bg-gradient-to-b from-glass-heavy to-glass shadow-glass">
          <span className="label-overline">当前记录</span>
          <strong className="font-serif text-2xl leading-tight">{analysesCount}</strong>
        </article>
        <article className="grid gap-2.5 min-h-[110px] p-4.5 rounded-2xl bg-gradient-to-b from-glass-heavy to-glass shadow-glass">
          <span className="label-overline">筛选状态</span>
          <strong className="font-serif text-2xl leading-tight">{hasActiveFilters ? "已聚焦" : "查看全部"}</strong>
        </article>
        <article className="grid gap-2.5 min-h-[110px] p-4.5 rounded-2xl bg-gradient-to-b from-glass-heavy to-glass shadow-glass">
          <span className="label-overline">当前焦点</span>
          <strong className="font-serif text-2xl leading-tight">{activeTitle ?? "选择一条洞察"}</strong>
        </article>
      </div>
      <div className="flex gap-2.5">
        <Link className="ink-link-button" href={`/workspace/project/${projectId}/studio`}>
          创作
        </Link>
        <Link className="ink-link-button" href={`/workspace/project/${projectId}/engine`}>
          工作流
        </Link>
      </div>
    </section>
  );
}

function useLabListOptions(filterState: ReturnType<typeof createInitialLabAnalysisFilterState>) {
  const deferredContentId = useDeferredValue(filterState.contentId.trim());
  const deferredGeneratedSkillKey = useDeferredValue(filterState.generatedSkillKey.trim());

  return useMemo(
    () =>
      buildLabAnalysisListOptions({
        ...filterState,
        contentId: deferredContentId,
        generatedSkillKey: deferredGeneratedSkillKey,
      }),
    [deferredContentId, deferredGeneratedSkillKey, filterState],
  );
}

function useCreateAnalysisMutation({
  activeId,
  formState,
  listOptions,
  listQueryKey,
  projectId,
  queryClient,
  setFormState,
  setSelectedId,
}: Readonly<{
  activeId: string | null;
  formState: ReturnType<typeof createInitialLabAnalysisFormState>;
  listOptions: ReturnType<typeof buildLabAnalysisListOptions>;
  listQueryKey: ReturnType<typeof buildLabAnalysisQueryKey>;
  projectId: string;
  queryClient: ReturnType<typeof useQueryClient>;
  setFormState: Dispatch<SetStateAction<ReturnType<typeof createInitialLabAnalysisFormState>>>;
  setSelectedId: Dispatch<SetStateAction<string | null>>;
}>) {
  return useMutation({
    mutationFn: () => createAnalysis(projectId, buildLabCreatePayload(formState)),
    onSuccess: async (result) => {
      const matchesFilters = matchesLabAnalysisListOptions(result, listOptions);
      if (matchesFilters) {
        const createdSummary = buildLabAnalysisSummary(result);
        queryClient.setQueryData<AnalysisSummary[]>(listQueryKey, (current) =>
          prependLabAnalysisSummary(current, createdSummary),
        );
        queryClient.setQueryData(["analysis-detail", projectId, result.id], result);
      }
      showAppNotice({
        content: matchesFilters ? "洞察已保存。" : "洞察已保存，清除筛选后可在列表中看到。",
        title: "洞察",
        tone: "success",
      });
      setSelectedId(matchesFilters ? result.id : activeId);
      setFormState(createInitialLabAnalysisFormState());
      await refreshAnalyses(projectId, queryClient);
    },
    onError: (error) =>
      showAppNotice({ content: getErrorMessage(error), title: "洞察", tone: "danger" }),
  });
}

function useDeleteAnalysisMutation({
  activeId,
  analyses,
  listQueryKey,
  projectId,
  queryClient,
  setPendingDeleteAnalysis,
  setSelectedId,
}: Readonly<{
  activeId: string | null;
  analyses: AnalysisSummary[];
  listQueryKey: ReturnType<typeof buildLabAnalysisQueryKey>;
  projectId: string;
  queryClient: ReturnType<typeof useQueryClient>;
  setPendingDeleteAnalysis: Dispatch<SetStateAction<AnalysisSummary | AnalysisDetail | null>>;
  setSelectedId: Dispatch<SetStateAction<string | null>>;
}>) {
  return useMutation({
    mutationFn: ({ analysisId }: DeleteAnalysisMutationVariables) => deleteAnalysis(projectId, analysisId),
    onSuccess: async (_, variables) => {
      queryClient.setQueryData<AnalysisSummary[]>(listQueryKey, (current) =>
        removeLabAnalysisSummary(current, variables.analysisId),
      );
      queryClient.removeQueries({ exact: true, queryKey: ["analysis-detail", projectId, variables.analysisId] });
      setSelectedId(resolveNextLabSelectedIdAfterDelete(analyses, activeId, variables.analysisId));
      showAppNotice({
        content: `洞察「${variables.analysisTitle}」已删除。`,
        title: "洞察",
        tone: "success",
      });
      setPendingDeleteAnalysis(null);
      await refreshAnalyses(projectId, queryClient);
    },
    onError: (error) => {
      showAppNotice({ content: getErrorMessage(error), title: "洞察", tone: "danger" });
      setPendingDeleteAnalysis(null);
    },
  });
}

async function refreshAnalyses(projectId: string, queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["analyses", projectId] }),
    queryClient.invalidateQueries({ queryKey: ["analysis-detail", projectId] }),
    queryClient.invalidateQueries({ queryKey: ["engine-context-style-analyses", projectId] }),
  ]);
}
