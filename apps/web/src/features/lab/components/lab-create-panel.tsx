"use client";

import { useState } from "react";

import { AppSelect } from "@/components/ui/app-select";

import type { LabAnalysisFormState } from "./lab-support";
import { LAB_ANALYSIS_TYPES, createInitialLabAnalysisFormState } from "./lab-support";

type LabCreatePanelProps = {
  isPending: boolean;
  onCancel: () => void;
  onSubmit: (formState: LabAnalysisFormState) => void;
};

export function LabCreatePanel({
  isPending,
  onCancel,
  onSubmit,
}: Readonly<LabCreatePanelProps>) {
  const [formState, setFormState] = useState<LabAnalysisFormState>(createInitialLabAnalysisFormState);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    onSubmit(formState);
  };

  const handleFieldChange = (patch: Partial<LabAnalysisFormState>) => {
    setFormState((current) => ({ ...current, ...patch }));
  };

  return (
    <div className="h-full flex flex-col rounded" style={{ background: "var(--bg-muted)", border: "1px solid var(--line-soft)" }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid var(--line-soft)" }}>
        <span className="text-[12px] font-medium" style={{ color: "var(--text-secondary)" }}>记录新的洞察</span>
        <button
          className="px-3 py-1.5 rounded text-[11px] font-medium transition-colors"
          style={{ background: "var(--bg-surface)", color: "var(--text-secondary)" }}
          onClick={onCancel}
          type="button"
        >
          取消
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <form className="space-y-3" onSubmit={handleSubmit}>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>洞察类型</span>
            <AppSelect
              disabled={isPending}
              options={LAB_ANALYSIS_TYPES.map((item) => ({ label: item, value: item }))}
              value={formState.analysisType}
              onChange={(value) => handleFieldChange({ analysisType: value as LabAnalysisFormState["analysisType"] })}
            />
          </label>
          <LabTextField
            label="来源标题"
            required
            disabled={isPending}
            value={formState.sourceTitle}
            onChange={(value) => handleFieldChange({ sourceTitle: value })}
          />
          <LabTextField
            label="来源 Skill"
            disabled={isPending}
            placeholder="可选，例如 skill.style.river"
            value={formState.generatedSkillKey}
            onChange={(value) => handleFieldChange({ generatedSkillKey: value })}
          />
          <LabTextAreaField
            label="洞察正文（JSON）"
            disabled={isPending}
            value={formState.result}
            onChange={(value) => handleFieldChange({ result: value })}
          />
          <LabTextAreaField
            label="后续建议（JSON）"
            disabled={isPending}
            minHeightClassName="min-h-32"
            value={formState.suggestions}
            onChange={(value) => handleFieldChange({ suggestions: value })}
          />
          <button
            className="w-full px-4 py-2 rounded text-[12px] font-medium transition-all disabled:opacity-40"
            style={{ background: "var(--accent-primary)", color: "var(--bg-canvas)" }}
            disabled={isPending}
            type="submit"
          >
            {isPending ? "保存中..." : "保存洞察"}
          </button>
        </form>
      </div>
    </div>
  );
}

function LabTextField({
  label,
  onChange,
  value,
  ...props
}: Readonly<
  Omit<React.ComponentProps<"input">, "onChange" | "value"> & {
    label: string;
    onChange: (value: string) => void;
    value: string;
  }
>) {
  return (
    <label className="block space-y-1">
      <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <input
        className="w-full px-3 py-2 rounded text-[12px] outline-none"
        style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-soft)" }}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent-primary)"; }}
        onBlur={(e) => { e.currentTarget.style.borderColor = "var(--bg-muted)"; }}
        {...props}
      />
    </label>
  );
}

function LabTextAreaField({
  label,
  minHeightClassName = "min-h-40",
  onChange,
  value,
  ...props
}: Readonly<
  Omit<React.ComponentProps<"textarea">, "onChange" | "value"> & {
    label: string;
    minHeightClassName?: string;
    onChange: (value: string) => void;
    value: string;
  }
>) {
  return (
    <label className="block space-y-1">
      <span className="text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <textarea
        className={`w-full px-3 py-2 rounded text-[12px] outline-none resize-y ${minHeightClassName}`}
        style={{ background: "var(--bg-canvas)", color: "var(--text-primary)", border: "1px solid var(--line-soft)" }}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent-primary)"; }}
        onBlur={(e) => { e.currentTarget.style.borderColor = "var(--bg-muted)"; }}
        {...props}
      />
    </label>
  );
}
