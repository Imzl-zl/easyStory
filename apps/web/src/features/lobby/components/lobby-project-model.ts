"use client";

import { useDeferredValue, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { buildFilteredProjects } from "@/features/lobby/components/lobby-project-support";
import { getErrorMessage } from "@/lib/api/client";
import { deleteProject, listProjects, restoreProject } from "@/lib/api/projects";
import { listTemplates } from "@/lib/api/templates";

export type ProjectActionVariables = {
  projectId: string;
  type: "delete" | "restore";
};

export function useLobbyProjectModel({ deletedOnly }: { deletedOnly: boolean }) {
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const deferredSearchText = useDeferredValue(searchText);
  const projectsQuery = useQuery({
    queryKey: ["projects", deletedOnly],
    queryFn: () => listProjects(deletedOnly),
  });
  const templatesQuery = useQuery({ queryKey: ["templates"], queryFn: listTemplates });
  const actionMutation = useMutation({
    mutationFn: ({ projectId, type }: ProjectActionVariables) =>
      type === "delete" ? deleteProject(projectId) : restoreProject(projectId),
    onSuccess: async () => {
      setFeedback("项目状态已更新。");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error) => setFeedback(getErrorMessage(error)),
  });
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
    feedback,
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
