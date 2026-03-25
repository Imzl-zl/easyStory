import { ProjectSettingsPage } from "@/features/project-settings/components/project-settings-page";

type ProjectSettingsRouteProps = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

export default async function ProjectSettingsRoutePage({
  params,
}: ProjectSettingsRouteProps) {
  const { projectId } = await params;
  return <ProjectSettingsPage projectId={projectId} />;
}
