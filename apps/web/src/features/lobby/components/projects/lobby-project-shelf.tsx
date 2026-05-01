"use client";

import type { UseMutationResult } from "@tanstack/react-query";

import { LobbyProjectCard } from "@/features/lobby/components/projects/lobby-project-card";
import { LobbyProjectListItem } from "@/features/lobby/components/projects/lobby-project-list-item";
import type { ProjectActionVariables } from "@/features/lobby/components/projects/lobby-project-model";
import {
  ProjectShelfEmptyState,
  ProjectShelfErrorState,
  ProjectShelfLoadingState,
} from "@/features/lobby/components/projects/lobby-project-shelf-states";
import type { ProjectDetail, ProjectSummary } from "@/lib/api/types";

type ProjectActionMutation = UseMutationResult<
  ProjectDetail | void,
  unknown,
  ProjectActionVariables
>;

type LobbyProjectShelfProps = {
  actionMutation: ProjectActionMutation;
  deletedOnly: boolean;
  error: unknown;
  isLoading: boolean;
  projects: ProjectSummary[];
  viewMode?: "grid" | "list";
};

export function LobbyProjectShelf({
  actionMutation,
  deletedOnly,
  error,
  isLoading,
  projects,
  viewMode = "grid",
}: LobbyProjectShelfProps) {
  if (isLoading) {
    return <ProjectShelfLoadingState />;
  }

  if (error) {
    return <ProjectShelfErrorState error={error} />;
  }

  if (projects.length === 0) {
    return <ProjectShelfEmptyState deletedOnly={deletedOnly} />;
  }

  if (viewMode === "list") {
    return (
      <div className="flex flex-col gap-3">
        {projects.map((project) => (
          <LobbyProjectListItem
            actionMutation={actionMutation}
            key={project.id}
            project={project}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-5 sm:gap-6 [grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr))]">
      {projects.map((project, index) => (
        <LobbyProjectCard
          actionMutation={actionMutation}
          key={project.id}
          project={project}
          index={index}
        />
      ))}
    </div>
  );
}
