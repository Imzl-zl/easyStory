"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Message } from "@arco-design/web-react";

import {
  AssistantTurnStreamTerminalError,
  runAssistantTurn,
  runAssistantTurnStream,
} from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";
import { listProjectDocumentCatalog } from "@/lib/api/projects";
import type { AssistantActiveBufferState } from "@/lib/api/types";

import {
  buildStudioAttachmentOnlyMessage,
  extractStudioChatAttachmentMeta,
  readStudioChatAttachments,
  STUDIO_ATTACHMENT_MAX_COUNT,
  type StudioChatAttachment,
} from "./studio-chat-attachment-support";
import { useStudioChatCredentialModel } from "./studio-chat-credential-model";
import {
  appendStudioChatMessageDelta,
  applyStudioChatToolCallResult,
  applyStudioChatToolCallStart,
  buildNextStudioChatSettingsForProvider,
  buildStudioAssistantTurnPayload,
  buildStudioDocumentCatalogQueryKey,
  buildStudioUserRequestContent,
  createStudioChatMessage,
  INITIAL_STUDIO_CHAT_SETTINGS,
  resolveStudioModelButtonLabel,
  STUDIO_PENDING_REPLY_MESSAGE,
  type StudioChatMessage,
} from "./studio-chat-support";
import {
  buildFailedStudioConversationSession,
  buildSucceededStudioConversationSession,
} from "./studio-chat-turn-support";
import { useStudioChatSkillModel } from "./studio-chat-skill-model";
import { useStudioChatState } from "./studio-chat-state";

type UseStudioChatModelOptions = {
  activeBufferState: AssistantActiveBufferState | null;
  currentDocumentPath: string | null;
  projectId: string;
};

export function useStudioChatModel({
  activeBufferState,
  currentDocumentPath,
  projectId,
}: UseStudioChatModelOptions) {
  const state = useStudioChatState(projectId);
  const [attachments, setAttachments] = useState<StudioChatAttachment[]>([]);
  const [isResponding, setIsResponding] = useState(false);
  const needsDocumentCatalog = Boolean(currentDocumentPath) || state.selectedContextPaths.length > 0;
  const hasUserMessage = useMemo(
    () => state.messages.some((message) => message.role === "user"),
    [state.messages],
  );
  const documentCatalogQuery = useQuery({
    queryKey: buildStudioDocumentCatalogQueryKey(projectId),
    queryFn: () => listProjectDocumentCatalog(projectId),
    enabled: needsDocumentCatalog,
    staleTime: Number.POSITIVE_INFINITY,
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
  });
  const credentialModel = useStudioChatCredentialModel(
    projectId,
    hasUserMessage,
    state.settings,
    state.setSettings,
  );
  const skillModel = useStudioChatSkillModel(projectId, {
    activeConversationId: state.activeConversationId,
    conversationSkillId: state.conversationSkillId,
    nextTurnSkillId: state.nextTurnSkillId,
    patchConversationSession: state.patchConversationSession,
  });

  useEffect(() => {
    setAttachments([]);
  }, [state.activeConversationId]);

  const handleToggleContext = useCallback((path: string) => {
    state.setSelectedContextPaths((current) =>
      current.includes(path)
        ? current.filter((item) => item !== path)
        : [...current, path],
    );
  }, [state]);

  const handleProviderChange = useCallback((provider: string) => {
    state.setSettings((current) =>
      buildNextStudioChatSettingsForProvider(
        credentialModel.credentialOptions,
        current,
        provider,
      ));
  }, [credentialModel.credentialOptions, state]);

  const handleModelNameChange = useCallback((value: string) => {
    state.setSettings((current) => ({ ...current, modelName: value }));
  }, [state]);

  const handleStreamOutputChange = useCallback((value: boolean) => {
    state.setSettings((current) => ({ ...current, streamOutput: value }));
  }, [state]);

  const handleAttachFiles = useCallback(async (files: FileList | null) => {
    if (!files) {
      return;
    }
    try {
      if (attachments.length + files.length > STUDIO_ATTACHMENT_MAX_COUNT) {
        throw new Error(`一次最多保留 ${STUDIO_ATTACHMENT_MAX_COUNT} 个文件。`);
      }
      const nextAttachments = await readStudioChatAttachments(files);
      setAttachments((current) => [...current, ...nextAttachments]);
    } catch (error) {
      Message.error(getErrorMessage(error));
    }
  }, [attachments.length]);

  const handleRemoveAttachment = useCallback((attachmentId: string) => {
    setAttachments((current) => current.filter((attachment) => attachment.id !== attachmentId));
  }, []);

  const handleSendMessage = useCallback(async (content: string) => {
    if (isResponding) {
      return;
    }
    if (!credentialModel.canChat) {
      Message.warning(credentialModel.credentialNotice ?? "当前没有可用模型连接。");
      return;
    }
    if (needsDocumentCatalog) {
      if (documentCatalogQuery.error) {
        Message.error(getErrorMessage(documentCatalogQuery.error));
        return;
      }
      if (!documentCatalogQuery.data) {
        Message.warning("当前文稿目录快照仍在加载，请稍后重试。");
        return;
      }
    }
    const conversationId = state.activeConversationId;
    const userMessage = buildStudioUserMessage({
      attachments,
      content,
    });

    const assistantMessage = createStudioChatMessage(
      "assistant",
      STUDIO_PENDING_REPLY_MESSAGE,
      { status: "pending" },
    );
    const nextMessages = [...state.messages, userMessage];
    const consumedNextTurnSkillId = state.nextTurnSkillId;
    const activeSkillId = consumedNextTurnSkillId ?? state.conversationSkillId;
    const payload = buildStudioAssistantTurnPayload({
      activeBufferState,
      conversationId,
      currentDocumentPath,
      documentCatalogEntries: documentCatalogQuery.data ?? null,
      latestCompletedRunId: state.latestCompletedRunId,
      messages: nextMessages,
      projectId,
      selectedContextPaths: state.selectedContextPaths,
      settings: state.settings,
      skillId: activeSkillId,
    });

    state.patchConversationSession(conversationId, (current) => ({
      ...current,
      composerText: "",
      messages: [...current.messages, userMessage, assistantMessage],
    }));
    setAttachments([]);
    setIsResponding(true);

    try {
      const result = state.settings.streamOutput
        ? await runStudioChatStream(payload, assistantMessage.id, (updater) => {
          state.patchConversationSession(conversationId, (current) => ({
            ...current,
            messages: updater(current.messages),
          }));
        })
        : await runAssistantTurn(payload);
      state.patchConversationSession(conversationId, (current) =>
        buildSucceededStudioConversationSession(current, {
          consumedNextTurnSkillId,
          content: result.content,
          messageId: assistantMessage.id,
          runId: result.run_id,
        }));
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      state.patchConversationSession(conversationId, (current) =>
        buildFailedStudioConversationSession(current, {
          errorMessage,
          messageId: assistantMessage.id,
          terminalReason: resolveStudioToolProgressTerminalReason(error),
        }));
      Message.error(errorMessage);
    } finally {
      setIsResponding(false);
    }
  }, [
    activeBufferState,
    credentialModel.canChat,
    credentialModel.credentialNotice,
    currentDocumentPath,
    documentCatalogQuery.data,
    documentCatalogQuery.error,
    isResponding,
    needsDocumentCatalog,
    projectId,
    state,
    attachments,
  ]);

  return {
    activeConversationId: state.activeConversationId,
    attachments: extractStudioChatAttachmentMeta(attachments),
    composerText: state.composerText,
    conversationSummaries: state.conversationSummaries,
    credentialModel,
    createConversation: state.createConversation,
    deleteConversation: state.deleteConversation,
    handleAttachFiles,
    handleModelNameChange,
    handleProviderChange,
    handleRemoveAttachment,
    handleSendMessage,
    handleStreamOutputChange,
    handleToggleContext,
    isResponding,
    messages: state.messages,
    remapDocumentPathReferences: state.remapDocumentPathReferences,
    selectConversation: state.selectConversation,
    selectedContextPaths: state.selectedContextPaths,
    selectedCredentialLabel: credentialModel.selectedCredential?.displayLabel ?? null,
    setComposerText: state.setComposerText,
    settings: state.settings,
    skillModel,
    visibleModelLabel: resolveStudioModelButtonLabel({
      modelName: state.settings.modelName,
      selectedCredential: credentialModel.selectedCredential,
    }),
  };
}

async function runStudioChatStream(
  payload: Parameters<typeof runAssistantTurn>[0],
  messageId: string,
  updateMessages: (updater: (current: StudioChatMessage[]) => StudioChatMessage[]) => void,
) {
  return runAssistantTurnStream(payload, {
    onChunk: (delta) => {
      updateMessages((current) =>
        appendStudioChatMessageDelta(current, messageId, delta));
    },
    onToolCallResult: (payload) => {
      updateMessages((current) =>
        applyStudioChatToolCallResult(current, messageId, payload));
    },
    onToolCallStart: (payload) => {
      updateMessages((current) =>
        applyStudioChatToolCallStart(current, messageId, payload));
    },
  });
}

function buildStudioUserMessage(options: {
  attachments: StudioChatAttachment[];
  content: string;
}) {
  const trimmedContent = options.content.trim();
  const displayContent = trimmedContent || buildStudioAttachmentOnlyMessage(options.attachments);
  const requestContent = buildStudioUserRequestContent({
    attachments: options.attachments,
    message: displayContent,
  });
  return createStudioChatMessage("user", displayContent, {
    attachments: extractStudioChatAttachmentMeta(options.attachments),
    requestContent,
  });
}

function resolveStudioToolProgressTerminalReason(error: unknown) {
  return error instanceof AssistantTurnStreamTerminalError && error.terminalStatus === "cancelled"
    ? "cancelled"
    : "interrupted";
}
