"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Message } from "@arco-design/web-react";

import {
  AssistantTurnStreamTerminalError,
  runAssistantTurn,
  runAssistantTurnStream,
} from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";
import { listProjectDocumentCatalog } from "@/lib/api/projects";
import type { AssistantActiveBufferState, ProjectDocumentCatalogEntry } from "@/lib/api/types";

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
  resolveStudioPreparedAssistantTurnPayload,
  buildStudioUserRequestContent,
  createStudioChatMessage,
  resolveStudioModelButtonLabel,
  STUDIO_PENDING_REPLY_MESSAGE,
  type StudioChatMessage,
} from "./studio-chat-support";
import { buildStudioDocumentCatalogQueryKey } from "./studio-document-catalog-support";
import { runStudioSendOnce } from "./studio-chat-send-guard-support";
import {
  resolveStudioSkillSendBlockReason,
  resolveStudioSendableSkillSelection,
  type StudioSkillLookupStatus,
} from "./studio-chat-skill-support";
import {
  buildFailedStudioConversationSession,
  buildSucceededStudioConversationSession,
} from "./studio-chat-turn-support";
import { useStudioChatSkillModel } from "./studio-chat-skill-model";
import { useStudioChatState } from "./studio-chat-state";
import {
  buildStudioWriteIntentNotice,
  resolveStudioCurrentWriteTarget,
  resolveStudioRequestedWriteTargets,
  resolveStudioWriteSendBlockReason,
} from "./studio-chat-write-support";

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
  const [writeToCurrentDocument, setWriteToCurrentDocument] = useState(false);
  const sendInFlightRef = useRef(false);
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

  const documentCatalogErrorMessage = useMemo(
    () => (documentCatalogQuery.error ? getErrorMessage(documentCatalogQuery.error) : null),
    [documentCatalogQuery.error],
  );
  const currentWriteTarget = useMemo(() => resolveStudioCurrentWriteTarget({
    activeBufferState,
    currentDocumentPath,
    documentCatalogErrorMessage,
    documentCatalogEntries: documentCatalogQuery.data ?? null,
  }), [activeBufferState, currentDocumentPath, documentCatalogErrorMessage, documentCatalogQuery.data]);

  const writeIntentNotice = useMemo(
    () => buildStudioWriteIntentNotice(currentWriteTarget, writeToCurrentDocument),
    [currentWriteTarget, writeToCurrentDocument],
  );
  const skillLookupStatus = useMemo<StudioSkillLookupStatus>(() => {
    if (skillModel.skillsLoading) {
      return "loading";
    }
    return skillModel.skillErrorMessage ? "error" : "ready";
  }, [skillModel.skillErrorMessage, skillModel.skillsLoading]);
  const activeSkillSelection = useMemo(() => resolveStudioSendableSkillSelection({
    conversationSkillId: state.conversationSkillId,
    nextTurnSkillId: state.nextTurnSkillId,
    skillLookupStatus,
    skillOptions: skillModel.skillOptions,
  }), [
    skillModel.skillOptions,
    skillLookupStatus,
    state.conversationSkillId,
    state.nextTurnSkillId,
  ]);
  const skillSendBlockReason = useMemo(() => resolveStudioSkillSendBlockReason({
    conversationSkillId: state.conversationSkillId,
    nextTurnSkillId: state.nextTurnSkillId,
    skillLookupStatus,
    skillOptions: skillModel.skillOptions,
  }), [skillLookupStatus, skillModel.skillOptions, state.conversationSkillId, state.nextTurnSkillId]);
  const writeSendBlockReason = useMemo(() => resolveStudioWriteSendBlockReason({
    enabled: writeToCurrentDocument,
    writeTarget: currentWriteTarget,
  }), [currentWriteTarget, writeToCurrentDocument]);

  useEffect(() => {
    setWriteToCurrentDocument(false);
  }, [currentDocumentPath, state.activeConversationId]);

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

  const handleToggleWriteToCurrentDocument = useCallback(() => {
    if (writeToCurrentDocument) {
      setWriteToCurrentDocument(false);
      return;
    }
    if (!currentWriteTarget.available) {
      if (currentWriteTarget.disabledReason) {
        Message.warning(currentWriteTarget.disabledReason);
      }
      return;
    }
    setWriteToCurrentDocument(true);
  }, [currentWriteTarget, writeToCurrentDocument]);

  const handleSendMessage = useCallback((content: string) => runStudioSendOnce(
    sendInFlightRef,
    async () => {
      if (!ensureStudioChatTurnCanStart({
        canChat: credentialModel.canChat,
        credentialNotice: credentialModel.credentialNotice,
        documentCatalogEntries: documentCatalogQuery.data ?? null,
        documentCatalogError: documentCatalogQuery.error,
        isResponding,
        needsDocumentCatalog,
        skillSendBlockReason,
        toolCapabilityNotice: credentialModel.toolCapabilityNotice,
        writeSendBlockReason,
      })) {
        return false;
      }
      const requestedWriteTargets = resolveStudioRequestedWriteTargets({
        enabled: writeToCurrentDocument,
        writeTarget: currentWriteTarget,
      });
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
      const consumedNextTurnSkillId = activeSkillSelection.nextTurnSkillId;
      const activeSkillId = consumedNextTurnSkillId ?? activeSkillSelection.conversationSkillId;
      const payloadResult = resolveStudioPreparedAssistantTurnPayload({
        activeBufferState,
        conversationId,
        currentDocumentPath,
        documentCatalogEntries: documentCatalogQuery.data ?? null,
        latestCompletedRunId: state.latestCompletedRunId,
        messages: nextMessages,
        projectId,
        requestedWriteTargets,
        selectedContextPaths: state.selectedContextPaths,
        settings: state.settings,
        skillId: activeSkillId,
      });
      if (!payloadResult.ok) {
        Message.error(payloadResult.errorMessage);
        return false;
      }
      const payload = payloadResult.payload;

      state.patchConversationSession(conversationId, (current) => ({
        ...current,
        composerText: "",
        messages: [...current.messages, userMessage, assistantMessage],
      }));
      setAttachments([]);
      setWriteToCurrentDocument(false);
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
      return true;
    },
  ), [
    activeBufferState,
    currentWriteTarget,
    credentialModel.canChat,
    credentialModel.credentialNotice,
    currentDocumentPath,
    documentCatalogQuery.data,
    documentCatalogQuery.error,
    isResponding,
    needsDocumentCatalog,
    projectId,
    skillSendBlockReason,
    state,
    attachments,
    activeSkillSelection,
    writeSendBlockReason,
    writeToCurrentDocument,
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
    handleToggleWriteToCurrentDocument,
    isResponding,
    isWriteToCurrentDocumentEnabled: writeToCurrentDocument,
    messages: state.messages,
    remapDocumentPathReferences: state.remapDocumentPathReferences,
    selectConversation: state.selectConversation,
    selectedContextPaths: state.selectedContextPaths,
    selectedCredentialLabel: credentialModel.selectedCredential?.displayLabel ?? null,
    setComposerText: state.setComposerText,
    settings: state.settings,
    showWriteToCurrentDocument: Boolean(currentWriteTarget.path),
    skillModel,
    visibleModelLabel: resolveStudioModelButtonLabel({
      modelName: state.settings.modelName,
      selectedCredential: credentialModel.selectedCredential,
    }),
    writeIntentNotice,
    writeTargetDisabledReason: currentWriteTarget.disabledReason,
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

function ensureStudioChatTurnCanStart(options: {
  canChat: boolean;
  credentialNotice: string | null;
  documentCatalogEntries: ProjectDocumentCatalogEntry[] | null;
  documentCatalogError: unknown;
  isResponding: boolean;
  needsDocumentCatalog: boolean;
  skillSendBlockReason: string | null;
  toolCapabilityNotice: string | null;
  writeSendBlockReason: string | null;
}) {
  if (options.isResponding) {
    return false;
  }
  if (!options.canChat) {
    Message.warning(options.credentialNotice ?? "当前没有可用模型连接。");
    return false;
  }
  if (options.skillSendBlockReason) {
    Message.warning(options.skillSendBlockReason);
    return false;
  }
  if (options.toolCapabilityNotice) {
    Message.warning(options.toolCapabilityNotice);
    return false;
  }
  if (options.writeSendBlockReason) {
    Message.warning(options.writeSendBlockReason);
    return false;
  }
  if (!options.needsDocumentCatalog) {
    return true;
  }
  if (options.documentCatalogError) {
    Message.error(getErrorMessage(options.documentCatalogError));
    return false;
  }
  if (!options.documentCatalogEntries) {
    Message.warning("当前文稿目录快照仍在加载，请稍后重试。");
    return false;
  }
  return true;
}
