"use client";

type AssistantMcpRawEditorProps = {
  documentError: string | null;
  documentValue: string;
  mode: "create" | "edit";
  onChange: (value: string) => void;
};

export function AssistantMcpRawEditor({
  documentError,
  documentValue,
  mode,
  onChange,
}: Readonly<AssistantMcpRawEditorProps>) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)]">
      <label className="block space-y-2">
        <span className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium text-text-primary">MCP.yaml</span>
          <span className="text-[12px] leading-5 text-text-secondary">
            按连接文件直接写，保存后就能在 Hooks 里选用。
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
        <div className="rounded-3xl bg-glass shadow-glass px-4 py-4 text-[12px] leading-6 text-text-secondary">
          <p className="text-sm font-medium text-text-primary">文件约定</p>
          <p className="mt-2">当前正式支持的字段是 `name / enabled / version / description / transport / url / headers / timeout`。</p>
          <p className="mt-2">地址、请求头和超时都在这里维护，保存后聊天里的 Hook 会直接读取这份连接。</p>
          {mode === "create" ? (
            <p className="mt-3 rounded-2xl bg-glass px-3 py-2 text-[12px] leading-5 text-text-secondary">
              第一次保存后，系统会自动补上这份 MCP 的 id。
            </p>
          ) : null}
          {documentError ? (
            <p className="mt-3 rounded-2xl bg-accent-danger/10 px-3 py-2 text-[12px] leading-5 text-accent-danger">
              当前文件还没写对，修正后才能保存。
            </p>
          ) : null}
        </div>
        <div className="rounded-3xl bg-glass shadow-glass px-4 py-4 text-[12px] leading-6 text-text-secondary">
          <p className="text-sm font-medium text-text-primary">适合放什么</p>
          <p className="mt-2">适合保存稳定的外部工具连接，比如搜索、资料检索、知识库、抓取接口。</p>
          <p className="mt-2">不建议在这里堆临时参数；临时查询条件更适合在 Hook 的 `arguments` 或 `input_mapping` 里填写。</p>
        </div>
      </div>
    </div>
  );
}
