"use client";

import { createPortal } from "react-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode, RefObject } from "react";

import { observeFloatingPanelLayoutChanges } from "@/components/ui/floating-panel-support";
import {
  filterStudioChatSkillOptions,
  type StudioChatSkillOption,
} from "@/features/studio/components/chat/studio-chat-skill-support";
import type { StudioChatSkillModel } from "@/features/studio/components/chat/studio-chat-skill-model";
import type { StudioChatLayoutMode } from "@/features/studio/components/page/studio-page-support";

type StudioChatSkillPanelProps = {
  layoutMode?: StudioChatLayoutMode;
  disabled?: boolean;
  isOpen: boolean;
  model: StudioChatSkillModel;
  onOpenChange: (open: boolean) => void;
};

type SkillDrawerLayout = {
  backdropStyle: CSSProperties;
  panelStyle: CSSProperties;
};

export function StudioChatSkillPanel({
  layoutMode = "default",
  disabled = false,
  isOpen,
  model,
  onOpenChange,
}: Readonly<StudioChatSkillPanelProps>) {
  const compactLayout = layoutMode !== "default";
  const [layout, setLayout] = useState<SkillDrawerLayout | null>(null);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const filteredSkillOptions = useMemo(
    () => filterStudioChatSkillOptions(model.skillOptions, query),
    [model.skillOptions, query],
  );
  const closeDrawer = useCallback(() => {
    onOpenChange(false);
    setQuery("");
  }, [onOpenChange]);
  const updateLayout = useCallback(() => {
    setLayout(resolveSkillDrawerLayout(containerRef.current));
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeDrawer();
      }
    }

    updateLayout();
    const frameId = window.requestAnimationFrame(() => searchInputRef.current?.focus());
    const cleanupLayoutObserver = observeFloatingPanelLayoutChanges(containerRef.current, updateLayout);
    document.addEventListener("keydown", handleEscape);
    return () => {
      window.cancelAnimationFrame(frameId);
      cleanupLayoutObserver();
      document.removeEventListener("keydown", handleEscape);
    };
  }, [closeDrawer, isOpen, updateLayout]);

  return (
    <div className={`relative min-w-0 shrink-0 ${compactLayout ? "w-full max-w-none" : "max-w-[152px]"}`} ref={containerRef}>
      <button
        aria-expanded={isOpen}
        className={`group flex h-[30px] min-w-0 items-center gap-2 rounded-full px-3 text-left transition-[background-color,box-shadow] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/15 disabled:cursor-not-allowed disabled:opacity-60 ${compactLayout ? "w-full max-w-none" : "min-w-[132px] max-w-[152px]"} ${
          isOpen
            ? "bg-surface shadow-md"
            : "bg-surface shadow-xs hover:shadow-sm"
        }`}
        disabled={disabled}
        title={model.skillState.headline}
        type="button"
        onClick={() => {
          if (isOpen) {
            closeDrawer();
            return;
          }
          setQuery("");
          onOpenChange(true);
        }}
      >
        <span className="inline-flex shrink-0 items-center rounded-full bg-muted px-2 py-0.5 text-[10px] leading-4 text-text-secondary">
          Skill
        </span>
        <span className="min-w-0 flex-1 truncate text-[12px] font-medium leading-5 text-text-primary">
          {resolveTriggerLabel(model.skillState.headline)}
        </span>
        <span
          aria-hidden="true"
          className={`shrink-0 text-[10px] text-text-secondary transition-transform ${isOpen ? "rotate-180" : ""}`}
        >
          ▾
        </span>
      </button>
      {isOpen && layout ? createPortal(
        <>
          {/* 遮罩层 */}
          <button
            aria-label="关闭 Skill 面板"
            className="chat-panel-overlay"
            type="button"
            onClick={closeDrawer}
          />
          <SkillDrawer
            disabled={disabled}
            filteredSkillOptions={filteredSkillOptions}
            layout={layout}
            model={model}
            onClose={closeDrawer}
            query={query}
            searchInputRef={searchInputRef}
            setQuery={setQuery}
          />
        </>,
        document.body,
      ) : null}
    </div>
  );
}

type SkillDrawerProps = {
  disabled: boolean;
  filteredSkillOptions: StudioChatSkillOption[];
  layout: SkillDrawerLayout;
  model: StudioChatSkillModel;
  onClose: () => void;
  query: string;
  searchInputRef: RefObject<HTMLInputElement | null>;
  setQuery: (value: string) => void;
};

function SkillDrawer({
  disabled,
  filteredSkillOptions,
  layout,
  model,
  onClose,
  query,
  searchInputRef,
  setQuery,
}: Readonly<SkillDrawerProps>) {
  const resultSummary = buildResultSummary(filteredSkillOptions.length, model.skillOptions.length, query);

  return (
    <section
      aria-label="选择 Skill"
      className="chat-skill-panel"
      role="dialog"
      style={layout.panelStyle}
    >
      <div className="shrink-0 border-b border-line-soft px-3 pb-2 pt-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="m-0 text-[10px] font-medium tracking-[0.08em] text-text-secondary">Skill 模式</p>
            <h3 className="mt-1 text-[13px] font-semibold leading-5 text-text-primary">
              这轮对话怎么套 Skill
            </h3>
            <p className="mt-0.5 text-[10.5px] leading-4 text-text-secondary">
              {resultSummary}
            </p>
          </div>
          <button
            className="chat-panel-header__close"
            type="button"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <CurrentModeCard disabled={disabled} model={model} onClose={onClose} />
      </div>

      <div className="shrink-0 border-b border-line-soft px-3 py-2">
        <label className="block">
          <span className="sr-only">筛选 Skill</span>
          <input
            className="chat-panel-search"
            placeholder="按名称、描述或作用域筛选 Skill"
            ref={searchInputRef}
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2">
        {model.skillErrorMessage ? (
          <StateNotice tone="danger">
            {model.skillErrorMessage}
          </StateNotice>
        ) : null}
        {model.skillsLoading ? (
          <StateNotice>
            正在读取可用 Skill…
          </StateNotice>
        ) : null}
        {!model.skillErrorMessage && !model.skillsLoading && model.skillOptions.length === 0 ? (
          <StateNotice>
            当前还没有可直接套用的项目或全局 Skill。
          </StateNotice>
        ) : null}
        {!model.skillErrorMessage && !model.skillsLoading && model.skillOptions.length > 0 && filteredSkillOptions.length === 0 ? (
          <StateNotice>
            没找到和“{query.trim()}”匹配的 Skill，可以换个关键词再试。
          </StateNotice>
        ) : null}
        {!model.skillErrorMessage && !model.skillsLoading && filteredSkillOptions.length > 0 ? (
          <ul className="space-y-2">
            {filteredSkillOptions.map((option) => (
              <SkillOptionCard
                disabled={disabled}
                key={option.value}
                model={model}
                option={option}
                onClose={onClose}
              />
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

function CurrentModeCard({
  disabled,
  model,
  onClose,
}: Readonly<{
  disabled: boolean;
  model: StudioChatSkillModel;
  onClose: () => void;
}>) {
  return (
    <div className="mt-2 rounded-2xl bg-[var(--bg-panel-warm-gradient)] shadow-sm px-3 py-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="m-0 text-[10px] font-medium tracking-[0.08em] text-text-secondary">当前模式</p>
          <p className="mt-1 text-[12px] font-semibold leading-5 text-text-primary">
            {model.skillState.headline}
          </p>
          {model.skillState.detail ? (
            <p className="mt-1 text-[10.5px] leading-4 text-text-secondary">
              {model.skillState.detail}
            </p>
          ) : null}
        </div>
        <button
          className={`inline-flex h-7 shrink-0 items-center rounded-full border px-2.5 text-[10.5px] font-medium transition ${
            isPlainChatMode(model)
              ? "border-accent-primary-muted bg-accent-primary-soft text-accent-primary"
              : "bg-surface shadow-xs text-text-secondary hover:shadow-sm hover:text-text-primary"
          }`}
          disabled={disabled}
          type="button"
          onClick={() => {
            model.resetToPlainChat();
            onClose();
          }}
        >
          普通对话
        </button>
      </div>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {model.skillState.nextTurnSkillId ? (
          <button
            className={DRAWER_ACTION_BUTTON_CLASS}
            disabled={disabled}
            type="button"
            onClick={() => {
              model.clearNextTurnSkill();
              onClose();
            }}
          >
            清除本次 Skill
          </button>
        ) : null}
        {model.skillState.conversationSkillId ? (
          <button
            className={DRAWER_ACTION_BUTTON_CLASS}
            disabled={disabled}
            type="button"
            onClick={() => {
              model.clearConversationSkill();
              onClose();
            }}
          >
            清除会话 Skill
          </button>
        ) : null}
      </div>
    </div>
  );
}

function SkillOptionCard({
  disabled,
  model,
  onClose,
  option,
}: Readonly<{
  disabled: boolean;
  model: StudioChatSkillModel;
  onClose: () => void;
  option: StudioChatSkillOption;
}>) {
  const nextSelected = option.value === model.skillState.nextTurnSkillId;
  const conversationSelected = option.value === model.skillState.conversationSkillId;
  const hasActiveMode = nextSelected || conversationSelected;

  return (
    <li>
      <div
        className={`rounded-2xl border px-3 py-2 transition ${
          hasActiveMode
            ? "border-accent-primary-muted bg-[var(--chat-skill-option-active-bg)] shadow-sm"
            : "bg-[var(--chat-skill-panel-bg)] shadow-xs"
        }`}
      >
        <div className="min-w-0">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[12px] font-semibold leading-5 text-text-primary">
                {option.label}
              </span>
              <span className="inline-flex items-center rounded-full bg-surface px-2 py-0.5 text-[10px] leading-4 text-text-secondary">
                {option.scopeLabel}
              </span>
              {nextSelected ? (
                <span className="inline-flex items-center rounded-full bg-accent-primary/10 px-2 py-0.5 text-[10px] leading-4 text-accent-primary">
                  本次
                </span>
              ) : null}
              {conversationSelected ? (
                <span className="inline-flex items-center rounded-full bg-accent-warning/15 px-2 py-0.5 text-[10px] leading-4 text-accent-tertiary">
                  会话
                </span>
              ) : null}
            </div>
            {option.description ? (
              <p className="mt-1.5 line-clamp-2 text-[10.5px] leading-4 text-text-secondary">
                {option.description}
              </p>
            ) : (
              <p className="mt-1.5 text-[10.5px] leading-4 text-text-tertiary">
                这个 Skill 没有补充说明，适合你已经熟悉它的用途时直接套用。
              </p>
            )}
          </div>
          <div className="mt-2 flex justify-end gap-1.5">
            <button
              className={resolveModeButtonClassName(nextSelected)}
              disabled={disabled}
              type="button"
              onClick={() => {
                model.useSkillOnce(option.value);
                onClose();
              }}
            >
              {nextSelected ? "本次中" : "本次"}
            </button>
            <button
              className={resolveModeButtonClassName(conversationSelected)}
              disabled={disabled}
              type="button"
              onClick={() => {
                model.useSkillForConversation(option.value);
                onClose();
              }}
            >
              {conversationSelected ? "会话中" : "会话"}
            </button>
          </div>
        </div>
      </div>
    </li>
  );
}

function StateNotice({
  children,
  tone = "muted",
}: Readonly<{
  children: ReactNode;
  tone?: "danger" | "muted";
}>) {
  return (
    <div
      className={`rounded-2xl px-3 py-2.5 text-[11px] leading-5 ${
        tone === "danger"
          ? "bg-accent-danger/10 text-accent-danger"
          : "bg-muted text-text-secondary"
      }`}
    >
      {children}
    </div>
  );
}

function resolveSkillDrawerLayout(container: HTMLDivElement | null): SkillDrawerLayout | null {
  if (!container) {
    return null;
  }
  const chatPanel = container?.closest("aside");
  if (!(chatPanel instanceof HTMLElement)) {
    return null;
  }
  const rect = chatPanel.getBoundingClientRect();
  const triggerRect = container.getBoundingClientRect();
  const gutter = rect.width > 460 ? 14 : 10;
  const panelWidth = Math.min(320, Math.max(rect.width - gutter * 2 - 44, 248));
  const panelLeft = Math.max(
    rect.left + gutter,
    Math.min(triggerRect.left, rect.right - gutter - panelWidth),
  );
  const panelTop = Math.max(rect.top + gutter, triggerRect.bottom + 6);
  const panelHeight = Math.max(Math.min(rect.bottom - panelTop - gutter, 520), 240);

  return {
    backdropStyle: {
      height: Math.max(rect.bottom - panelTop, 0),
      left: rect.left,
      position: "fixed",
      top: panelTop,
      width: rect.width,
      zIndex: 165,
    },
    panelStyle: {
      height: panelHeight,
      left: panelLeft,
      position: "fixed",
      top: panelTop,
      width: panelWidth,
      zIndex: 170,
    },
  };
}

function buildResultSummary(visibleCount: number, totalCount: number, query: string) {
  if (!query.trim()) {
    return `共 ${totalCount} 个可用 Skill，点一下就能从侧边套用。`;
  }
  return `筛到 ${visibleCount} / ${totalCount} 个 Skill，可以继续缩小范围后再套用。`;
}

const DRAWER_ACTION_BUTTON_CLASS =
  "inline-flex h-7 items-center rounded-full bg-surface shadow-xs px-2.5 text-[10.5px] text-text-secondary transition hover:shadow-sm hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-60";

function isPlainChatMode(model: StudioChatSkillModel) {
  return model.skillState.conversationSkillId === null && model.skillState.nextTurnSkillId === null;
}

function resolveModeButtonClassName(active: boolean) {
  return `inline-flex h-7 items-center justify-center rounded-full px-2.5 text-[10.5px] font-medium transition ${
    active
      ? "bg-accent-primary-soft text-accent-primary"
      : "bg-surface text-text-secondary hover:bg-surface hover:text-text-primary"
  }`;
}

function resolveTriggerLabel(headline: string) {
  if (headline.startsWith("当前会话 · ")) {
    return `会话 · ${headline.slice("当前会话 · ".length)}`;
  }
  return headline;
}
