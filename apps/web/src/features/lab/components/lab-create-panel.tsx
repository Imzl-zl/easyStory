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
      <div className="space-y-1">
        <h2 className="font-serif text-xl font-semibold">新建分析</h2>
        <p className="text-sm leading-6 text-[var(--text-secondary)]">
          选择分析类型，填好来源标题和结果内容，就能把这条分析记录保存下来。
        </p>
      </div>
      <LabCreateFields formState={formState} isPending={isPending} onFieldChange={onFieldChange} />
      <button className="ink-button w-full" disabled={isPending} type="submit">
        {isPending ? "创建中..." : "创建分析"}
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
        <span className="label-text">分析类型</span>
        <AppSelect
          disabled={isPending}
          options={LAB_ANALYSIS_TYPES.map((item) => ({ label: item, value: item }))}
          value={formState.analysisType}
          onChange={(value) => onFieldChange({ analysisType: value as LabAnalysisFormState["analysisType"] })}
        />
      </label>
      <LabTextField label="来源标题" required value={formState.sourceTitle} onChange={(value) => onFieldChange({ sourceTitle: value })} />
      <LabTextField
        label="生成标记"
        placeholder="可选，例如 skill.style.river"
        value={formState.generatedSkillKey}
        onChange={(value) => onFieldChange({ generatedSkillKey: value })}
      />
      <LabTextAreaField label="分析结果（JSON）" value={formState.result} onChange={(value) => onFieldChange({ result: value })} />
      <LabTextAreaField
        label="建议列表（JSON）"
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
