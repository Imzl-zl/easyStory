"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { showAppNotice } from "@/components/ui/app-notice";
import {
  buildFilteredProjects,
  type ProjectActionType,
  resolveEmptyTrashNotice,
  resolveProjectActionNotice,
} from "@/features/lobby/components/projects/lobby-project-support";
import { getErrorMessage } from "@/lib/api/client";
import {
  deleteProject,
  emptyTrash,
  listProjects,
  physicalDeleteProject,
  restoreProject,
} from "@/lib/api/projects";
import { listTemplates } from "@/lib/api/templates";
import type { ProjectDetail } from "@/lib/api/types";

export type ProjectActionVariables = {
  projectId: string;
  type: ProjectActionType;
};

export function useLobbyProjectModel({ deletedOnly }: { deletedOnly: boolean }) {
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState("");
  const deferredSearchText = useDeferredValue(searchText);
  const projectsQuery = useQuery({
    queryKey: ["projects", deletedOnly],
    queryFn: () => listProjects(deletedOnly),
  });
  const templatesQuery = useQuery({ queryKey: ["templates"], queryFn: listTemplates });
  const actionMutation = useProjectActionMutation(queryClient);
  const emptyTrashMutation = useEmptyTrashMutation(queryClient);
  const filteredProjects = useMemo(
    () => buildFilteredProjects(projectsQuery.data, deferredSearchText),
    [deferredSearchText, projectsQuery.data],
  );
  const templateNameById = useMemo(
    () => new Map((templatesQuery.data ?? []).map((template) => [template.id, template.name])),
    [templatesQuery.data],
  );
  const templatePreviewNames = useMemo(
    () => (templatesQuery.data ?? []).slice(0, 3).map((template) => template.name),
    [templatesQuery.data],
  );

  return {
    actionMutation,
    deletedOnly,
    deletedProjectCount: projectsQuery.data?.length ?? 0,
    emptyTrashMutation,
    filteredProjects,
    projectsQuery,
    searchText,
    setSearchText,
    templateCount: templatesQuery.data?.length ?? 0,
    templateNameById,
    templatePreviewNames,
    templatesQuery,
  };
}

function useProjectActionMutation(
  queryClient: ReturnType<typeof useQueryClient>,
) {
  return useMutation<ProjectDetail | void, unknown, ProjectActionVariables>({
    mutationFn: ({ projectId, type }: ProjectActionVariables) => executeProjectAction(projectId, type),
    onSuccess: async (_, variables) => {
      showAppNotice(resolveProjectActionNotice(variables.type));
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "项目",
        tone: "danger",
      }),
  });
}

function useEmptyTrashMutation(
  queryClient: ReturnType<typeof useQueryClient>,
) {
  return useMutation({
    mutationFn: emptyTrash,
    onSuccess: async (result) => {
      showAppNotice(resolveEmptyTrashNotice(result));
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error) =>
      showAppNotice({
        content: getErrorMessage(error),
        title: "回收站",
        tone: "danger",
      }),
  });
}

function executeProjectAction(projectId: string, type: ProjectActionType) {
  if (type === "delete") {
    return deleteProject(projectId);
  }
  if (type === "restore") {
    return restoreProject(projectId);
  }
  return physicalDeleteProject(projectId);
}
