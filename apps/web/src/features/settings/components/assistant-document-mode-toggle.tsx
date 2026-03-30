"use client";

export type AssistantDocumentEditMode = "document" | "guided";

type AssistantDocumentModeToggleProps = {
  description: string;
  fileLabel: string;
  mode: AssistantDocumentEditMode;
  onChange: (mode: AssistantDocumentEditMode) => void;
  guidedDisabled?: boolean;
};

export function AssistantDocumentModeToggle({
  description,
  fileLabel,
  mode,
  onChange,
  guidedDisabled = false,
}: Readonly<AssistantDocumentModeToggleProps>) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 rounded-[24px] border border-[var(--line-soft)] bg-[rgba(255,255,255,0.72)] px-4 py-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-[var(--text-primary)]">编辑方式</p>
        <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">{description}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-[rgba(248,243,235,0.92)] px-3 py-1 text-[12px] font-medium text-[var(--text-secondary)]">
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
