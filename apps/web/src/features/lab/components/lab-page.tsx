"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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
  const deferredContentId = useDeferredValue(filterState.contentId.trim());
  const deferredGeneratedSkillKey = useDeferredValue(filterState.generatedSkillKey.trim());
  const listOptions = useMemo(
    () =>
      buildLabAnalysisListOptions({
        ...filterState,
        contentId: deferredContentId,
        generatedSkillKey: deferredGeneratedSkillKey,
      }),
    [deferredContentId, deferredGeneratedSkillKey, filterState],
  );
  const listQueryKey = buildLabAnalysisQueryKey(projectId, listOptions);

  const listQuery = useQuery({
    queryKey: listQueryKey,
    queryFn: () => listAnalyses(projectId, listOptions),
  });
  const analyses = listQuery.data ?? [];
  const activeId = resolveActiveLabAnalysisId(analyses, selectedId);
  const hasActiveFilters = hasActiveLabAnalysisListOptions(listOptions);

  const detailQuery = useQuery({
    queryKey: ["analysis-detail", projectId, activeId],
    queryFn: () => getAnalysis(projectId, activeId as string),
    enabled: Boolean(activeId),
  });

  const refreshAnalyses = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["analyses", projectId] }),
      queryClient.invalidateQueries({ queryKey: ["analysis-detail", projectId] }),
      queryClient.invalidateQueries({ queryKey: ["engine-context-style-analyses", projectId] }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createAnalysis(projectId, buildLabCreatePayload(formState)),
    onSuccess: async (result) => {
      const matchesFilters = matchesLabAnalysisListOptions(result, listOptions);
      const message = matchesFilters
        ? "分析记录已创建。"
        : "分析记录已创建，但当前筛选条件里还看不到，清除筛选后即可查看。";
      if (matchesFilters) {
        const createdSummary = buildLabAnalysisSummary(result);
        queryClient.setQueryData<AnalysisSummary[]>(listQueryKey, (current) =>
          prependLabAnalysisSummary(current, createdSummary),
        );
        queryClient.setQueryData(["analysis-detail", projectId, result.id], result);
      }
      showAppNotice({
        content: message,
        title: "分析记录",
        tone: "success",
      });
      setSelectedId(matchesFilters ? result.id : activeId);
      setFormState(createInitialLabAnalysisFormState());
      await refreshAnalyses();
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "分析记录",
        tone: "danger",
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ analysisId }: DeleteAnalysisMutationVariables) => deleteAnalysis(projectId, analysisId),
    onSuccess: async (_, variables) => {
      queryClient.setQueryData<AnalysisSummary[]>(listQueryKey, (current) =>
        removeLabAnalysisSummary(current, variables.analysisId),
      );
      queryClient.removeQueries({
        exact: true,
        queryKey: ["analysis-detail", projectId, variables.analysisId],
      });
      setSelectedId(resolveNextLabSelectedIdAfterDelete(analyses, activeId, variables.analysisId));
      showAppNotice({
        content: `分析记录「${variables.analysisTitle}」已删除。`,
        title: "分析记录",
        tone: "success",
      });
      setPendingDeleteAnalysis(null);
      await refreshAnalyses();
    },
    onError: (error) => {
      showAppNotice({
        content: getErrorMessage(error),
        title: "分析记录",
        tone: "danger",
      });
      setPendingDeleteAnalysis(null);
    },
  });

  return (
    <div className="space-y-4">
      <div className="grid items-start gap-6 xl:grid-cols-[280px_minmax(0,1fr)] min-[1900px]:grid-cols-[280px_minmax(0,1fr)_360px]">
        <div className="xl:sticky xl:top-6">
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
        </div>
        <div className="grid min-w-0 gap-6 min-[1900px]:contents">
          <LabDetailPanel
            activeId={activeId}
            analysis={detailQuery.data}
            errorMessage={detailQuery.error ? getErrorMessage(detailQuery.error) : null}
            hasActiveFilters={hasActiveFilters}
            isDeletePending={deleteMutation.isPending}
            isLoading={detailQuery.isLoading}
            onRequestDelete={setPendingDeleteAnalysis}
          />
          <div className="min-[1900px]:max-h-[calc(100vh-12rem)] min-[1900px]:overflow-y-auto min-[1900px]:overscroll-y-contain">
            <LabCreatePanel
              formState={formState}
              isPending={createMutation.isPending}
              onFieldChange={(patch) => setFormState((current) => ({ ...current, ...patch }))}
              onSubmit={() => createMutation.mutate()}
            />
          </div>
        </div>
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
