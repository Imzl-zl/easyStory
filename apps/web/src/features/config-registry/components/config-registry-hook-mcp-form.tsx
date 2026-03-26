"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  ConfigRegistryObject,
  HookConfigDetail,
  McpServerConfigDetail,
} from "@/lib/api/types";

import {
  CheckboxListField,
  FormNotice,
  FormSection,
  RadioGroupField,
  SelectField,
  StaticField,
  TextAreaField,
  TextField,
} from "./config-registry-form-fields";
import {
  buildDefaultHookActionConfig,
  HOOK_ACTION_TYPE_OPTIONS,
  HOOK_EVENT_OPTIONS,
  HOOK_NODE_TYPE_OPTIONS,
  isHookNodeEvent,
  sanitizeHookDraft,
  validateJsonObject,
  validateJsonValue,
  validateStringMap,
  WEBHOOK_METHOD_OPTIONS,
} from "./config-registry-form-support";
import { JsonTextAreaField } from "./config-registry-json-field";
import type { ConfigRegistryReferenceFieldState } from "./config-registry-reference-support";
import { formatConfigRegistryDocument } from "./config-registry-support";

type HookMcpCommonProps<T> = {
  detail: T;
  isPending: boolean;
  onDraftChange: (draft: T) => void;
  onDirtyChange: (value: boolean) => void;
  onSave: (payload: T) => void;
};

export function HookFormEditor({
  agentReferenceField,
  detail,
  isPending,
  mcpReferenceField,
  onDraftChange,
  onDirtyChange,
  onSave,
}: Readonly<
  HookMcpCommonProps<HookConfigDetail> & {
    agentReferenceField: ConfigRegistryReferenceFieldState;
    mcpReferenceField: ConfigRegistryReferenceFieldState;
  }
>) {
  return (
    <HookFormEditorBody
      agentReferenceField={agentReferenceField}
      key={formatConfigRegistryDocument(detail)}
      detail={detail}
      isPending={isPending}
      mcpReferenceField={mcpReferenceField}
      onDraftChange={onDraftChange}
      onDirtyChange={onDirtyChange}
      onSave={onSave}
    />
  );
}

function HookFormEditorBody({
  agentReferenceField,
  detail,
  isPending,
  mcpReferenceField,
  onDraftChange,
  onDirtyChange,
  onSave,
}: Readonly<
  HookMcpCommonProps<HookConfigDetail> & {
    agentReferenceField: ConfigRegistryReferenceFieldState;
    mcpReferenceField: ConfigRegistryReferenceFieldState;
  }
>) {
  const [draft, setDraft] = useState(() => sanitizeHookDraft(detail));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [jsonResetVersion, setJsonResetVersion] = useState(0);
  const actionConfig = draft.action.config ?? buildDefaultHookActionConfig(draft.action.action_type);
  const condition = draft.condition ?? { field: "", operator: "==", value: "" };

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
          <TextField label="名称" name="hook-name" required value={draft.name} onChange={(value) => setDraft({ ...draft, name: value })} />
          <TextField label="版本" name="hook-version" required value={draft.version} onChange={(value) => setDraft({ ...draft, version: value })} />
          <TextField label="作者" name="hook-author" value={draft.author ?? ""} onChange={(value) => setDraft({ ...draft, author: value || null })} />
          <TextField label="优先级" inputMode="numeric" name="hook-priority" value={String(draft.priority)} onChange={(value) => setDraft({ ...draft, priority: parseNumber(value, draft.priority) })} />
        </div>
        <TextAreaField label="描述" name="hook-description" value={draft.description ?? ""} onChange={(value) => setDraft({ ...draft, description: value || null })} />
        <label className="flex items-center gap-3 text-sm text-[var(--text-primary)]">
          <input checked={draft.enabled} type="checkbox" onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} />
          已启用
        </label>
      </FormSection>

      <FormSection title="触发条件">
        <SelectField label="事件" options={HOOK_EVENT_OPTIONS.map(toSimpleOption)} value={draft.trigger.event} onChange={(value) => setDraft(sanitizeHookDraft({ ...draft, trigger: { ...draft.trigger, event: value } }))} />
        {isHookNodeEvent(draft.trigger.event) ? (
          <CheckboxListField label="节点类型过滤" emptyMessage="暂无节点类型。" options={HOOK_NODE_TYPE_OPTIONS.map(toSimpleOption)} values={draft.trigger.node_types} onChange={(values) => setDraft({ ...draft, trigger: { ...draft.trigger, node_types: values } })} />
        ) : (
          <StaticField label="节点类型过滤" description="当前事件不消费 node_types，保存时会自动清空。" value="当前事件不适用" />
        )}
      </FormSection>

      <FormSection title="执行条件">
        <div className="grid gap-3 md:grid-cols-3">
          <TextField label="字段路径" name="hook-condition-field" value={condition.field} onChange={(value) => setDraft({ ...draft, condition: buildCondition({ ...condition, field: value }) })} />
          <SelectField label="操作符" options={["==", "!=", ">", "<", ">=", "<=", "in", "not_in"].map((value) => ({ label: value, value }))} value={condition.operator} onChange={(value) => setDraft({ ...draft, condition: buildCondition({ ...condition, operator: value }) })} />
          <TextField label="比较值" name="hook-condition-value" value={String(condition.value ?? "")} onChange={(value) => setDraft({ ...draft, condition: buildCondition({ ...condition, value }) })} />
        </div>
      </FormSection>

      <FormSection title="动作配置">
        <RadioGroupField label="动作类型" options={HOOK_ACTION_TYPE_OPTIONS.map(toSimpleOption)} value={draft.action.action_type} onChange={(value) => {
          setErrors((current) => clearHookActionErrors(current));
          setDraft({ ...draft, action: { action_type: value as HookConfigDetail["action"]["action_type"], config: buildDefaultHookActionConfig(value as HookConfigDetail["action"]["action_type"]) } });
        }} />
        {draft.action.action_type === "script" ? (
          <div className="grid gap-3 md:grid-cols-2">
            <TextField label="module" name="hook-script-module" value={readString(actionConfig.module)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, module: value } } })} />
            <TextField label="function" name="hook-script-function" value={readString(actionConfig.function)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, function: value } } })} />
            <JsonTextAreaField emptyValue={{}} label="params" parseValue={validateJsonObject} syncKey={`script-params:${jsonResetVersion}`} value={asObject(actionConfig.params)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, params: value } } })} onErrorChange={(message) => setErrors((current) => updateError(current, "hook-action", message))} />
          </div>
        ) : null}
        {draft.action.action_type === "webhook" ? (
          <div className="grid gap-3 md:grid-cols-2">
            <TextField label="url" name="hook-webhook-url" type="url" value={readString(actionConfig.url)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, url: value } } })} />
            <SelectField label="method" options={WEBHOOK_METHOD_OPTIONS.map(toSimpleOption)} value={readString(actionConfig.method) || "POST"} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, method: value } } })} />
            <JsonTextAreaField emptyValue={{}} label="headers" parseValue={validateStringMap} syncKey={`webhook-headers:${jsonResetVersion}`} value={asStringMap(actionConfig.headers)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, headers: value } } })} onErrorChange={(message) => setErrors((current) => updateError(current, "hook-action", message))} />
            <JsonTextAreaField emptyValue={{}} label="body" parseValue={validateJsonValue} syncKey={`webhook-body:${jsonResetVersion}`} value={actionConfig.body ?? {}} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, body: value } } })} onErrorChange={(message) => setErrors((current) => updateError(current, "hook-action-body", message))} />
          </div>
        ) : null}
        {draft.action.action_type === "agent" ? (
          <div className="grid gap-3 md:grid-cols-2">
            {agentReferenceField.bannerMessage || agentReferenceField.options.length === 0 ? (
              <div className="md:col-span-2">
                <FormNotice
                  message={agentReferenceField.bannerMessage ?? agentReferenceField.emptyMessage}
                  tone={agentReferenceField.bannerTone ?? "muted"}
                />
              </div>
            ) : null}
            <SelectField label="agent_id" options={[{ label: "请选择 Agent", value: "" }, ...agentReferenceField.options]} value={readString(actionConfig.agent_id)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, agent_id: value } } })} />
            <JsonTextAreaField emptyValue={{}} label="input_mapping" parseValue={validateJsonObject} syncKey={`agent-input:${jsonResetVersion}`} value={asObject(actionConfig.input_mapping)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, input_mapping: value } } })} onErrorChange={(message) => setErrors((current) => updateError(current, "hook-action", message))} />
          </div>
        ) : null}
        {draft.action.action_type === "mcp" ? (
          <div className="grid gap-3 md:grid-cols-2">
            {mcpReferenceField.bannerMessage || mcpReferenceField.options.length === 0 ? (
              <div className="md:col-span-2">
                <FormNotice
                  message={mcpReferenceField.bannerMessage ?? mcpReferenceField.emptyMessage}
                  tone={mcpReferenceField.bannerTone ?? "muted"}
                />
              </div>
            ) : null}
            <SelectField label="server_id" options={[{ label: "请选择 MCP Server", value: "" }, ...mcpReferenceField.options]} value={readString(actionConfig.server_id)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, server_id: value } } })} />
            <TextField label="tool_name" name="hook-tool-name" value={readString(actionConfig.tool_name)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, tool_name: value } } })} />
            <JsonTextAreaField emptyValue={{}} label="arguments" parseValue={validateJsonObject} syncKey={`mcp-arguments:${jsonResetVersion}`} value={asObject(actionConfig.arguments)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, arguments: value } } })} onErrorChange={(message) => setErrors((current) => updateError(current, "hook-action", message))} />
            <JsonTextAreaField emptyValue={{}} label="input_mapping" parseValue={validateJsonObject} syncKey={`mcp-input:${jsonResetVersion}`} value={asObject(actionConfig.input_mapping)} onChange={(value) => setDraft({ ...draft, action: { ...draft.action, config: { ...actionConfig, input_mapping: value } } })} onErrorChange={(message) => setErrors((current) => updateError(current, "hook-action-mapping", message))} />
          </div>
        ) : null}
      </FormSection>

      <FormSection title="执行设置">
        <div className="grid gap-3 md:grid-cols-2">
          <TextField label="超时（秒）" inputMode="numeric" name="hook-timeout" value={String(draft.timeout)} onChange={(value) => setDraft({ ...draft, timeout: parseNumber(value, draft.timeout) })} />
          <label className="flex items-center gap-3 text-sm text-[var(--text-primary)]">
            <input checked={draft.retry !== null} type="checkbox" onChange={(event) => setDraft({ ...draft, retry: event.target.checked ? draft.retry ?? { delay: 1, max_attempts: 3 } : null })} />
            启用重试
          </label>
        </div>
        {draft.retry ? (
          <div className="grid gap-3 md:grid-cols-2">
            <TextField label="最大重试次数" inputMode="numeric" name="hook-retry-max" value={String(draft.retry.max_attempts)} onChange={(value) => setDraft({ ...draft, retry: { ...draft.retry!, max_attempts: parseNumber(value, draft.retry!.max_attempts) } })} />
            <TextField label="重试间隔（秒）" inputMode="numeric" name="hook-retry-delay" value={String(draft.retry.delay)} onChange={(value) => setDraft({ ...draft, retry: { ...draft.retry!, delay: parseNumber(value, draft.retry!.delay) } })} />
          </div>
        ) : null}
      </FormSection>

      <FormActions errorMessage={firstError(errors)} isDirty={isDirty} isPending={isPending} onReset={() => { setJsonResetVersion((current) => current + 1); setDraft(sanitizeHookDraft(detail)); setErrors({}); }} onSave={() => onSave(draft)} />
    </div>
  );
}

export function McpFormEditor({
  detail,
  isPending,
  onDraftChange,
  onDirtyChange,
  onSave,
}: Readonly<HookMcpCommonProps<McpServerConfigDetail>>) {
  return (
    <McpFormEditorBody
      key={formatConfigRegistryDocument(detail)}
      detail={detail}
      isPending={isPending}
      onDraftChange={onDraftChange}
      onDirtyChange={onDirtyChange}
      onSave={onSave}
    />
  );
}

function McpFormEditorBody({
  detail,
  isPending,
  onDraftChange,
  onDirtyChange,
  onSave,
}: Readonly<HookMcpCommonProps<McpServerConfigDetail>>) {
  const [draft, setDraft] = useState(detail);
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
        <StaticField label="传输协议" value={detail.transport} description="当前后端只支持 streamable_http。" />
        <div className="grid gap-3 md:grid-cols-2">
          <TextField label="名称" name="mcp-name" required value={draft.name} onChange={(value) => setDraft({ ...draft, name: value })} />
          <TextField label="版本" name="mcp-version" required value={draft.version} onChange={(value) => setDraft({ ...draft, version: value })} />
          <TextField label="地址" name="mcp-url" required type="url" value={draft.url} onChange={(value) => setDraft({ ...draft, url: value })} />
          <TextField label="超时（秒）" inputMode="numeric" name="mcp-timeout" value={String(draft.timeout)} onChange={(value) => setDraft({ ...draft, timeout: parseNumber(value, draft.timeout) })} />
        </div>
        <TextAreaField label="描述" name="mcp-description" value={draft.description ?? ""} onChange={(value) => setDraft({ ...draft, description: value || null })} />
        <label className="flex items-center gap-3 text-sm text-[var(--text-primary)]">
          <input checked={draft.enabled} type="checkbox" onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} />
          已启用
        </label>
      </FormSection>

      <JsonTextAreaField emptyValue={{}} label="headers" parseValue={validateStringMap} syncKey={`headers:${jsonResetVersion}`} value={draft.headers} onChange={(value) => setDraft({ ...draft, headers: value })} onErrorChange={(message) => setErrors((current) => updateError(current, "headers", message))} />
      <FormActions errorMessage={firstError(errors)} isDirty={isDirty} isPending={isPending} onReset={() => { setJsonResetVersion((current) => current + 1); setDraft(detail); setErrors({}); }} onSave={() => onSave(draft)} />
    </div>
  );
}

function FormActions({ errorMessage, isDirty, isPending, onReset, onSave }: Readonly<{ errorMessage: string | null; isDirty: boolean; isPending: boolean; onReset: () => void; onSave: () => void; }>) {
  return (
    <div className="space-y-3">
      {errorMessage ? <div className="rounded-2xl bg-[rgba(178,65,46,0.12)] px-4 py-3 text-sm text-[var(--accent-danger)]">{errorMessage}</div> : null}
      <div className="flex flex-wrap gap-2">
        <button className="ink-button" disabled={isPending || !isDirty || Boolean(errorMessage)} type="button" onClick={onSave}>{isPending ? "保存中…" : "保存配置"}</button>
        <button className="ink-button-secondary" disabled={isPending || !isDirty} type="button" onClick={onReset}>还原编辑</button>
      </div>
    </div>
  );
}

function buildCondition(condition: { field: string; operator: string; value: string | number | boolean }) {
  if (!condition.field.trim()) {
    return null;
  }
  return condition;
}

function parseNumber(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function asObject(value: unknown): ConfigRegistryObject {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as ConfigRegistryObject) : {};
}

function asStringMap(value: unknown): Record<string, string> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, string>) : {};
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

function clearHookActionErrors(errors: Record<string, string>): Record<string, string> {
  const next = { ...errors };
  delete next["hook-action"];
  delete next["hook-action-body"];
  delete next["hook-action-mapping"];
  return next;
}

function toSimpleOption(option: { label: string; value: string }) {
  return option;
}
