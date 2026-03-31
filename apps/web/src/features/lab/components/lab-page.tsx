"use client";

import { useDeferredValue, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import { createAnalysis, deleteAnalysis, getAnalysis, listAnalyses } from "@/lib/api/analysis";
import { getErrorMessage } from "@/lib/api/client";
import type { AnalysisDetail, AnalysisSummary } from "@/lib/api/types";

import { LabCreatePanel } from "./lab-create-panel";
import { LabDeleteConfirmDialog } from "./lab-delete-confirm-dialog";
import { LabDetailPanel } from "./lab-detail-panel";
import styles from "./lab-page.module.css";
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
    <div className={styles.page}>
      <LabHero
        activeTitle={detailQuery.data ? formatLabAnalysisTitle(detailQuery.data) : null}
        analysesCount={analyses.length}
        hasActiveFilters={hasActiveFilters}
      />
      <div className={styles.stage}>
        <aside className={styles.column}>
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
        <section className={styles.column}>
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
        <aside className={styles.column}>
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
}: Readonly<{
  activeTitle: string | null;
  analysesCount: number;
  hasActiveFilters: boolean;
}>) {
  return (
    <section className={styles.hero}>
      <div>
        <p className={styles.eyebrow}>洞察工作台</p>
        <h1 className={styles.heroTitle}>把灵感拆解、文风判断和结构分析留在项目语境里。</h1>
        <p className={styles.heroDescription}>
          这里不再像分析记录后台，而更像围绕当前作品展开的一张研究桌。
        </p>
      </div>
      <div className={styles.heroCards}>
        <article className={styles.heroCard}>
          <span className={styles.heroCardLabel}>当前记录</span>
          <strong className={styles.heroCardValue}>{analysesCount}</strong>
        </article>
        <article className={styles.heroCard}>
          <span className={styles.heroCardLabel}>筛选状态</span>
          <strong className={styles.heroCardValue}>{hasActiveFilters ? "已聚焦" : "查看全部"}</strong>
        </article>
        <article className={styles.heroCard}>
          <span className={styles.heroCardLabel}>当前焦点</span>
          <strong className={styles.heroCardValue}>{activeTitle ?? "选择一条洞察"}</strong>
        </article>
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
