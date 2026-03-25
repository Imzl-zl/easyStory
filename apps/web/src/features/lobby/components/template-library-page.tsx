"use client";

import Link from "next/link";

import { SectionCard } from "@/components/ui/section-card";
import { useTemplateLibraryModel } from "@/features/lobby/components/template-library-model";
import { TemplateLibraryDetailPanel } from "@/features/lobby/components/template-library-detail-panel";
import { TemplateLibraryEditorPanel } from "@/features/lobby/components/template-library-editor-panel";
import { TemplateLibrarySidebar } from "@/features/lobby/components/template-library-sidebar";

type TemplateLibraryPageProps = {
  initialTemplateId?: string | null;
};

export function TemplateLibraryPage({ initialTemplateId = null }: TemplateLibraryPageProps) {
  const model = useTemplateLibraryModel(initialTemplateId);

  return (
    <div className="space-y-6">
      <SectionCard
        title="模板库"
        description="管理创作模板，为你的故事定下基调。"
        action={
          <div className="flex flex-wrap gap-2">
            <Link className="ink-button-secondary" href="/workspace/lobby">返回项目大厅</Link>
            <Link className="ink-button-secondary" href="/workspace/lobby/new">创建项目</Link>
          </div>
        }
      >
        <div className="grid gap-6 xl:grid-cols-[280px_1fr_360px]">
          <TemplateLibrarySidebar model={model} />
          <TemplateLibraryDetailPanel model={model} />
          <TemplateLibraryEditorPanel model={model} />
        </div>
      </SectionCard>
    </div>
  );
}
