import type { ProjectSummary } from "@/lib/api/types";

export function buildFilteredProjects(
  projects: ProjectSummary[] | undefined,
  keyword: string,
): ProjectSummary[] {
  const normalizedKeyword = keyword.trim().toLowerCase();
  if (!normalizedKeyword) {
    return projects ?? [];
  }
  return (projects ?? []).filter((project) => project.name.toLowerCase().includes(normalizedKeyword));
}
