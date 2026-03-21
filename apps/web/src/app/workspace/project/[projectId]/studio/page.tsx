import { StudioPage } from "@/features/studio/components/studio-page";

type StudioRouteProps = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

export default async function ProjectStudioPage({ params }: StudioRouteProps) {
  const { projectId } = await params;
  return <StudioPage projectId={projectId} />;
}
