"use client";

import Link from "next/link";
import { Tag } from "@arco-design/web-react";

import { getErrorMessage } from "@/lib/api/client";

import {
  AgentSelectField,
  HookSelectionField,
  ProviderSelectField,
  SkillSelectField,
} from "@/features/lobby/components/incubator/incubator-chat-settings-fields";
import type { IncubatorChatModel } from "@/features/lobby/components/incubator/incubator-page-model";
import { resolveIncubatorAgentId, resolveIncubatorHookIds } from "@/features/lobby/components/incubator/incubator-chat-support";

type SelectOption = { label: string; value: string; description?: string };

type ChatCapabilitiesPanelProps = {
  agentOptions: SelectOption[];
  agentQueryError: unknown;
  hookOptions: SelectOption[];
  hookQueryError: unknown;
  model: IncubatorChatModel;
  skillOptions: SelectOption[];
  skillQueryError: unknown;
};

export function ChatCapabilitiesPanel({
  agentOptions,
  agentQueryError,
  hookOptions,
  hookQueryError,
  model,
  skillOptions,
  skillQueryError,
}: Readonly<ChatCapabilitiesPanelProps>) {
  const hasSelectedAgent = Boolean(resolveIncubatorAgentId(model.settings.agentId));
  const selectedHookCount = resolveIncubatorHookIds(model.settings.hookIds).length;

  return (
    <>
      <section className="rounded-[16px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.58)] px-3 py-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[12px] font-medium text-[var(--text-primary)]">先从这里开始</p>
            <p className="mt-1 text-[11px] leading-5 text-[var(--text-secondary)]">
              大多数时候，只要选一个 Skill 和模型连接就够了。
            </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SettingsLink href="/workspace/lobby/settings?tab=skills">Skills</SettingsLink>
          <SettingsLink href="/workspace/lobby/settings?tab=credentials">模型连接</SettingsLink>
        </div>
        </div>
        <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <SkillSelectField model={model} disabled={hasSelectedAgent} options={skillOptions} />
          <ProviderSelectField model={model} />
        </div>
        <p className="mt-3 rounded-[14px] bg-[rgba(255,255,255,0.72)] px-3 py-2 text-[11px] leading-5 text-[var(--text-secondary)]">
          如果你只是想直接聊天，保持这里的默认值就可以。
        </p>
        {hasSelectedAgent ? (
          <p className="mt-3 rounded-[14px] bg-[rgba(46,111,106,0.08)] px-3 py-2 text-[11px] leading-5 text-[var(--accent-ink)]">
            你已经在“高级能力”里切换了 Agent，它会优先使用自己绑定的 Skill。
          </p>
        ) : null}
        {skillQueryError ? (
          <p className="mt-3 rounded-[14px] bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[11px] leading-5 text-[var(--accent-danger)]">
            {getErrorMessage(skillQueryError)}
          </p>
        ) : null}
      </section>

      <details className="overflow-hidden rounded-[16px] border border-[rgba(101,92,82,0.1)] bg-[rgba(255,255,255,0.74)]">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2.5 text-[12px] font-medium text-[var(--text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] focus-visible:ring-inset">
          <span>更多能力</span>
          <Tag
            bordered={false}
            className="!m-0 !rounded-full !bg-[rgba(248,243,235,0.92)] !px-2.5 !py-1 !text-[10.5px] !leading-4 !text-[var(--text-secondary)]"
            size="small"
          >
            {hasSelectedAgent ? "已选 Agent" : "未选 Agent"} · Hooks {selectedHookCount}
          </Tag>
        </summary>
        <div className="space-y-3 border-t border-[var(--line-soft)] px-3 py-3">
          <p className="text-[11px] leading-5 text-[var(--text-secondary)]">
            想固定助手角色、自动整理回复，或者连接外部工具时，再来这里配置。
          </p>
          <div className="flex flex-wrap gap-2">
            <SettingsLink href="/workspace/lobby/settings?tab=agents">Agents</SettingsLink>
            <SettingsLink href="/workspace/lobby/settings?tab=hooks">Hooks</SettingsLink>
            <SettingsLink href="/workspace/lobby/settings?tab=mcp">MCP</SettingsLink>
          </div>
          <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <AgentSelectField model={model} options={agentOptions} />
            <div className="rounded-[14px] border border-[rgba(101,92,82,0.1)] bg-[rgba(248,243,235,0.6)] px-3 py-3">
              <p className="text-[12px] font-medium text-[var(--text-primary)]">自动动作</p>
              <p className="mt-1 text-[11px] leading-5 text-[var(--text-secondary)]">
                需要时可以在回复前后自动多做一步，不用每次手动说明。
              </p>
              {hookOptions.length > 0 ? (
                <div className="mt-3">
                  <HookSelectionField hookOptions={hookOptions} model={model} />
                </div>
              ) : (
                <p className="mt-3 rounded-[14px] bg-[rgba(255,255,255,0.78)] px-3 py-2 text-[11px] leading-5 text-[var(--text-secondary)]">
                  你还没有可用的 Hooks，先去设置页创建一个。
                </p>
              )}
            </div>
          </div>
          {agentQueryError ? (
            <p className="rounded-[14px] bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[11px] leading-5 text-[var(--accent-danger)]">
              {getErrorMessage(agentQueryError)}
            </p>
          ) : null}
          {hookQueryError ? (
            <p className="rounded-[14px] bg-[rgba(178,65,46,0.08)] px-3 py-2 text-[11px] leading-5 text-[var(--accent-danger)]">
              {getErrorMessage(hookQueryError)}
            </p>
          ) : null}
        </div>
      </details>
    </>
  );
}

function SettingsLink({
  children,
  href,
}: Readonly<{
  children: React.ReactNode;
  href: string;
}>) {
  return (
    <Link
      className="inline-flex items-center justify-center rounded-full border border-[var(--line-soft)] bg-[rgba(255,255,255,0.82)] px-3 py-1.5 text-[12px] font-medium text-[var(--accent-ink)] transition hover:bg-[rgba(46,111,106,0.08)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(46,111,106,0.16)] focus-visible:ring-offset-2 focus-visible:ring-offset-[rgba(255,255,255,0.74)]"
      href={href}
    >
      {children}
    </Link>
  );
}
