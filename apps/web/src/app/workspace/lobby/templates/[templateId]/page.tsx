import { TemplateLibraryPage } from "@/features/lobby/components/templates/template-library-page";

type TemplateLibraryDetailRouteProps = {
  params: Promise<{ templateId: string }>;
};

export const dynamic = "force-dynamic";

export default async function WorkspaceLobbyTemplateDetailPage({
  params,
}: TemplateLibraryDetailRouteProps) {
  const { templateId } = await params;
  return <TemplateLibraryPage initialTemplateId={templateId} />;
}
