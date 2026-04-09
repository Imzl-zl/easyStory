"use client";

import {
  INITIAL_STUDIO_CHAT_SETTINGS,
  type StudioChatMessage,
  type StudioChatSettings,
} from "@/features/studio/components/chat/studio-chat-support";
import {
  areStudioChatSettingsEqual,
  buildStudioConversationTitle,
  compareStudioConversationByUpdatedAt,
  generateStudioConversationId,
  normalizeStudioChatProjectState,
  normalizeStudioChatSession,
  normalizeStudioConversationTime,
} from "@/features/studio/components/chat/studio-chat-store-normalize-support";

export type StudioChatSession = {
  composerText: string;
  conversationSkillId: string | null;
  latestCompletedRunId: string | null;
  messages: StudioChatMessage[];
  nextTurnSkillId: string | null;
  selectedContextPaths: string[];
  settings: StudioChatSettings;
};

export type StudioConversationSummary = {
  id: string;
  title: string;
  updatedAt: string;
};

export type StudioConversationRecord = StudioConversationSummary & {
  session: StudioChatSession;
};

export type StudioChatProjectState = {
  activeConversationId: string;
  conversations: StudioConversationRecord[];
};

export type StudioConversationPatchOptions = {
  preserveUpdatedAt?: boolean;
};

export type PersistedStudioChatStoreState = {
  projectStatesByScopeId?: Record<string, StudioChatProjectState>;
};

export function buildStudioChatScopeId(userId: string, projectId: string) {
  return `${userId}::${projectId}`;
}

export function createEmptyStudioChatSession(): StudioChatSession {
  return {
    composerText: "",
    conversationSkillId: null,
    latestCompletedRunId: null,
    messages: [],
    nextTurnSkillId: null,
    selectedContextPaths: [],
    settings: { ...INITIAL_STUDIO_CHAT_SETTINGS },
  };
}

function createNextStudioChatSessionSeed(current: StudioChatSession | null): StudioChatSession {
  if (!current) {
    return createEmptyStudioChatSession();
  }
  return {
    ...createEmptyStudioChatSession(),
    settings: { ...current.settings },
  };
}

export function createEmptyStudioChatProjectState(): StudioChatProjectState {
  const conversation = buildConversationRecord(createEmptyStudioChatSession());
  return { activeConversationId: conversation.id, conversations: [conversation] };
}

export function readStudioChatProjectState(
  projectStatesByScopeId: Record<string, StudioChatProjectState>,
  scopeId: string | null,
): StudioChatProjectState | null {
  return scopeId ? projectStatesByScopeId[scopeId] ?? null : null;
}

export function readStudioChatSession(
  projectStatesByScopeId: Record<string, StudioChatProjectState>,
  scopeId: string | null,
): StudioChatSession | null {
  return readActiveConversation(readStudioChatProjectState(projectStatesByScopeId, scopeId))?.session ?? null;
}

export function readStudioConversationSummaries(
  projectStatesByScopeId: Record<string, StudioChatProjectState>,
  scopeId: string | null,
): StudioConversationSummary[] {
  return readStudioChatProjectState(projectStatesByScopeId, scopeId)?.conversations.map(({ id, title, updatedAt }) => ({
    id,
    title,
    updatedAt,
  })) ?? [];
}

export function normalizePersistedStudioChatProjectState(
  projectState: StudioChatProjectState | unknown,
): StudioChatProjectState {
  return normalizeStudioChatProjectState(projectState, "persisted");
}

export function serializeStudioChatProjectState(projectState: StudioChatProjectState) {
  return JSON.stringify(projectState);
}

export function ensureStudioChatProjectState(projectState: StudioChatProjectState | undefined) {
  return projectState ? normalizeStudioChatProjectState(projectState, "runtime") : createEmptyStudioChatProjectState();
}

export function isStudioChatSessionEmpty(session: StudioChatSession): boolean {
  if (session.composerText.trim()) {
    return false;
  }
  if (session.conversationSkillId || session.nextTurnSkillId || session.latestCompletedRunId) {
    return false;
  }
  if (session.messages.length > 0 || session.selectedContextPaths.length > 0) {
    return false;
  }
  return areStudioChatSettingsEqual(session.settings, INITIAL_STUDIO_CHAT_SETTINGS);
}

export function createConversationForProjectState(projectState: StudioChatProjectState | undefined) {
  const currentProjectState = ensureStudioChatProjectState(projectState);
  const activeConversation = readActiveConversation(currentProjectState);
  if (activeConversation && isStudioChatSessionEmpty(activeConversation.session)) {
    return projectState ?? currentProjectState;
  }
  const conversation = buildConversationRecord(
    createNextStudioChatSessionSeed(activeConversation?.session ?? null),
  );
  return {
    activeConversationId: conversation.id,
    conversations: [conversation, ...currentProjectState.conversations],
  };
}

export function deleteConversationFromProjectState(
  projectState: StudioChatProjectState | undefined,
  conversationId: string,
): StudioChatProjectState {
  const currentProjectState = ensureStudioChatProjectState(projectState);
  const conversations = currentProjectState.conversations.filter((item) => item.id !== conversationId);
  if (conversations.length === currentProjectState.conversations.length) {
    return projectState ?? currentProjectState;
  }
  if (conversations.length === 0) {
    return createEmptyStudioChatProjectState();
  }
  return {
    activeConversationId:
      currentProjectState.activeConversationId === conversationId
        ? conversations[0].id
        : currentProjectState.activeConversationId,
    conversations,
  };
}

export function patchConversationInProjectState(
  projectState: StudioChatProjectState | undefined,
  conversationId: string | null,
  updater: (current: StudioChatSession) => StudioChatSession,
  options: StudioConversationPatchOptions = {},
): StudioChatProjectState {
  const currentProjectState = ensureStudioChatProjectState(projectState);
  const targetConversationId = resolveTargetConversationId(currentProjectState, conversationId);
  if (targetConversationId === null) {
    return currentProjectState;
  }
  let didChange = false;
  const conversations = currentProjectState.conversations
    .map((item) => {
      if (item.id !== targetConversationId) {
        return item;
      }
      const nextSession = updater(item.session);
      if (nextSession === item.session) {
        return item;
      }
      didChange = true;
      return buildPatchedConversationRecord(item, nextSession, options);
    })
    .sort(compareStudioConversationByUpdatedAt);
  if (!didChange) {
    return projectState ?? currentProjectState;
  }
  return {
    activeConversationId: currentProjectState.activeConversationId,
    conversations,
  };
}

export function selectConversationForProjectState(
  projectState: StudioChatProjectState | undefined,
  conversationId: string,
): StudioChatProjectState {
  const currentProjectState = ensureStudioChatProjectState(projectState);
  if (!currentProjectState.conversations.some((item) => item.id === conversationId)) {
    return projectState ?? currentProjectState;
  }
  if (currentProjectState.activeConversationId === conversationId) {
    return projectState ?? currentProjectState;
  }
  return { ...currentProjectState, activeConversationId: conversationId };
}

export function upsertProjectState(
  projectStatesByScopeId: Record<string, StudioChatProjectState>,
  scopeId: string,
  projectState: StudioChatProjectState,
) {
  return {
    projectStatesByScopeId: {
      ...projectStatesByScopeId,
      [scopeId]: normalizeStudioChatProjectState(projectState, "runtime"),
    },
  };
}

export function remapDocumentPathReferencesInProjectState(
  projectState: StudioChatProjectState | undefined,
  previousPath: string,
  nextPath: string | null,
): StudioChatProjectState {
  const currentProjectState = ensureStudioChatProjectState(projectState);
  let didChange = false;
  const conversations = currentProjectState.conversations.map((conversation) => {
    const selectedContextPaths = remapDocumentPathReferences(
      conversation.session.selectedContextPaths,
      previousPath,
      nextPath,
    );
    if (areStringArraysEqual(selectedContextPaths, conversation.session.selectedContextPaths)) {
      return conversation;
    }
    didChange = true;
    return {
      ...conversation,
      session: {
        ...conversation.session,
        selectedContextPaths,
      },
    };
  });
  if (!didChange) {
    return projectState ?? currentProjectState;
  }
  return {
    ...currentProjectState,
    conversations,
  };
}

function buildConversationRecord(
  session: StudioChatSession,
  id = generateStudioConversationId(),
): StudioConversationRecord {
  const normalizedSession = normalizeStudioChatSession(session, "runtime");
  return {
    id,
    session: normalizedSession,
    title: buildStudioConversationTitle(normalizedSession),
    updatedAt: new Date().toISOString(),
  };
}

function buildPatchedConversationRecord(
  current: StudioConversationRecord,
  nextSession: StudioChatSession,
  options: StudioConversationPatchOptions,
): StudioConversationRecord {
  const normalizedSession = normalizeStudioChatSession(nextSession, "runtime");
  if (options.preserveUpdatedAt) {
    return {
      ...current,
      session: normalizedSession,
      title: buildStudioConversationTitle(normalizedSession),
    };
  }
  return buildConversationRecord(normalizedSession, current.id);
}

function readActiveConversation(projectState: StudioChatProjectState | null) {
  if (!projectState) {
    return null;
  }
  return projectState.conversations.find((item) => item.id === projectState.activeConversationId)
    ?? projectState.conversations[0]
    ?? null;
}

function resolveTargetConversationId(projectState: StudioChatProjectState, conversationId: string | null) {
  if (!conversationId) {
    return projectState.activeConversationId;
  }
  return projectState.conversations.some((item) => item.id === conversationId) ? conversationId : null;
}

function remapDocumentPathReferences(
  paths: string[],
  previousPath: string,
  nextPath: string | null,
) {
  return Array.from(
    new Set(
      paths.flatMap((path) => {
        if (path !== previousPath && !path.startsWith(`${previousPath}/`)) {
          return [path];
        }
        if (nextPath === null) {
          return [];
        }
        if (path === previousPath) {
          return [nextPath];
        }
        return [`${nextPath}${path.slice(previousPath.length)}`];
      }),
    ),
  );
}

function areStringArraysEqual(left: string[], right: string[]) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}
