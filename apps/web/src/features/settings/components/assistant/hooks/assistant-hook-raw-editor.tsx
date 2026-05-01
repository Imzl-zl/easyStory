"use client";

type SelectOption = { label: string; value: string; description?: string };

type AssistantHookRawEditorProps = {
  agentErrorMessage?: string | null;
  agentOptions?: SelectOption[];
  documentError: string | null;
  documentValue: string;
  mode: "create" | "edit";
  mcpErrorMessage?: string | null;
  mcpOptions?: SelectOption[];
  onChange: (value: string) => void;
};

export function AssistantHookRawEditor({
  agentErrorMessage,
  agentOptions,
  documentError,
  documentValue,
  mode,
  mcpErrorMessage,
  mcpOptions,
  onChange,
}: Readonly<AssistantHookRawEditorProps>) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
      <label className="block space-y-2">
        <span className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium text-text-primary">HOOK.yaml</span>
          <span className="text-[12px] leading-5 text-text-secondary">
            按事件和动作来写，保存后立即生效。
          </span>
        </span>
        <textarea
          className="ink-input min-h-[420px] font-mono text-[12px] leading-6"
          spellCheck={false}
          value={documentValue}
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
      <div className="space-y-3">
        <InfoCard title="文件约定">
          <p>当前只支持 `before_assistant_response` 和 `after_assistant_response` 两个事件。</p>
          <p className="mt-2">动作类型只支持 `agent` 或 `mcp`。</p>
          <p className="mt-2">`author / priority / timeout / trigger.node_types` 目前是固定字段，暂不支持自定义。</p>
          {mode === "create" ? (
            <p className="mt-3 rounded-2xl bg-glass px-3 py-2 text-[12px] leading-5 text-text-secondary">
              第一次保存后，系统会自动补上这份 Hook 的 id。
            </p>
          ) : null}
          {documentError ? (
            <p className="mt-3 rounded-2xl bg-accent-danger/10 px-3 py-2 text-[12px] leading-5 text-accent-danger">
              当前文件还没写对，修正后才能保存。
            </p>
          ) : null}
        </InfoCard>
        <ReferenceCard
          emptyText="还没有可选 Agent。"
          errorMessage={agentErrorMessage}
          items={agentOptions}
          title="可用 Agent"
        />
        <ReferenceCard
          emptyText="还没有可选 MCP。"
          errorMessage={mcpErrorMessage}
          items={mcpOptions}
          title="可用 MCP"
        />
      </div>
    </div>
  );
}

function InfoCard({
  children,
  title,
}: Readonly<{ children: React.ReactNode; title: string }>) {
  return (
    <div className="rounded-3xl bg-glass shadow-glass px-4 py-4 text-[12px] leading-6 text-text-secondary">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function ReferenceCard({
  emptyText,
  errorMessage,
  items,
  title,
}: Readonly<{
  emptyText: string;
  errorMessage?: string | null;
  items?: SelectOption[];
  title: string;
}>) {
  return (
    <div className="rounded-3xl bg-glass shadow-glass px-4 py-4">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      {errorMessage ? (
        <p className="mt-3 rounded-2xl bg-accent-danger/10 px-3 py-2 text-[12px] leading-5 text-accent-danger">
          {errorMessage}
        </p>
      ) : null}
      <div className="mt-3 space-y-2">
        {(items ?? []).length === 0 ? (
          <div className="rounded-2xl bg-glass px-3 py-2.5 text-[12px] leading-5 text-text-secondary">
            {emptyText}
          </div>
        ) : (
          (items ?? []).map((item) => (
            <div className="rounded-2xl bg-glass px-3 py-2.5" key={item.value}>
              <p className="text-[12px] font-medium text-text-primary">{item.label}</p>
              <p className="mt-1 break-all font-mono text-[11px] leading-5 text-text-secondary">
                {item.value}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
