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
        title="Template Library"
        description="模板库是 Lobby 的子视图：这里管理内建模板与自定义模板，不把模板 CRUD 混进书架页本体。"
        action={
          <div className="flex flex-wrap gap-2">
            <Link className="ink-button-secondary" href="/workspace/lobby">返回 Lobby</Link>
            <Link className="ink-button-secondary" href="/workspace/lobby/new">进入 Incubator</Link>
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
