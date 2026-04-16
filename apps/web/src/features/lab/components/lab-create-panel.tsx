"use client";

import { AppSelect } from "@/components/ui/app-select";

import type { LabAnalysisFormState } from "./lab-support";
import { LAB_ANALYSIS_TYPES } from "./lab-support";

type LabCreatePanelProps = {
  formState: LabAnalysisFormState;
  isPending: boolean;
  onFieldChange: (patch: Partial<LabAnalysisFormState>) => void;
  onSubmit: () => void;
};

export function LabCreatePanel({
  formState,
  isPending,
  onFieldChange,
  onSubmit,
}: Readonly<LabCreatePanelProps>) {
  return (
    <form
      className="panel-shell space-y-4 p-5"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div>
        <h2 className="font-serif text-xl font-semibold">记录新的洞察</h2>
      </div>
      <LabCreateFields formState={formState} isPending={isPending} onFieldChange={onFieldChange} />
      <button className="ink-button w-full" disabled={isPending} type="submit">
        {isPending ? "保存中..." : "保存洞察"}
      </button>
    </form>
  );
}

function LabCreateFields({
  formState,
  isPending,
  onFieldChange,
}: Readonly<{
  formState: LabAnalysisFormState;
  isPending: boolean;
  onFieldChange: (patch: Partial<LabAnalysisFormState>) => void;
}>) {
  return (
    <>
      <label className="block space-y-2">
        <span className="label-text">洞察类型</span>
        <AppSelect
          disabled={isPending}
          options={LAB_ANALYSIS_TYPES.map((item) => ({ label: item, value: item }))}
          value={formState.analysisType}
          onChange={(value) => onFieldChange({ analysisType: value as LabAnalysisFormState["analysisType"] })}
        />
      </label>
      <LabTextField label="来源标题" required value={formState.sourceTitle} onChange={(value) => onFieldChange({ sourceTitle: value })} />
      <LabTextField
        label="来源 Skill"
        placeholder="可选，例如 skill.style.river"
        value={formState.generatedSkillKey}
        onChange={(value) => onFieldChange({ generatedSkillKey: value })}
      />
      <LabTextAreaField label="洞察正文（JSON）" value={formState.result} onChange={(value) => onFieldChange({ result: value })} />
      <LabTextAreaField
        label="后续建议（JSON）"
        minHeightClassName="min-h-32"
        value={formState.suggestions}
        onChange={(value) => onFieldChange({ suggestions: value })}
      />
    </>
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
    <label className="block space-y-2">
      <span className="label-text">{label}</span>
      <input className="ink-input" value={value} onChange={(event) => onChange(event.target.value)} {...props} />
    </label>
  );
}

function LabTextAreaField({
  label,
  minHeightClassName = "min-h-40",
  onChange,
  value,
}: Readonly<{
  label: string;
  minHeightClassName?: string;
  onChange: (value: string) => void;
  value: string;
}>) {
  return (
    <label className="block space-y-2">
      <span className="label-text">{label}</span>
      <textarea
        className={`ink-textarea ${minHeightClassName}`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
