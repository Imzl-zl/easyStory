"use client";

import type { StudioChatAttachmentMeta } from "./studio-chat-attachment-support";
import {
  finalizeStudioChatToolProgress,
  INITIAL_STUDIO_CHAT_SETTINGS,
  STUDIO_PENDING_REPLY_MESSAGE,
  type StudioChatMessage,
  type StudioChatSettings,
  type StudioChatToolProgressEntry,
} from "./studio-chat-support";
import type {
  StudioChatProjectState,
  StudioChatSession,
  StudioConversationRecord,
  StudioConversationSummary,
} from "./studio-chat-store-support";

const CONVERSATION_TITLE_MAX_LENGTH = 22;
const DEFAULT_CONVERSATION_TITLE = "新对话";
const STUDIO_INTERRUPTED_REPLY_MESSAGE = "这次回复中断了，你可以重新发送。";

export function normalizeStudioChatProjectState(
  projectState: StudioChatProjectState | unknown,
  mode: "persisted" | "runtime",
): StudioChatProjectState {
  const record = isRecord(projectState) ? projectState : {};
  const rawConversations = Array.isArray(record.conversations) ? record.conversations : [];
  const conversations = rawConversations
    .map((conversation) => normalizeConversation(conversation, mode))
    .sort(compareStudioConversationByUpdatedAt)
    .filter((item, index, current) => current.findIndex((candidate) => candidate.id === item.id) === index);
  if (conversations.length === 0) {
    return createFallbackProjectState();
  }
  const activeConversationId = readStringValue(record.activeConversationId);
  return {
    activeConversationId:
      activeConversationId && conversations.some((item) => item.id === activeConversationId)
        ? activeConversationId
        : conversations[0].id,
    conversations,
  };
}

export function normalizeStudioChatSession(
  value: unknown,
  mode: "persisted" | "runtime",
): StudioChatSession {
  const record = isRecord(value) ? value : {};
  return {
    composerText: readStringValue(record.composerText) ?? "",
    conversationSkillId: readOptionalSkillId(record.conversationSkillId),
    latestCompletedRunId: readOptionalString(record.latestCompletedRunId),
    messages: normalizeMessages(record.messages, mode),
    nextTurnSkillId: readOptionalSkillId(record.nextTurnSkillId),
    selectedContextPaths: readStringArray(record.selectedContextPaths),
    settings: { ...INITIAL_STUDIO_CHAT_SETTINGS, ...(isRecord(record.settings) ? record.settings : {}) },
  };
}

export function buildStudioConversationTitle(session: StudioChatSession) {
  const source = session.messages.find((item) => item.role === "user")?.content ?? session.composerText;
  const normalizedText = source.replace(/\s+/g, " ").trim();
  if (!normalizedText) {
    return DEFAULT_CONVERSATION_TITLE;
  }
  return normalizedText.length > CONVERSATION_TITLE_MAX_LENGTH
    ? `${normalizedText.slice(0, CONVERSATION_TITLE_MAX_LENGTH)}…`
    : normalizedText;
}

export function compareStudioConversationByUpdatedAt(
  left: StudioConversationSummary,
  right: StudioConversationSummary,
) {
  return right.updatedAt.localeCompare(left.updatedAt);
}

export function generateStudioConversationId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `conversation-${Math.random().toString(36).slice(2, 10)}`;
}

export function normalizeStudioConversationTime(value: string | null) {
  if (!value) {
    return new Date().toISOString();
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();
}

export function areStudioChatSettingsEqual(left: StudioChatSettings, right: StudioChatSettings) {
  return left.maxOutputTokens === right.maxOutputTokens
    && left.modelName === right.modelName
    && left.provider === right.provider
    && left.streamOutput === right.streamOutput;
}

function createFallbackProjectState(): StudioChatProjectState {
  const conversation = buildFallbackConversationRecord();
  return { activeConversationId: conversation.id, conversations: [conversation] };
}

function buildFallbackConversationRecord(): StudioConversationRecord {
  const session = {
    composerText: "",
    conversationSkillId: null,
    latestCompletedRunId: null,
    messages: [],
    nextTurnSkillId: null,
    selectedContextPaths: [],
    settings: { ...INITIAL_STUDIO_CHAT_SETTINGS },
  };
  return {
    id: generateStudioConversationId(),
    session,
    title: DEFAULT_CONVERSATION_TITLE,
    updatedAt: new Date().toISOString(),
  };
}

function normalizeConversation(
  conversation: StudioConversationRecord | unknown,
  mode: "persisted" | "runtime",
): StudioConversationRecord {
  const record = isRecord(conversation) ? conversation : {};
  const session = normalizeStudioChatSession(record.session, mode);
  return {
    id: readStringValue(record.id) ?? generateStudioConversationId(),
    title: buildStudioConversationTitle(session),
    updatedAt: normalizeStudioConversationTime(readStringValue(record.updatedAt)),
    session,
  };
}

function normalizeMessages(value: unknown, mode: "persisted" | "runtime") {
  const messages = Array.isArray(value) ? value : [];
  return messages.map((message) => normalizeMessage(message, mode));
}

function normalizeMessage(value: unknown, mode: "persisted" | "runtime"): StudioChatMessage {
  const record = isRecord(value) ? value : {};
  const content = readStringValue(record.content) ?? "";
  const rawMarkdown = readStringValue(record.rawMarkdown) ?? content;
  const status = record.status === "pending" || record.status === "error" ? record.status : undefined;
  const normalizedMessage: StudioChatMessage = {
    attachments: normalizeAttachments(record.attachments),
    content,
    id: readStringValue(record.id) ?? `message-${Math.random().toString(36).slice(2, 10)}`,
    rawMarkdown,
    requestContent: readStringValue(record.requestContent) ?? undefined,
    role: record.role === "assistant" ? "assistant" : "user",
    status,
    toolProgress: normalizeToolProgress(record.toolProgress),
  };
  if (mode !== "persisted" || normalizedMessage.status !== "pending") {
    return normalizedMessage;
  }
  const interruptedContent = buildInterruptedMessageContent(normalizedMessage.content || normalizedMessage.rawMarkdown);
  return {
    ...normalizedMessage,
    content: interruptedContent,
    rawMarkdown: interruptedContent,
    status: "error",
    toolProgress: finalizeStudioChatToolProgress(normalizedMessage.toolProgress, "interrupted"),
  };
}

function normalizeAttachments(value: unknown): StudioChatAttachmentMeta[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  return value.flatMap((item) => {
    const record = isRecord(item) ? item : {};
    const id = readStringValue(record.id);
    const name = readStringValue(record.name);
    const size = typeof record.size === "number" && Number.isFinite(record.size) ? record.size : null;
    return id && name && size !== null ? [{ id, name, size }] : [];
  });
}

function normalizeToolProgress(value: unknown): StudioChatToolProgressEntry[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const entries = value.flatMap((item) => {
    const record = isRecord(item) ? item : {};
    const label = readOptionalString(record.label);
    const statusLabel = readOptionalString(record.statusLabel);
    const toolCallId = readOptionalString(record.toolCallId);
    const tone = normalizeToolProgressTone(record.tone);
    if (!label || !statusLabel || !toolCallId || !tone) {
      return [];
    }
    return [{
      detail: readOptionalString(record.detail) ?? undefined,
      label,
      statusLabel,
      toolCallId,
      tone,
    }];
  });
  return entries.length > 0 ? entries : undefined;
}

function buildInterruptedMessageContent(content: string) {
  const trimmed = content.trim();
  if (!trimmed || trimmed === STUDIO_PENDING_REPLY_MESSAGE) {
    return STUDIO_INTERRUPTED_REPLY_MESSAGE;
  }
  return `${trimmed}\n\n${STUDIO_INTERRUPTED_REPLY_MESSAGE}`;
}

function readStringArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.trim().length > 0) : [];
}

function readOptionalSkillId(value: unknown) {
  const normalized = readStringValue(value)?.trim();
  return normalized || null;
}

function readOptionalString(value: unknown) {
  const normalized = readStringValue(value)?.trim();
  return normalized || null;
}

function normalizeToolProgressTone(value: unknown): StudioChatToolProgressEntry["tone"] | null {
  if (value === "danger" || value === "muted" || value === "running" || value === "success") {
    return value;
  }
  return null;
}

function readStringValue(value: unknown) {
  return typeof value === "string" ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
