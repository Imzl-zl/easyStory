"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { Button, Input, Message, Radio } from "@arco-design/web-react";

import { AppSelect } from "@/components/ui/app-select";
import { renderFloatingPanel, useFloatingPanelStyle } from "@/components/ui/floating-panel-support";
import type {
  DocumentTreeNode,
  StudioChatLayoutMode,
} from "@/features/studio/components/page/studio-page-support";
import { getErrorMessage } from "@/lib/api/client";
import {
  normalizeAssistantThinkingBudgetInput,
  resolveAssistantReasoningControl,
} from "@/features/shared/assistant/assistant-reasoning-support";

import { STUDIO_ATTACHMENT_ACCEPT, type StudioChatAttachmentMeta } from "@/features/studio/components/chat/studio-chat-attachment-support";
import { submitStudioComposerMessage } from "@/features/studio/components/chat/studio-chat-composer-support";
import { StudioChatContextSelectorContent } from "@/features/studio/components/chat/studio-chat-context-selector";
import type { StudioChatSettings, StudioProviderOption } from "@/features/studio/components/chat/studio-chat-support";
import { resolveStudioWriteToggleDisabled } from "@/features/studio/components/chat/studio-chat-write-support";

type StudioChatComposerProps = {
  attachments: StudioChatAttachmentMeta[];
  availableContexts: DocumentTreeNode[];
  canChat: boolean;
  layoutMode?: StudioChatLayoutMode;
  composerText: string;
  credentialNotice: string | null;
  credentialSettingsHref: string;
  isCredentialLoading: boolean;
  isResponding: boolean;
  modelButtonLabel: string;
  onAttachFiles: (files: FileList | null) => void;
  onComposerTextChange: (value: string) => void;
  onModelNameChange: (value: string) => void;
  onProviderChange: (provider: string) => void;
  onReasoningEffortChange: (value: string) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => boolean | Promise<boolean>;
  onStreamOutputChange: (value: boolean) => void;
  onThinkingBudgetChange: (value: string) => void;
  onThinkingLevelChange: (value: string) => void;
  onToggleContext: (path: string) => void;
  onToggleWriteToCurrentDocument: () => void;
  providerOptions: StudioProviderOption[];
  selectedContextPaths: string[];
  selectedCredentialApiDialect: string | null;
  selectedCredentialLabel: string | null;
  settings: Pick<
    StudioChatSettings,
    "modelName" | "provider" | "reasoningEffort" | "streamOutput" | "thinkingBudget" | "thinkingLevel"
  >;
  showWriteToCurrentDocument: boolean;
  writeIntentNotice: string | null;
  writeTargetDisabledReason: string | null;
  isWriteToCurrentDocumentEnabled: boolean;
};

const MODEL_PICKER_PANEL_CLASS =
  "overflow-y-auto rounded-2xl border border-[rgba(44,36,22,0.1)] bg-white/95 p-3.5 shadow-[0_18px_46px_rgba(44,36,22,0.18)] backdrop-blur-sm";
const MODEL_PICKER_PROVIDER_LIST_CLASS =
  "mt-2 grid gap-1 rounded-xl border border-[rgba(44,36,22,0.1)] bg-[rgba(249,247,243,0.92)] p-1 max-h-56 overflow-y-auto";

export function StudioChatComposer({
  attachments,
  availableContexts,
  canChat,
  layoutMode = "default",
  composerText,
  credentialNotice,
  credentialSettingsHref,
  isCredentialLoading,
  isResponding,
  modelButtonLabel,
  onAttachFiles,
  onComposerTextChange,
  onModelNameChange,
  onProviderChange,
  onReasoningEffortChange,
  onRemoveAttachment,
  onSendMessage,
  onStreamOutputChange,
  onThinkingBudgetChange,
  onThinkingLevelChange,
  onToggleContext,
  onToggleWriteToCurrentDocument,
  providerOptions,
  selectedContextPaths,
  selectedCredentialApiDialect,
  selectedCredentialLabel,
  settings,
  showWriteToCurrentDocument,
  writeIntentNotice,
  writeTargetDisabledReason,
  isWriteToCurrentDocumentEnabled,
}: Readonly<StudioChatComposerProps>) {
  const compactLayout = layoutMode !== "default";
  const iconLayout = layoutMode === "icon";
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showProviderList, setShowProviderList] = useState(false);
  const [showContextSelector, setShowContextSelector] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelPickerRef = useRef<HTMLDivElement>(null);
  const modelButtonRef = useRef<HTMLButtonElement>(null);
  const contextSelectorRef = useRef<HTMLDivElement>(null);
  const contextButtonRef = useRef<HTMLButtonElement>(null);
  const modelPickerStyle = useFloatingPanelStyle(showModelPicker, modelButtonRef, {
    align: "right",
    maxHeight: 480,
    preferredWidth: 352,
    side: "top",
  });
  const contextSelectorStyle = useFloatingPanelStyle(showContextSelector, contextButtonRef, {
    align: "left",
    maxHeight: 320,
    preferredWidth: 352,
    side: "top",
  });

  const currentProviderOption = useMemo(
    () =>
      providerOptions.find((option) => option.value === settings.provider)
      ?? providerOptions[0]
      ?? null,
    [providerOptions, settings.provider],
  );
  const reasoningControl = useMemo(
    () =>
      resolveAssistantReasoningControl({
        apiDialect: selectedCredentialApiDialect,
        modelName: settings.modelName || currentProviderOption?.defaultModel,
      }),
    [currentProviderOption?.defaultModel, selectedCredentialApiDialect, settings.modelName],
  );

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target;
      if (target instanceof HTMLElement && target.closest(".arco-trigger-popup")) {
        return;
      }
      if (
        modelPickerRef.current &&
        !modelPickerRef.current.contains(target as Node) &&
        modelButtonRef.current &&
        !modelButtonRef.current.contains(target as Node)
      ) {
        setShowProviderList(false);
        setShowModelPicker(false);
      }
      if (
        contextSelectorRef.current &&
        !contextSelectorRef.current.contains(target as Node) &&
        contextButtonRef.current &&
        !contextButtonRef.current.contains(target as Node)
      ) {
        setShowContextSelector(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleToggleContextSelector = useCallback(() => {
    setShowModelPicker(false);
    setShowProviderList(false);
    setShowContextSelector((visible) => !visible);
  }, []);

  const handleToggleModelPicker = useCallback(() => {
    setShowContextSelector(false);
    setShowProviderList(false);
    setShowModelPicker((visible) => !visible);
  }, []);

  const handleToggleProviderList = useCallback(() => {
    setShowProviderList((visible) => !visible);
  }, []);

  const handleSelectProvider = useCallback((provider: string) => {
    setShowProviderList(false);
    onProviderChange(provider);
  }, [onProviderChange]);

  const handleUnexpectedSendError = useCallback((error: unknown) => {
    console.error("Studio chat composer send failed unexpectedly.", error);
    Message.error(getErrorMessage(error));
  }, []);

  const handleSubmit = useCallback(() => {
    submitStudioComposerMessage({
      canChat,
      composerText,
      isResponding,
      onSendMessage,
      onUnexpectedError: handleUnexpectedSendError,
    });
  }, [canChat, composerText, handleUnexpectedSendError, isResponding, onSendMessage]);

  const handleComposerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
      event.preventDefault();
      handleSubmit();
    },
    [handleSubmit],
  );

  return (
    <div className="relative z-20 shrink-0 border-t border-[rgba(44,36,22,0.08)] bg-gradient-to-b from-[var(--bg-surface)] to-[rgba(248,243,235,0.92)]">
      <div className="relative z-20 px-3 py-2.5">
        {credentialNotice ? (
          <div className="mb-2 flex flex-wrap items-center gap-2 rounded-lg bg-[rgba(178,65,46,0.08)] px-3 py-2 text-sm text-[var(--accent-danger)]">
            <p className="min-w-0 flex-1">{credentialNotice}</p>
            <Link className="inline-flex items-center gap-1 font-medium underline underline-offset-2 hover:no-underline" href={credentialSettingsHref}>
              模型连接
              <JumpLinkIcon />
            </Link>
          </div>
        ) : null}

        {attachments.length > 0 ? (
          <div className="mb-1.5 flex flex-wrap gap-1.5">
            {attachments.map((attachment) => (
              <button
                className="inline-flex items-center gap-1.5 h-6 px-2 rounded-md bg-[rgba(107,143,113,0.12)] text-xs text-[var(--text-primary)] hover:bg-[rgba(107,143,113,0.2)] transition-colors"
                key={attachment.id}
                type="button"
                onClick={() => onRemoveAttachment(attachment.id)}
              >
                <span className="truncate max-w-[120px]">{attachment.name}</span>
                <span className="opacity-60 hover:opacity-100">×</span>
              </button>
            ))}
          </div>
        ) : null}

        <Input.TextArea
          autoSize={{ maxRows: 5, minRows: 2 }}
          className="w-full text-sm leading-relaxed resize-none border border-[rgba(44,36,22,0.1)] rounded-lg bg-white/80 focus:border-[var(--accent-primary)] focus:shadow-[0_0_0_3px_rgba(107,143,113,0.12)] transition-all placeholder:text-[var(--text-muted)]"
          placeholder={canChat ? "写你的要求，或直接带文件进来一起改。" : "先启用可用模型后再开始提问"}
          value={composerText}
          onChange={onComposerTextChange}
          onKeyDown={handleComposerKeyDown}
        />

        <div className={`mt-1.5 flex gap-2 ${compactLayout ? "flex-col items-stretch" : "items-start justify-between"}`}>
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
            <ToolbarIconButton label="上传文件" onClick={() => fileInputRef.current?.click()}>
              <PaperclipIcon />
            </ToolbarIconButton>

            <div className="relative">
              <ToolbarChipButton
                active={showContextSelector}
                badge={selectedContextPaths.length > 0 ? String(selectedContextPaths.length) : null}
                iconOnly={iconLayout}
                label={`上下文 ${selectedContextPaths.length}`}
                onClick={handleToggleContextSelector}
                buttonRef={contextButtonRef}
              >
                <ContextIcon />
              </ToolbarChipButton>

              {showContextSelector ? renderFloatingPanel(
                <StudioChatContextSelectorContent
                  availableContexts={availableContexts}
                  onToggleContext={onToggleContext}
                  panelRef={contextSelectorRef}
                  panelStyle={contextSelectorStyle}
                  selectedContextPaths={selectedContextPaths}
                />,
              ) : null}
            </div>

            <div className="relative">
              <ToolbarChipButton
                active={showModelPicker}
                label={modelButtonLabel}
                onClick={handleToggleModelPicker}
                buttonRef={modelButtonRef}
              >
                <SparkIcon />
              </ToolbarChipButton>

              {showModelPicker ? renderFloatingPanel(
                <div
                  className={MODEL_PICKER_PANEL_CLASS}
                  ref={modelPickerRef}
                  style={modelPickerStyle}
                >
                  <div className="mb-3">
                    <p className="text-sm font-medium text-[var(--text-primary)]">切换模型</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      {selectedCredentialLabel ?? "先选可用渠道，再决定模型名。"}
                    </p>
                  </div>
                  <label className="grid gap-1.5">
                    <span className="text-xs font-medium text-[var(--text-secondary)]">渠道</span>
                    <div className="relative">
                      <button
                        aria-expanded={showProviderList}
                        className="flex min-h-10 w-full items-center justify-between gap-3 rounded-xl border border-[rgba(44,36,22,0.1)] bg-white/92 px-3 py-2.5 text-left text-sm text-[var(--text-primary)] transition-colors hover:border-[rgba(107,143,113,0.3)] focus:outline-none focus:ring-2 focus:ring-[rgba(107,143,113,0.18)]"
                        type="button"
                        onClick={handleToggleProviderList}
                      >
                        <span className="min-w-0 flex-1 truncate font-medium">
                          {currentProviderOption?.label ?? (isCredentialLoading ? "正在读取渠道..." : "选择可用渠道")}
                        </span>
                        <span className={`shrink-0 text-[10px] opacity-60 transition-transform ${showProviderList ? "rotate-180" : ""}`}>⌄</span>
                      </button>
                      {showProviderList ? (
                        <div className={MODEL_PICKER_PROVIDER_LIST_CLASS}>
                          {providerOptions.length > 0 ? (
                            providerOptions.map((option) => {
                              const selected = option.value === settings.provider;
                              return (
                                <button
                                  className={`flex w-full flex-col items-start gap-1 rounded-lg px-3 py-2.5 text-left transition-colors ${selected ? "bg-[rgba(107,143,113,0.12)] text-[var(--accent-primary)]" : "text-[var(--text-primary)] hover:bg-[rgba(107,143,113,0.06)]"}`}
                                  key={option.value}
                                  type="button"
                                  onMouseDown={(event) => {
                                    event.preventDefault();
                                    handleSelectProvider(option.value);
                                  }}
                                >
                                  <span className="text-sm font-medium leading-relaxed">{option.label}</span>
                                  {option.description ? (
                                    <span className="text-xs leading-relaxed text-[var(--text-muted)]">{option.description}</span>
                                  ) : null}
                                </button>
                              );
                            })
                          ) : (
                            <p className="px-3 py-3 text-sm text-[var(--text-muted)]">
                              {isCredentialLoading ? "正在读取渠道..." : "当前没有可用渠道"}
                            </p>
                          )}
                        </div>
                      ) : null}
                    </div>
                  </label>
                  <label className="mt-3 grid gap-1.5">
                    <span className="text-xs font-medium text-[var(--text-secondary)]">模型</span>
                    <Input
                      allowClear
                      autoComplete="off"
                      placeholder="留空则跟随当前渠道默认模型"
                      spellCheck={false}
                      value={settings.modelName}
                      onChange={onModelNameChange}
                    />
                  </label>
                  <div className="mt-3 rounded-[14px] border border-[rgba(44,36,22,0.08)] bg-[rgba(249,247,243,0.92)] px-3 py-2.5">
                    <p className="m-0 text-[12px] font-medium text-[var(--text-primary)]">{reasoningControl.title}</p>
                    <p className="mt-1 text-[11px] leading-4 text-[var(--text-secondary)]">{reasoningControl.description}</p>
                    {reasoningControl.kind === "gemini_budget" ? (
                      <div className="mt-2.5 space-y-2">
                        <div className="flex flex-wrap gap-2">
                          <ReasoningChipButton
                            active={settings.thinkingBudget === ""}
                            label="跟随默认"
                            onClick={() => onThinkingBudgetChange("")}
                          />
                          {reasoningControl.allowDisable ? (
                            <ReasoningChipButton
                              active={settings.thinkingBudget === "0"}
                              label="关闭思考"
                              onClick={() => onThinkingBudgetChange("0")}
                            />
                          ) : null}
                          {reasoningControl.allowDynamic ? (
                            <ReasoningChipButton
                              active={settings.thinkingBudget === "-1"}
                              label="动态思考"
                              onClick={() => onThinkingBudgetChange("-1")}
                            />
                          ) : null}
                        </div>
                        <Input
                          allowClear
                          autoComplete="off"
                          inputMode="numeric"
                          placeholder={reasoningControl.placeholder}
                          spellCheck={false}
                          value={settings.thinkingBudget}
                          onChange={(value) => onThinkingBudgetChange(normalizeAssistantThinkingBudgetInput(value))}
                        />
                      </div>
                    ) : reasoningControl.kind === "none" ? null : (
                      <div className="mt-2.5">
                        <AppSelect
                          ariaLabel={reasoningControl.title}
                          className="min-w-0"
                          options={reasoningControl.options}
                          value={reasoningControl.kind === "openai" ? settings.reasoningEffort : settings.thinkingLevel}
                          onChange={(value) =>
                            reasoningControl.kind === "openai"
                              ? onReasoningEffortChange(value)
                              : onThinkingLevelChange(value)}
                        />
                      </div>
                    )}
                  </div>
                  <div className="mt-3 rounded-[14px] border border-[rgba(44,36,22,0.08)] bg-[rgba(249,247,243,0.92)] px-3 py-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="m-0 text-[12px] font-medium text-[var(--text-primary)]">回复显示方式</p>
                        <p className="m-0 text-[11px] leading-4 text-[var(--text-secondary)]">仅当前项目聊天生效</p>
                      </div>
                      <Radio.Group
                        aria-label="回复显示方式"
                        mode="fill"
                        size="small"
                        type="button"
                        value={settings.streamOutput ? "stream" : "buffered"}
                        onChange={(value) => onStreamOutputChange(value === "stream")}
                      >
                        <Radio value="stream">边写边显示</Radio>
                        <Radio value="buffered">生成后整体显示</Radio>
                      </Radio.Group>
                    </div>
                  </div>
                </div>,
              ) : null}
            </div>

            {showWriteToCurrentDocument ? (
              <ToolbarToggleButton
                active={isWriteToCurrentDocumentEnabled}
                disabled={resolveStudioWriteToggleDisabled({
                  enabled: isWriteToCurrentDocumentEnabled,
                  writeTargetDisabledReason,
                })}
                iconOnly={iconLayout}
                label={isWriteToCurrentDocumentEnabled ? "本轮改当前稿" : "改当前稿"}
                title={writeTargetDisabledReason ?? "显式开启后，助手本轮才可改写当前文稿。"}
                onClick={onToggleWriteToCurrentDocument}
              >
                <WriteIcon />
              </ToolbarToggleButton>
            ) : null}
          </div>

          <Button
            className={compactLayout ? "w-full" : "shrink-0"}
            disabled={!canChat || isResponding}
            loading={isResponding}
            shape="round"
            type="primary"
            onClick={handleSubmit}
          >
            发送
          </Button>
        </div>

        {writeIntentNotice ? (
          <p className={`mt-1.5 px-1 text-[11px] leading-4 ${isWriteToCurrentDocumentEnabled ? "text-[var(--accent-primary)]" : "text-[var(--text-muted)]"}`}>
            {writeIntentNotice}
          </p>
        ) : null}

        <input
          accept={STUDIO_ATTACHMENT_ACCEPT}
          className="hidden"
          ref={fileInputRef}
          type="file"
          multiple
          onChange={(e) => onAttachFiles(e.target.files)}
        />
      </div>
    </div>
  );
}

function ReasoningChipButton({
  active,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      className={`rounded-full border px-3 py-1 text-[11px] transition ${
        active
          ? "border-[rgba(107,143,113,0.28)] bg-[rgba(107,143,113,0.12)] text-[var(--accent-primary)]"
          : "border-[rgba(44,36,22,0.1)] bg-white/92 text-[var(--text-secondary)] hover:border-[rgba(107,143,113,0.24)]"
      }`}
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function ToolbarIconButton({
  children,
  label,
  onClick,
}: {
  children: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button aria-label={label} className="flex h-[30px] w-[30px] items-center justify-center rounded-lg text-[var(--text-secondary)] transition-colors hover:bg-[rgba(107,143,113,0.1)] hover:text-[var(--text-primary)]" type="button" onClick={onClick}>
      {children}
    </button>
  );
}

function ToolbarChipButton({
  active = false,
  badge = null,
  children,
  iconOnly = false,
  label,
  onClick,
  buttonRef,
}: {
  active?: boolean;
  badge?: string | null;
  children: ReactNode;
  iconOnly?: boolean;
  label: string;
  onClick: () => void;
  buttonRef?: React.Ref<HTMLButtonElement>;
}) {
  return (
    <button
      ref={buttonRef}
      aria-label={label}
      className={`relative inline-flex h-[26px] min-w-0 max-w-full items-center rounded-lg text-[11px] font-medium transition-colors ${active ? "bg-[rgba(107,143,113,0.15)] text-[var(--accent-primary)]" : "bg-[rgba(44,36,22,0.05)] text-[var(--text-secondary)] hover:bg-[rgba(107,143,113,0.1)]"} ${iconOnly ? "w-[30px] justify-center px-0" : "gap-1.5 px-2.5"}`}
      title={label}
      type="button"
      onClick={onClick}
    >
      <span className="opacity-70">{children}</span>
      {!iconOnly ? <span className="min-w-0 truncate">{label}</span> : null}
      {!iconOnly ? <span className="opacity-50 text-[10px]">⌄</span> : null}
      {iconOnly && badge ? (
        <span className="absolute -right-1 -top-1 inline-flex min-w-4 items-center justify-center rounded-full bg-[var(--accent-primary)] px-1 text-[9px] leading-4 text-white">
          {badge}
        </span>
      ) : null}
    </button>
  );
}

function ToolbarToggleButton({
  active = false,
  children,
  disabled = false,
  iconOnly = false,
  label,
  onClick,
  title,
}: {
  active?: boolean;
  children: ReactNode;
  disabled?: boolean;
  iconOnly?: boolean;
  label: string;
  onClick: () => void;
  title?: string;
}) {
  return (
    <button
      aria-pressed={active}
      aria-label={label}
      className={`inline-flex h-[26px] min-w-0 max-w-full items-center rounded-lg text-[11px] font-medium transition-colors ${
        disabled
          ? "cursor-not-allowed bg-[rgba(44,36,22,0.04)] text-[rgba(44,36,22,0.35)]"
          : active
            ? "bg-[rgba(107,143,113,0.16)] text-[var(--accent-primary)]"
            : "bg-[rgba(44,36,22,0.05)] text-[var(--text-secondary)] hover:bg-[rgba(107,143,113,0.1)]"
      } ${iconOnly ? "w-[30px] justify-center px-0" : "gap-1.5 px-2.5"}`}
      disabled={disabled}
      title={title ?? label}
      type="button"
      onClick={onClick}
    >
      <span className="opacity-70">{children}</span>
      {!iconOnly ? <span className="min-w-0 truncate">{label}</span> : null}
    </button>
  );
}

function JumpLinkIcon() {
  return (
    <svg aria-hidden="true" fill="none" height="14" viewBox="0 0 16 16" width="14">
      <path
        d="M6 4h6v6m-1-5-6.5 6.5M4 7.5V12h4.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function PaperclipIcon() {
  return <ComposerIcon path="M9.5 18.5 15.4 12.6a3 3 0 0 0-4.2-4.2l-6.3 6.3a4.5 4.5 0 0 0 6.4 6.4l6.7-6.7" />;
}

function ContextIcon() {
  return <ComposerIcon path="M7 17h10M6 7.5h12l-1 9H7l-1-9Zm4-3h4" />;
}

function SparkIcon() {
  return <ComposerIcon path="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3Zm6 11 .7 2.3L21 17l-2.3.7L18 20l-.7-2.3L15 17l2.3-.7L18 14Z" />;
}

function WriteIcon() {
  return <ComposerIcon path="M5 19.2 5.7 15l8.9-8.9a1.8 1.8 0 0 1 2.5 0l1 1a1.8 1.8 0 0 1 0 2.5L9.2 18.5 5 19.2Zm7.1-11.4 3.7 3.7" />;
}

function ComposerIcon({ path }: { path: string }) {
  return (
    <svg aria-hidden="true" fill="none" height="16" viewBox="0 0 24 24" width="16">
      <path d={path} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
    </svg>
  );
}
