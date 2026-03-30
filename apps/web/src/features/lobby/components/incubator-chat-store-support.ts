"use client";

import type { ProjectIncubatorConversationDraft } from "@/lib/api/types";

import {
  createIncubatorInitialMessages,
  INCUBATOR_INTERRUPTED_REPLY_MESSAGE,
  INITIAL_INCUBATOR_CHAT_SETTINGS,
  resolveInterruptedIncubatorReply,
  type IncubatorChatMessage,
  type IncubatorChatSettings,
} from "./incubator-chat-support";

const CONVERSATION_TITLE_MAX_LENGTH = 22;
const DEFAULT_CONVERSATION_TITLE = "新对话";
const PERSISTED_MODE = "persisted";
const RUNTIME_MODE = "runtime";

export type IncubatorChatSession = {
  composerText: string;
  draft: ProjectIncubatorConversationDraft | null;
  draftFingerprint: string | null;
  hasCustomProjectName: boolean;
  messages: IncubatorChatMessage[];
  projectName: string;
  settings: IncubatorChatSettings;
};

export type IncubatorConversationSummary = {
  id: string;
  title: string;
  updatedAt: string;
};

export type IncubatorConversationRecord = IncubatorConversationSummary & {
  session: IncubatorChatSession;
};

export type IncubatorChatUserState = {
  activeConversationId: string;
  conversations: IncubatorConversationRecord[];
};

export type LegacyPersistedIncubatorChatStoreState = {
  sessionsByUserId?: Record<string, IncubatorChatSession>;
  userStatesByUserId?: Record<string, IncubatorChatUserState>;
};

export function createEmptyIncubatorChatSession(): IncubatorChatSession {
  return {
    composerText: "",
    draft: null,
    draftFingerprint: null,
    hasCustomProjectName: false,
    messages: createIncubatorInitialMessages(),
    projectName: "",
    settings: { ...INITIAL_INCUBATOR_CHAT_SETTINGS },
  };
}

export function createEmptyIncubatorChatUserState(): IncubatorChatUserState {
  const conversation = buildConversationRecord(createEmptyIncubatorChatSession());
  return { activeConversationId: conversation.id, conversations: [conversation] };
}

export function readIncubatorChatUserState(
  userStatesByUserId: Record<string, IncubatorChatUserState>,
  userId: string | null,
): IncubatorChatUserState | null {
  return userId ? userStatesByUserId[userId] ?? null : null;
}

export function readIncubatorActiveConversationId(
  userStatesByUserId: Record<string, IncubatorChatUserState>,
  userId: string | null,
): string | null {
  return readIncubatorChatUserState(userStatesByUserId, userId)?.activeConversationId ?? null;
}

export function readIncubatorChatSession(
  userStatesByUserId: Record<string, IncubatorChatUserState>,
  userId: string | null,
): IncubatorChatSession | null {
  return readActiveConversation(readIncubatorChatUserState(userStatesByUserId, userId))?.session ?? null;
}

export function readIncubatorConversationSummaries(
  userStatesByUserId: Record<string, IncubatorChatUserState>,
  userId: string | null,
): IncubatorConversationSummary[] {
  return readIncubatorChatUserState(userStatesByUserId, userId)?.conversations.map(({ id, title, updatedAt }) => ({
    id,
    title,
    updatedAt,
  })) ?? [];
}

export function normalizePersistedIncubatorChatSession(
  session: IncubatorChatSession,
): IncubatorChatSession {
  return normalizeIncubatorChatSession(session, PERSISTED_MODE);
}

function normalizeRuntimeIncubatorChatSession(
  session: IncubatorChatSession,
): IncubatorChatSession {
  return normalizeIncubatorChatSession(session, RUNTIME_MODE);
}

function normalizeIncubatorChatSession(
  session: IncubatorChatSession,
  mode: typeof PERSISTED_MODE | typeof RUNTIME_MODE,
): IncubatorChatSession {
  return {
    composerText: session.composerText ?? "",
    draft: session.draft ?? null,
    draftFingerprint: session.draftFingerprint ?? null,
    hasCustomProjectName: session.hasCustomProjectName ?? false,
    messages: normalizeIncubatorMessages(session.messages ?? [], mode),
    projectName: session.projectName ?? "",
    settings: { ...INITIAL_INCUBATOR_CHAT_SETTINGS, ...session.settings },
  };
}

export function normalizePersistedIncubatorChatUserState(
  userState: IncubatorChatUserState | unknown,
): IncubatorChatUserState {
  return normalizeIncubatorChatUserState(userState, PERSISTED_MODE);
}

function normalizeRuntimeIncubatorChatUserState(
  userState: IncubatorChatUserState | unknown,
): IncubatorChatUserState {
  return normalizeIncubatorChatUserState(userState, RUNTIME_MODE);
}

function normalizeIncubatorChatUserState(
  userState: IncubatorChatUserState | unknown,
  mode: typeof PERSISTED_MODE | typeof RUNTIME_MODE,
): IncubatorChatUserState {
  const conversations = resolveConversations(userState, mode);
  if (conversations.length === 0) {
    return createEmptyIncubatorChatUserState();
  }
  const activeConversationId = resolvePersistedActiveConversationId(userState, conversations);
  return { activeConversationId, conversations };
}

export function serializeIncubatorChatUserState(userState: IncubatorChatUserState): string {
  return JSON.stringify(userState);
}

export function isIncubatorChatSessionEmpty(session: IncubatorChatSession): boolean {
  if (session.composerText.trim() || session.projectName.trim() || session.draft || session.draftFingerprint) {
    return false;
  }
  if (session.hasCustomProjectName) {
    return false;
  }
  if (!areIncubatorSettingsEqual(session.settings, INITIAL_INCUBATOR_CHAT_SETTINGS)) {
    return false;
  }
  return !session.messages.some((message) => message.role === "user");
}

export function ensureIncubatorChatUserState(userState: IncubatorChatUserState | undefined) {
  return userState ? normalizeRuntimeIncubatorChatUserState(userState) : createEmptyIncubatorChatUserState();
}

export function createConversationForUserState(userState: IncubatorChatUserState | undefined) {
  const currentUserState = ensureIncubatorChatUserState(userState);
  const activeConversation = readActiveConversation(currentUserState);
  if (activeConversation && isIncubatorChatSessionEmpty(activeConversation.session)) {
    return userState ?? currentUserState;
  }
  const conversation = buildConversationRecord(createEmptyIncubatorChatSession());
  return { activeConversationId: conversation.id, conversations: [conversation, ...currentUserState.conversations] };
}

export function deleteConversationFromUserState(
  userState: IncubatorChatUserState | undefined,
  conversationId: string,
): IncubatorChatUserState {
  const currentUserState = ensureIncubatorChatUserState(userState);
  const conversations = currentUserState.conversations.filter((item) => item.id !== conversationId);
  if (conversations.length === currentUserState.conversations.length) {
    return userState ?? currentUserState;
  }
  if (conversations.length === 0) {
    return createEmptyIncubatorChatUserState();
  }
  return {
    activeConversationId: currentUserState.activeConversationId === conversationId
      ? conversations[0].id
      : currentUserState.activeConversationId,
    conversations,
  };
}

export function patchConversationInUserState(
  userState: IncubatorChatUserState | undefined,
  conversationId: string | null,
  updater: (current: IncubatorChatSession) => IncubatorChatSession,
): IncubatorChatUserState {
  const currentUserState = ensureIncubatorChatUserState(userState);
  const targetConversationId = resolveTargetConversationId(currentUserState, conversationId);
  if (targetConversationId === null) {
    return currentUserState;
  }
  let didChange = false;
  const conversations = currentUserState.conversations
    .map((item) => {
      if (item.id !== targetConversationId) {
        return item;
      }
      const nextSession = updater(item.session);
      if (nextSession === item.session) {
        return item;
      }
      didChange = true;
      return buildConversationRecord(nextSession, item.id);
    })
    .sort(compareConversationByUpdatedAt);
  if (!didChange) {
    return userState ?? currentUserState;
  }
  return {
    activeConversationId: currentUserState.activeConversationId,
    conversations,
  };
}

export function selectConversationForUserState(
  userState: IncubatorChatUserState | undefined,
  conversationId: string,
): IncubatorChatUserState {
  const currentUserState = ensureIncubatorChatUserState(userState);
  if (!currentUserState.conversations.some((item) => item.id === conversationId)) {
    return userState ?? currentUserState;
  }
  if (currentUserState.activeConversationId === conversationId) {
    return userState ?? currentUserState;
  }
  return { ...currentUserState, activeConversationId: conversationId };
}

export function upsertUserState(
  userStatesByUserId: Record<string, IncubatorChatUserState>,
  userId: string,
  userState: IncubatorChatUserState,
) {
  return { userStatesByUserId: { ...userStatesByUserId, [userId]: normalizeRuntimeIncubatorChatUserState(userState) } };
}

export function removeUserState(
  userStatesByUserId: Record<string, IncubatorChatUserState>,
  userId: string,
) {
  if (!(userId in userStatesByUserId)) {
    return { userStatesByUserId };
  }
  const nextUserStates = { ...userStatesByUserId };
  delete nextUserStates[userId];
  return { userStatesByUserId: nextUserStates };
}

export function migratePersistedState(persistedState: unknown) {
  const state = persistedState as LegacyPersistedIncubatorChatStoreState | undefined;
  if (!state) {
    return { userStatesByUserId: {} };
  }
  if (state.userStatesByUserId) {
    return { userStatesByUserId: mapUserStates(state.userStatesByUserId) };
  }
  return {
    userStatesByUserId: Object.fromEntries(
      Object.entries(state.sessionsByUserId ?? {}).map(([userId, session]) => [
        userId,
        normalizePersistedIncubatorChatUserState({
          activeConversationId: "legacy",
          conversations: [buildConversationRecord(session, "legacy", PERSISTED_MODE)],
        }),
      ]),
    ),
  };
}

function readActiveConversation(userState: IncubatorChatUserState | null) {
  if (!userState) {
    return null;
  }
  return userState.conversations.find((item) => item.id === userState.activeConversationId)
    ?? userState.conversations[0]
    ?? null;
}

function normalizeConversation(
  conversation: IncubatorConversationRecord | unknown,
  mode: typeof PERSISTED_MODE | typeof RUNTIME_MODE,
): IncubatorConversationRecord {
  const record = isRecord(conversation) ? conversation : {};
  const session = mode === PERSISTED_MODE
    ? normalizePersistedIncubatorChatSession(resolveConversationSession(record))
    : normalizeRuntimeIncubatorChatSession(resolveConversationSession(record));
  return {
    id: readStringValue(record.id) ?? generateConversationId(),
    title: buildConversationTitle(session),
    updatedAt: normalizeConversationTime(readStringValue(record.updatedAt) ?? undefined),
    session,
  };
}

function normalizeIncubatorMessages(
  messages: IncubatorChatMessage[],
  mode: typeof PERSISTED_MODE | typeof RUNTIME_MODE,
) {
  if (messages.length === 0) {
    return createIncubatorInitialMessages();
  }
  if (mode === RUNTIME_MODE) {
    return messages;
  }
  return messages.map((message) => message.status !== "pending"
    ? message
    : { ...message, content: buildInterruptedMessageContent(message.content), status: "error" as const });
}

function buildInterruptedMessageContent(content: string) {
  return resolveInterruptedIncubatorReply(content) ?? INCUBATOR_INTERRUPTED_REPLY_MESSAGE;
}

function buildConversationRecord(
  session: IncubatorChatSession,
  id = generateConversationId(),
  mode: typeof PERSISTED_MODE | typeof RUNTIME_MODE = RUNTIME_MODE,
) {
  const normalizedSession = mode === PERSISTED_MODE
    ? normalizePersistedIncubatorChatSession(session)
    : normalizeRuntimeIncubatorChatSession(session);
  return { id, session: normalizedSession, title: buildConversationTitle(normalizedSession), updatedAt: new Date().toISOString() };
}

function buildConversationTitle(session: IncubatorChatSession) {
  const source = session.messages.find((item) => item.role === "user")?.content
    ?? session.projectName;
  const normalizedText = source.replace(/\s+/g, " ").trim();
  if (!normalizedText) {
    return DEFAULT_CONVERSATION_TITLE;
  }
  return normalizedText.length > CONVERSATION_TITLE_MAX_LENGTH
    ? `${normalizedText.slice(0, CONVERSATION_TITLE_MAX_LENGTH)}…`
    : normalizedText;
}

function compareConversationByUpdatedAt(left: IncubatorConversationSummary, right: IncubatorConversationSummary) {
  return right.updatedAt.localeCompare(left.updatedAt);
}

function normalizeConversationTime(value: string | undefined) {
  if (!value) {
    return new Date().toISOString();
  }
  const parsedValue = new Date(value);
  return Number.isNaN(parsedValue.getTime()) ? new Date().toISOString() : parsedValue.toISOString();
}

function resolveConversations(
  userState: unknown,
  mode: typeof PERSISTED_MODE | typeof RUNTIME_MODE,
) {
  const record = isRecord(userState) ? userState : {};
  const rawConversations = Array.isArray(record.conversations) ? record.conversations : [];
  return rawConversations
    .map((conversation) => normalizeConversation(conversation, mode))
    .sort(compareConversationByUpdatedAt)
    .filter((item, index, current) => current.findIndex((candidate) => candidate.id === item.id) === index);
}

function resolvePersistedActiveConversationId(
  userState: unknown,
  conversations: IncubatorConversationRecord[],
) {
  const record = isRecord(userState) ? userState : {};
  const activeConversationId = readStringValue(record.activeConversationId);
  return activeConversationId && conversations.some((item) => item.id === activeConversationId)
    ? activeConversationId
    : conversations[0].id;
}

function resolveConversationSession(record: Record<string, unknown>) {
  if (isRecord(record.session)) {
    return record.session as IncubatorChatSession;
  }
  return record as IncubatorChatSession;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readStringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function resolveTargetConversationId(userState: IncubatorChatUserState, conversationId: string | null) {
  if (!conversationId) {
    return userState.activeConversationId;
  }
  return userState.conversations.some((item) => item.id === conversationId)
    ? conversationId
    : null;
}

function generateConversationId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `conversation-${Math.random().toString(36).slice(2, 10)}`;
}

function areIncubatorSettingsEqual(left: IncubatorChatSettings, right: IncubatorChatSettings) {
  return left.agentId === right.agentId
    && left.allowSystemCredentialPool === right.allowSystemCredentialPool
    && JSON.stringify(left.hookIds) === JSON.stringify(right.hookIds)
    && left.maxOutputTokens === right.maxOutputTokens
    && left.modelName === right.modelName
    && left.provider === right.provider
    && left.skillId === right.skillId
    && left.streamOutput === right.streamOutput;
}

function mapUserStates(userStatesByUserId: Record<string, IncubatorChatUserState>) {
  return Object.fromEntries(
    Object.entries(userStatesByUserId).map(([userId, userState]) => [
      userId,
      normalizePersistedIncubatorChatUserState(userState),
    ]),
  );
}
