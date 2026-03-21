import { EnginePage } from "@/features/engine/components/engine-page";

type EngineRouteProps = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

export default async function ProjectEnginePage({ params }: EngineRouteProps) {
  const { projectId } = await params;
  return <EnginePage projectId={projectId} />;
}
