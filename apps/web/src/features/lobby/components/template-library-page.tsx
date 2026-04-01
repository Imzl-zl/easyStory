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
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-3rem)] lg:min-h-[calc(100vh-3rem)] lg:overflow-hidden">
      <SectionCard
        bodyClassName="min-h-0 flex-1"
        className="flex min-h-0 flex-1 flex-col"
        title="模板库"
        description="查看和维护项目模板。"
        action={
          <div className="flex flex-wrap gap-2">
            <Link className="ink-button-secondary" href="/workspace/lobby">返回书架</Link>
            <Link className="ink-button-secondary" href="/workspace/lobby/new">创建作品</Link>
          </div>
        }
      >
        <div className="grid min-h-0 gap-5 xl:grid-cols-[260px_minmax(0,1fr)_340px] 2xl:grid-cols-[280px_minmax(0,1fr)_360px]">
          <TemplateLibrarySidebar model={model} />
          <TemplateLibraryDetailPanel model={model} />
          <TemplateLibraryEditorPanel model={model} />
        </div>
      </SectionCard>
    </div>
  );
}
