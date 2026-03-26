"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  AgentConfigDetail,
  SkillConfigDetail,
} from "@/lib/api/types";

import {
  CheckboxListField,
  FormNotice,
  FormSection,
  RadioGroupField,
  StaticField,
  TextAreaField,
  TextField,
} from "./config-registry-form-fields";
import {
  AGENT_TYPE_OPTIONS,
  formatCommaSeparatedList,
  parseCommaSeparatedList,
  sanitizeAgentDraft,
  sanitizeSkillDraft,
  validateJsonObject,
  validateNullableJsonObject,
} from "./config-registry-form-support";
import { JsonTextAreaField } from "./config-registry-json-field";
import type { ConfigRegistryReferenceFieldState } from "./config-registry-reference-support";
import { ModelConfigSection } from "./config-registry-model-config-section";
import { formatConfigRegistryDocument } from "./config-registry-support";

type CommonFormProps<T> = {
  detail: T;
  isPending: boolean;
  onDraftChange: (draft: T) => void;
  onDirtyChange: (value: boolean) => void;
  onSave: (payload: T) => void;
};

export function SkillFormEditor({
  detail,
  isPending,
  onDraftChange,
  onDirtyChange,
  onSave,
}: Readonly<CommonFormProps<SkillConfigDetail>>) {
  return (
    <SkillFormEditorBody
      key={formatConfigRegistryDocument(detail)}
      detail={detail}
      isPending={isPending}
      onDraftChange={onDraftChange}
      onDirtyChange={onDirtyChange}
      onSave={onSave}
    />
  );
}

function SkillFormEditorBody({
  detail,
  isPending,
  onDraftChange,
  onDirtyChange,
  onSave,
}: Readonly<CommonFormProps<SkillConfigDetail>>) {
  const [draft, setDraft] = useState(() => sanitizeSkillDraft(detail));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [jsonResetVersion, setJsonResetVersion] = useState(0);

  const isDirty = useMemo(
    () => Object.keys(errors).length > 0 || formatConfigRegistryDocument(draft) !== formatConfigRegistryDocument(detail),
    [detail, draft, errors],
  );

  useEffect(() => onDraftChange(draft), [draft, onDraftChange]);
  useEffect(() => onDirtyChange(isDirty), [isDirty, onDirtyChange]);

  return (
    <div className="space-y-4">
      <FormSection title="基本信息">
        <StaticField label="配置 ID" value={detail.id} />
        <div className="grid gap-3 md:grid-cols-2">
          <TextField label="名称" name="skill-name" required value={draft.name} onChange={(value) => setDraft({ ...draft, name: value })} />
          <TextField label="版本" name="skill-version" required value={draft.version} onChange={(value) => setDraft({ ...draft, version: value })} />
          <TextField label="分类" name="skill-category" required value={draft.category} onChange={(value) => setDraft({ ...draft, category: value })} />
          <TextField label="作者" name="skill-author" value={draft.author ?? ""} onChange={(value) => setDraft({ ...draft, author: value || null })} />
        </div>
        <TextField
          label="标签"
          name="skill-tags"
          placeholder="例如：story, generation"
          value={formatCommaSeparatedList(draft.tags)}
          onChange={(value) => setDraft({ ...draft, tags: parseCommaSeparatedList(value) })}
        />
        <TextAreaField label="描述" name="skill-description" value={draft.description ?? ""} onChange={(value) => setDraft({ ...draft, description: value || null })} />
      </FormSection>

      <FormSection title="Prompt 模板" description="Skill prompt 支持模板变量渲染。">
        <TextAreaField label="Prompt" minHeightClassName="min-h-64" name="skill-prompt" value={draft.prompt} onChange={(value) => setDraft({ ...draft, prompt: value })} />
      </FormSection>

      <FormSection title="输入输出契约" description="后端要求 `variables` 与 `inputs/outputs` 互斥，请只保留一侧。">
        <JsonTextAreaField
          emptyValue={{}}
          label="variables"
          parseValue={validateJsonObject}
          syncKey={`variables:${jsonResetVersion}`}
          value={draft.variables}
          onChange={(value) => setDraft({ ...draft, variables: value })}
          onErrorChange={(message) => setErrors((current) => updateError(current, "variables", message))}
        />
        <JsonTextAreaField
          emptyValue={{}}
          label="inputs"
          parseValue={validateJsonObject}
          syncKey={`inputs:${jsonResetVersion}`}
          value={draft.inputs}
          onChange={(value) => setDraft({ ...draft, inputs: value })}
          onErrorChange={(message) => setErrors((current) => updateError(current, "inputs", message))}
        />
        <JsonTextAreaField
          emptyValue={{}}
          label="outputs"
          parseValue={validateJsonObject}
          syncKey={`outputs:${jsonResetVersion}`}
          value={draft.outputs}
          onChange={(value) => setDraft({ ...draft, outputs: value })}
          onErrorChange={(message) => setErrors((current) => updateError(current, "outputs", message))}
        />
      </FormSection>

      <ModelConfigSection
        resetToken={jsonResetVersion}
        value={draft.model}
        onChange={(value) => setDraft({ ...draft, model: value })}
        onErrorChange={(message) => setErrors((current) => updateError(current, "model", message))}
      />

      <FormActions
        errorMessage={firstError(errors)}
        isDirty={isDirty}
        isPending={isPending}
        onReset={() => {
          setJsonResetVersion((current) => current + 1);
          setDraft(sanitizeSkillDraft(detail));
          setErrors({});
        }}
        onSave={() => onSave(draft)}
      />
    </div>
  );
}

export function AgentFormEditor({
  detail,
  isPending,
  mcpReferenceField,
  onDraftChange,
  onDirtyChange,
  onSave,
  skillReferenceField,
}: Readonly<
  CommonFormProps<AgentConfigDetail> & {
    mcpReferenceField: ConfigRegistryReferenceFieldState;
    skillReferenceField: ConfigRegistryReferenceFieldState;
  }
>) {
  return (
    <AgentFormEditorBody
      key={formatConfigRegistryDocument(detail)}
      detail={detail}
      isPending={isPending}
      mcpReferenceField={mcpReferenceField}
      onDraftChange={onDraftChange}
      onDirtyChange={onDirtyChange}
      onSave={onSave}
      skillReferenceField={skillReferenceField}
    />
  );
}

function AgentFormEditorBody({
  detail,
  isPending,
  mcpReferenceField,
  onDraftChange,
  onDirtyChange,
  onSave,
  skillReferenceField,
}: Readonly<
  CommonFormProps<AgentConfigDetail> & {
    mcpReferenceField: ConfigRegistryReferenceFieldState;
    skillReferenceField: ConfigRegistryReferenceFieldState;
  }
>) {
  const [draft, setDraft] = useState(() => sanitizeAgentDraft(detail));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [jsonResetVersion, setJsonResetVersion] = useState(0);

  const isDirty = useMemo(
    () => Object.keys(errors).length > 0 || formatConfigRegistryDocument(draft) !== formatConfigRegistryDocument(detail),
    [detail, draft, errors],
  );

  useEffect(() => onDraftChange(draft), [draft, onDraftChange]);
  useEffect(() => onDirtyChange(isDirty), [isDirty, onDirtyChange]);

  return (
    <div className="space-y-4">
      <FormSection title="基本信息">
        <StaticField label="配置 ID" value={detail.id} />
        <div className="grid gap-3 md:grid-cols-2">
          <TextField label="名称" name="agent-name" required value={draft.name} onChange={(value) => setDraft({ ...draft, name: value })} />
          <TextField label="版本" name="agent-version" required value={draft.version} onChange={(value) => setDraft({ ...draft, version: value })} />
          <TextField label="作者" name="agent-author" value={draft.author ?? ""} onChange={(value) => setDraft({ ...draft, author: value || null })} />
          <TextField label="标签" name="agent-tags" value={formatCommaSeparatedList(draft.tags)} onChange={(value) => setDraft({ ...draft, tags: parseCommaSeparatedList(value) })} />
        </div>
        <TextAreaField label="描述" name="agent-description" value={draft.description ?? ""} onChange={(value) => setDraft({ ...draft, description: value || null })} />
        <RadioGroupField
          label="类型"
          options={AGENT_TYPE_OPTIONS.map((item) => ({ label: item.label, value: item.value }))}
          value={draft.agent_type}
          onChange={(value) => {
            if (value === "reviewer") {
              setErrors((current) => updateError(current, "output_schema", null));
            }
            setDraft(sanitizeAgentDraft({ ...draft, agent_type: value as AgentConfigDetail["agent_type"] }));
          }}
        />
      </FormSection>

      <FormSection title="系统提示词" description="这里是纯文本，不做模板变量渲染。">
        <TextAreaField label="System Prompt" minHeightClassName="min-h-48" name="agent-system-prompt" value={draft.system_prompt} onChange={(value) => setDraft({ ...draft, system_prompt: value })} />
      </FormSection>

      {skillReferenceField.bannerMessage && skillReferenceField.bannerTone ? (
        <FormNotice message={skillReferenceField.bannerMessage} tone={skillReferenceField.bannerTone} />
      ) : null}
      <CheckboxListField label="绑定 Skills" description="从已注册 Skill 列表里选择。" emptyMessage={skillReferenceField.emptyMessage} options={skillReferenceField.options} values={draft.skill_ids} onChange={(values) => setDraft({ ...draft, skill_ids: values })} />
      {mcpReferenceField.bannerMessage && mcpReferenceField.bannerTone ? (
        <FormNotice message={mcpReferenceField.bannerMessage} tone={mcpReferenceField.bannerTone} />
      ) : null}
      <CheckboxListField label="绑定 MCP Servers" description="仅 Agent 与 Hook 使用同一组 MCP 配置。" emptyMessage={mcpReferenceField.emptyMessage} options={mcpReferenceField.options} values={draft.mcp_servers} onChange={(values) => setDraft({ ...draft, mcp_servers: values })} />

      {draft.agent_type !== "reviewer" ? (
        <JsonTextAreaField
          emptyValue={null}
          label="output_schema"
          parseValue={validateNullableJsonObject}
          syncKey={`output-schema:${jsonResetVersion}`}
          value={draft.output_schema}
          onChange={(value) => setDraft({ ...draft, output_schema: value })}
          onErrorChange={(message) => setErrors((current) => updateError(current, "output_schema", message))}
        />
      ) : (
        <FormSection title="输出 Schema">
          <StaticField label="output_schema" description="reviewer 类型不允许定义 output_schema。" value="当前类型下已禁用" />
        </FormSection>
      )}

      <ModelConfigSection
        resetToken={jsonResetVersion}
        value={draft.model}
        onChange={(value) => setDraft({ ...draft, model: value })}
        onErrorChange={(message) => setErrors((current) => updateError(current, "model", message))}
      />

      <FormActions
        errorMessage={firstError(errors)}
        isDirty={isDirty}
        isPending={isPending}
        onReset={() => {
          setJsonResetVersion((current) => current + 1);
          setDraft(sanitizeAgentDraft(detail));
          setErrors({});
        }}
        onSave={() => onSave(draft)}
      />
    </div>
  );
}

function FormActions({
  errorMessage,
  isDirty,
  isPending,
  onReset,
  onSave,
}: Readonly<{
  errorMessage: string | null;
  isDirty: boolean;
  isPending: boolean;
  onReset: () => void;
  onSave: () => void;
}>) {
  return (
    <div className="space-y-3">
      {errorMessage ? <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">{errorMessage}</div> : null}
      <div className="flex flex-wrap gap-2">
        <button className="ink-button" disabled={isPending || !isDirty || Boolean(errorMessage)} type="button" onClick={onSave}>
          {isPending ? "保存中…" : "保存配置"}
        </button>
        <button className="ink-button-secondary" disabled={isPending || !isDirty} type="button" onClick={onReset}>
          还原编辑
        </button>
      </div>
    </div>
  );
}

function updateError(current: Record<string, string>, key: string, message: string | null): Record<string, string> {
  if (!message) {
    const next = { ...current };
    delete next[key];
    return next;
  }
  return { ...current, [key]: message };
}

function firstError(errors: Record<string, string>): string | null {
  return Object.values(errors)[0] ?? null;
}
