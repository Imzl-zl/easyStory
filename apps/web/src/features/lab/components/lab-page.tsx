"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createAnalysis, deleteAnalysis, getAnalysis, listAnalyses } from "@/lib/api/analysis";
import { getErrorMessage } from "@/lib/api/client";
import type { AnalysisDetail, AnalysisSummary } from "@/lib/api/types";

import { LabCreatePanel } from "./lab-create-panel";
import { LabDeleteConfirmDialog } from "./lab-delete-confirm-dialog";
import { LabDetailPanel } from "./lab-detail-panel";
import { LabFeedbackBanner } from "./lab-feedback-banner";
import { LabSidebar } from "./lab-sidebar";
import {
  buildLabAnalysisSummary,
  buildLabAnalysisListOptions,
  buildLabAnalysisQueryKey,
  buildLabCreatePayload,
  buildLabFeedback,
  createInitialLabAnalysisFilterState,
  createInitialLabAnalysisFormState,
  hasActiveLabAnalysisListOptions,
  matchesLabAnalysisListOptions,
  prependLabAnalysisSummary,
  removeLabAnalysisSummary,
  resolveActiveLabAnalysisId,
  resolveNextLabSelectedIdAfterDelete,
  type LabFeedback,
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
  const [feedback, setFeedback] = useState<LabFeedback>(null);
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
      if (matchesFilters) {
        const createdSummary = buildLabAnalysisSummary(result);
        queryClient.setQueryData<AnalysisSummary[]>(listQueryKey, (current) =>
          prependLabAnalysisSummary(current, createdSummary),
        );
        queryClient.setQueryData(["analysis-detail", projectId, result.id], result);
      }
      setFeedback(
        buildLabFeedback(
          matchesFilters
            ? "分析记录已创建。"
            : "分析记录已创建，但当前过滤条件未包含它；清除过滤后可查看。",
        ),
      );
      setSelectedId(matchesFilters ? result.id : activeId);
      setFormState(createInitialLabAnalysisFormState());
      await refreshAnalyses();
    },
    onError: (error) => setFeedback(buildLabFeedback(getErrorMessage(error), "danger")),
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
      setFeedback(buildLabFeedback(`分析记录「${variables.analysisTitle}」已删除。`));
      setPendingDeleteAnalysis(null);
      await refreshAnalyses();
    },
    onError: (error) => {
      setFeedback(buildLabFeedback(getErrorMessage(error), "danger"));
      setPendingDeleteAnalysis(null);
    },
  });

  return (
    <div className="space-y-4">
      <LabFeedbackBanner feedback={feedback} />
      <div className="grid gap-6 xl:grid-cols-[280px_1fr_360px]">
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
        <LabDetailPanel
          activeId={activeId}
          analysis={detailQuery.data}
          errorMessage={detailQuery.error ? getErrorMessage(detailQuery.error) : null}
          hasActiveFilters={hasActiveFilters}
          isDeletePending={deleteMutation.isPending}
          isLoading={detailQuery.isLoading}
          onRequestDelete={setPendingDeleteAnalysis}
        />
        <LabCreatePanel
          formState={formState}
          isPending={createMutation.isPending}
          onFieldChange={(patch) => setFormState((current) => ({ ...current, ...patch }))}
          onSubmit={() => {
            setFeedback(null);
            createMutation.mutate();
          }}
        />
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
