import { LabPage } from "@/features/lab/components/lab-page";

type LabRouteProps = {
  params: Promise<{ projectId: string }>;
};

export const dynamic = "force-dynamic";

export default async function ProjectLabPage({ params }: LabRouteProps) {
  const { projectId } = await params;
  return <LabPage projectId={projectId} />;
}
