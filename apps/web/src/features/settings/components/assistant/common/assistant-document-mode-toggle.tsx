"use client";

export type AssistantDocumentEditMode = "document" | "guided";

type AssistantDocumentModeToggleProps = {
  fileLabel: string;
  mode: AssistantDocumentEditMode;
  onChange: (mode: AssistantDocumentEditMode) => void;
  guidedDisabled?: boolean;
};

export function AssistantDocumentModeToggle({
  fileLabel,
  mode,
  onChange,
  guidedDisabled = false,
}: Readonly<AssistantDocumentModeToggleProps>) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-3xl bg-glass shadow-glass px-4 py-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-text-primary">编辑方式</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-pill bg-glass-heavy px-3 py-1 text-[12px] font-medium text-text-secondary">
          {fileLabel}
        </span>
        <button
          className="ink-tab h-9 px-4 text-[13px]"
          data-active={mode === "guided"}
          disabled={guidedDisabled}
          type="button"
          onClick={() => onChange("guided")}
        >
          可视化编辑
        </button>
        <button
          className="ink-tab h-9 px-4 text-[13px]"
          data-active={mode === "document"}
          type="button"
          onClick={() => onChange("document")}
        >
          按文件编辑
        </button>
      </div>
    </div>
  );
}
