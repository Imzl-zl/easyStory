"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { Button, Checkbox, Input, Radio } from "@arco-design/web-react";

import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

import { STUDIO_ATTACHMENT_ACCEPT, type StudioChatAttachmentMeta } from "./studio-chat-attachment-support";
import type { StudioChatSettings, StudioProviderOption } from "./studio-chat-support";
import { buildStudioComposerHint } from "./studio-chat-ui-support";

type StudioChatComposerProps = {
  attachments: StudioChatAttachmentMeta[];
  availableContexts: DocumentTreeNode[];
  canChat: boolean;
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
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => void;
  onStreamOutputChange: (value: boolean) => void;
  onToggleContext: (path: string) => void;
  providerOptions: StudioProviderOption[];
  selectedContextPaths: string[];
  selectedCredentialLabel: string | null;
  settings: Pick<StudioChatSettings, "modelName" | "provider" | "streamOutput">;
};

const MODEL_PICKER_PANEL_CLASS =
  "absolute bottom-full right-0 z-40 mb-2 w-[min(22rem,calc(100vw-2rem))] max-h-[min(30rem,calc(100vh-4.5rem))] max-w-[calc(100vw-2rem)] overflow-y-auto rounded-2xl border border-[rgba(44,36,22,0.1)] bg-white/95 p-3.5 shadow-[0_18px_46px_rgba(44,36,22,0.18)] backdrop-blur-sm";
const MODEL_PICKER_PROVIDER_LIST_CLASS =
  "mt-2 grid gap-1 rounded-xl border border-[rgba(44,36,22,0.1)] bg-[rgba(249,247,243,0.92)] p-1 max-h-56 overflow-y-auto";

export function StudioChatComposer({
  attachments,
  availableContexts,
  canChat,
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
  onRemoveAttachment,
  onSendMessage,
  onStreamOutputChange,
  onToggleContext,
  providerOptions,
  selectedContextPaths,
  selectedCredentialLabel,
  settings,
}: Readonly<StudioChatComposerProps>) {
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showProviderList, setShowProviderList] = useState(false);
  const [showContextSelector, setShowContextSelector] = useState(false);
  const [contextSearchQuery, setContextSearchQuery] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({ 设定: true, 大纲: true, 章节: true });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelPickerRef = useRef<HTMLDivElement>(null);
  const modelButtonRef = useRef<HTMLButtonElement>(null);
  const contextSelectorRef = useRef<HTMLDivElement>(null);
  const contextButtonRef = useRef<HTMLButtonElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);

  const toggleGroup = useCallback((groupName: string) => {
    setExpandedGroups((prev) => ({ ...prev, [groupName]: !prev[groupName] }));
  }, []);

  const currentProviderOption = useMemo(
    () =>
      providerOptions.find((option) => option.value === settings.provider)
      ?? providerOptions[0]
      ?? null,
    [providerOptions, settings.provider],
  );

  const filteredContexts = useMemo(() => {
    const fileContexts = availableContexts.filter((n) => n.type === "file");
    if (!contextSearchQuery.trim()) {
      return fileContexts;
    }
    const query = contextSearchQuery.toLowerCase();
    return fileContexts.filter(
      (node) =>
        node.path.toLowerCase().includes(query) ||
        node.label.toLowerCase().includes(query),
    );
  }, [availableContexts, contextSearchQuery]);

  const groupedContexts = useMemo(() => {
    const groups: { [key: string]: typeof filteredContexts } = {
      设定: [],
      大纲: [],
      章节: [],
    };

    filteredContexts.forEach((node) => {
      const path = node.path.toLowerCase();
      if (path.includes("设定") || path.includes("setting")) {
        groups["设定"].push(node);
      } else if (path.includes("大纲") || path.includes("outline")) {
        groups["大纲"].push(node);
      } else {
        groups["章节"].push(node);
      }
    });

    return groups;
  }, [filteredContexts]);

  const totalFileCount = availableContexts.filter((n) => n.type === "file").length;

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

  const handleSubmit = useCallback(() => {
    const trimmed = composerText.trim();
    if (!trimmed || isResponding || !canChat) return;
    onSendMessage(trimmed);
    onComposerTextChange("");
  }, [canChat, composerText, isResponding, onComposerTextChange, onSendMessage]);

  const handleComposerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
      event.preventDefault();
      handleSubmit();
    },
    [handleSubmit],
  );

  return (
    <div className="relative z-20 shrink-0 border-t border-[rgba(44,36,22,0.08)] bg-gradient-to-b from-[var(--bg-surface)] to-[rgba(248,243,235,0.92)]" ref={composerRef}>
      <div className="relative z-20 p-3">
        {credentialNotice ? (
          <div className="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg bg-[rgba(178,65,46,0.08)] text-sm text-[var(--accent-danger)]">
            <p className="flex-1">{credentialNotice}</p>
            <Link className="font-medium underline underline-offset-2 hover:no-underline" href={credentialSettingsHref}>
              模型连接
            </Link>
          </div>
        ) : null}

        {attachments.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 mb-2">
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
          autoSize={{ maxRows: 6, minRows: 2 }}
          className="w-full text-sm leading-relaxed resize-none border border-[rgba(44,36,22,0.1)] rounded-lg bg-white/80 focus:border-[var(--accent-primary)] focus:shadow-[0_0_0_3px_rgba(107,143,113,0.12)] transition-all placeholder:text-[var(--text-muted)]"
          placeholder={canChat ? "写你的要求，或直接带文件进来一起改。" : "先启用可用模型后再开始提问"}
          value={composerText}
          onChange={onComposerTextChange}
          onKeyDown={handleComposerKeyDown}
        />

        <div className="flex items-center justify-between gap-2 mt-2">
          <div className="flex items-center gap-1">
            <ToolbarIconButton label="上传文件" onClick={() => fileInputRef.current?.click()}>
              <PaperclipIcon />
            </ToolbarIconButton>

            <div className="relative">
              <ToolbarChipButton
                active={showContextSelector}
                label={`上下文 ${selectedContextPaths.length}`}
                onClick={handleToggleContextSelector}
                buttonRef={contextButtonRef}
              >
                <ContextIcon />
              </ToolbarChipButton>

              {showContextSelector && (
                <div
                  className="absolute bottom-full left-0 z-30 mb-2 w-[min(22rem,calc(100vw-2rem))] max-h-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-[rgba(44,36,22,0.1)] bg-white/95 shadow-[0_18px_46px_rgba(44,36,22,0.16)] backdrop-blur-sm"
                  ref={contextSelectorRef}
                >
                  <p className="px-3 py-2 text-xs font-medium text-[var(--text-secondary)] border-b border-[rgba(44,36,22,0.06)]">
                    附加文档上下文 ({selectedContextPaths.length}/{totalFileCount})
                  </p>
                  <input
                    type="text"
                    className="w-full px-3 py-2 text-sm border-b border-[rgba(44,36,22,0.06)] bg-transparent focus:outline-none focus:bg-[rgba(107,143,113,0.05)]"
                    placeholder="搜索章节..."
                    value={contextSearchQuery}
                    onChange={(e) => setContextSearchQuery(e.target.value)}
                  />
                  <div className="overflow-y-auto max-h-52 scrollbar-thin">
                    {Object.entries(groupedContexts).map(([groupName, nodes]) => {
                      if (nodes.length === 0) return null;
                      return (
                        <div key={groupName}>
                          <div
                            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] cursor-pointer hover:bg-[rgba(107,143,113,0.05)] ${expandedGroups[groupName] ? "bg-[rgba(107,143,113,0.08)]" : ""}`}
                            onClick={() => toggleGroup(groupName)}
                          >
                            <span className={`transition-transform ${expandedGroups[groupName] ? "rotate-90" : ""}`}>▶</span>
                            <span>{groupName}</span>
                            <span className="ml-auto opacity-60">{nodes.length}</span>
                          </div>
                          {expandedGroups[groupName] && (
                            <div className="py-1">
                              {nodes.map((node) => (
                                <label className="flex items-center gap-2 px-3 py-1 cursor-pointer hover:bg-[rgba(107,143,113,0.05)]" key={node.id}>
                                  <Checkbox
                                    checked={selectedContextPaths.includes(node.path)}
                                    onChange={() => onToggleContext(node.path)}
                                  />
                                  <span className="min-w-0 flex-1 truncate text-sm">{node.label}</span>
                                  <span className="max-w-[80px] shrink-0 truncate text-xs text-[var(--text-muted)]">
                                    {node.path.split("/").slice(-2, -1)[0]}
                                  </span>
                                </label>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
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

              {showModelPicker && (
                <div
                  className={MODEL_PICKER_PANEL_CLASS}
                  ref={modelPickerRef}
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
                </div>
              )}
            </div>
          </div>

          <Button
            disabled={!canChat || isResponding}
            loading={isResponding}
            shape="round"
            type="primary"
            onClick={handleSubmit}
          >
            发送
          </Button>
        </div>

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
    <button aria-label={label} className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-secondary)] hover:bg-[rgba(107,143,113,0.1)] hover:text-[var(--text-primary)] transition-colors" type="button" onClick={onClick}>
      {children}
    </button>
  );
}

function ToolbarChipButton({
  active = false,
  children,
  label,
  onClick,
  buttonRef,
}: {
  active?: boolean;
  children: ReactNode;
  label: string;
  onClick: () => void;
  buttonRef?: React.Ref<HTMLButtonElement>;
}) {
  return (
    <button
      ref={buttonRef}
      className={`inline-flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-xs font-medium transition-colors ${active ? "bg-[rgba(107,143,113,0.15)] text-[var(--accent-primary)]" : "bg-[rgba(44,36,22,0.05)] text-[var(--text-secondary)] hover:bg-[rgba(107,143,113,0.1)]"}`}
      type="button"
      onClick={onClick}
    >
      <span className="opacity-70">{children}</span>
      <span>{label}</span>
      <span className="opacity-50 text-[10px]">⌄</span>
    </button>
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

function ComposerIcon({ path }: { path: string }) {
  return (
    <svg aria-hidden="true" fill="none" height="16" viewBox="0 0 24 24" width="16">
      <path d={path} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
    </svg>
  );
}
