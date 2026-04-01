"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { Button, Checkbox, Input } from "@arco-design/web-react";

import { AppSelect } from "@/components/ui/app-select";
import type { DocumentTreeNode } from "@/features/studio/components/studio-page-support";

import { STUDIO_ATTACHMENT_ACCEPT, type StudioChatAttachmentMeta } from "./studio-chat-attachment-support";
import type { StudioChatSettings, StudioProviderOption } from "./studio-chat-support";
import { buildStudioComposerHint } from "./studio-chat-ui-support";

type StudioChatComposerProps = {
  attachments: StudioChatAttachmentMeta[];
  availableContexts: DocumentTreeNode[];
  canChat: boolean;
  credentialNotice: string | null;
  credentialSettingsHref: string;
  isCredentialLoading: boolean;
  isResponding: boolean;
  modelButtonLabel: string;
  onAttachFiles: (files: FileList | null) => void;
  onModelNameChange: (value: string) => void;
  onProviderChange: (provider: string) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onSendMessage: (message: string) => void;
  onToggleContext: (path: string) => void;
  providerOptions: StudioProviderOption[];
  selectedContextPaths: string[];
  selectedCredentialLabel: string | null;
  settings: Pick<StudioChatSettings, "modelName" | "provider">;
};

export function StudioChatComposer({
  attachments,
  availableContexts,
  canChat,
  credentialNotice,
  credentialSettingsHref,
  isCredentialLoading,
  isResponding,
  modelButtonLabel,
  onAttachFiles,
  onModelNameChange,
  onProviderChange,
  onRemoveAttachment,
  onSendMessage,
  onToggleContext,
  providerOptions,
  selectedContextPaths,
  selectedCredentialLabel,
  settings,
}: Readonly<StudioChatComposerProps>) {
  const [inputText, setInputText] = useState("");
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showContextSelector, setShowContextSelector] = useState(false);
  const [contextSearchQuery, setContextSearchQuery] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({ 设定: true, 大纲: true, 章节: true });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const modelPickerRef = useRef<HTMLDivElement>(null);
  const contextSelectorRef = useRef<HTMLDivElement>(null);
  const contextButtonRef = useRef<HTMLButtonElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);

  const toggleGroup = useCallback((groupName: string) => {
    setExpandedGroups((prev) => ({ ...prev, [groupName]: !prev[groupName] }));
  }, []);

  const providerOptionsForSelect = useMemo(
    () => providerOptions.map((p) => ({ label: p.label, value: p.value })),
    [providerOptions],
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
      if (modelPickerRef.current && !modelPickerRef.current.contains(event.target as Node)) {
        setShowModelPicker(false);
      }
      if (
        contextSelectorRef.current &&
        !contextSelectorRef.current.contains(event.target as Node) &&
        contextButtonRef.current &&
        !contextButtonRef.current.contains(event.target as Node)
      ) {
        setShowContextSelector(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed || isResponding) return;
    onSendMessage(trimmed);
    setInputText("");
  }, [inputText, isResponding, onSendMessage]);

  const handleComposerKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
      event.preventDefault();
      handleSubmit();
    },
    [handleSubmit],
  );

  return (
    <div className="relative shrink-0 border-t border-[rgba(44,36,22,0.08)] bg-gradient-to-b from-[var(--bg-surface)] to-[rgba(248,243,235,0.92)]" ref={composerRef}>
      <div className="relative p-3">
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
          value={inputText}
          onChange={setInputText}
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
                onClick={() => setShowContextSelector((v) => !v)}
                buttonRef={contextButtonRef}
              >
                <ContextIcon />
              </ToolbarChipButton>

              {showContextSelector && (
                <div className="absolute bottom-full left-0 mb-2 w-72 max-h-80 overflow-hidden rounded-xl border border-[rgba(44,36,22,0.1)] bg-white/95 backdrop-blur-sm shadow-lg" ref={contextSelectorRef}>
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
                                  <span className="text-sm truncate flex-1">{node.label}</span>
                                  <span className="text-xs text-[var(--text-muted)] truncate max-w-[80px]">
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
                onClick={() => setShowModelPicker((v) => !v)}
              >
                <SparkIcon />
              </ToolbarChipButton>

              {showModelPicker && (
                <div className="absolute bottom-full left-0 mb-2 w-64 rounded-xl border border-[rgba(44,36,22,0.1)] bg-white/95 backdrop-blur-sm shadow-lg p-3" ref={modelPickerRef}>
                  <div className="mb-3">
                    <p className="text-sm font-medium text-[var(--text-primary)]">切换模型</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      {selectedCredentialLabel ?? "先选可用渠道，再决定模型名。"}
                    </p>
                  </div>
                  <label className="block mb-2">
                    <span className="text-xs font-medium text-[var(--text-secondary)] mb-1 block">渠道</span>
                    <AppSelect
                      aria-label="渠道"
                      options={providerOptionsForSelect}
                      placeholder={isCredentialLoading ? "正在读取渠道..." : "选择可用渠道"}
                      value={settings.provider}
                      onChange={onProviderChange}
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs font-medium text-[var(--text-secondary)] mb-1 block">模型</span>
                    <Input
                      allowClear
                      autoComplete="off"
                      placeholder="留空则跟随当前渠道默认模型"
                      spellCheck={false}
                      value={settings.modelName}
                      onChange={onModelNameChange}
                    />
                  </label>
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
