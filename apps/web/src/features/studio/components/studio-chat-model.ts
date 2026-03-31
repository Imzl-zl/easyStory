"use client";

import { useCallback, useMemo, useState } from "react";
import { Message } from "@arco-design/web-react";

import {
  buildAssistantRetryFailure,
  buildAssistantStreamRecoveryNotice,
  shouldRetryAssistantWithoutStream,
} from "@/features/lobby/components/incubator-assistant-request-support";
import { runAssistantTurn, runAssistantTurnStream } from "@/lib/api/assistant";
import { getErrorMessage } from "@/lib/api/client";

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
  buildNextStudioChatSettingsForProvider,
  buildStudioAssistantTurnPayload,
  buildStudioUserRequestContent,
  createStudioChatMessage,
  INITIAL_STUDIO_CHAT_SETTINGS,
  normalizeStudioAssistantReply,
  replaceStudioChatMessage,
  resolveStudioFailedReply,
  resolveStudioModelButtonLabel,
  STUDIO_PENDING_REPLY_MESSAGE,
  type StudioChatMessage,
} from "./studio-chat-support";

type UseStudioChatModelOptions = {
  currentDocumentContent: string;
  currentDocumentPath: string | null;
  projectId: string;
};

export function useStudioChatModel({
  currentDocumentContent,
  currentDocumentPath,
  projectId,
}: UseStudioChatModelOptions) {
  const [attachments, setAttachments] = useState<StudioChatAttachment[]>([]);
  const [messages, setMessages] = useState<StudioChatMessage[]>([]);
  const [selectedContextPaths, setSelectedContextPaths] = useState<string[]>([]);
  const [settings, setSettings] = useState(INITIAL_STUDIO_CHAT_SETTINGS);
  const [isResponding, setIsResponding] = useState(false);
  const hasUserMessage = useMemo(
    () => messages.some((message) => message.role === "user"),
    [messages],
  );
  const credentialModel = useStudioChatCredentialModel(
    projectId,
    hasUserMessage,
    settings,
    setSettings,
  );

  const handleToggleContext = useCallback((path: string) => {
    setSelectedContextPaths((current) =>
      current.includes(path)
        ? current.filter((item) => item !== path)
        : [...current, path],
    );
  }, []);

  const handleProviderChange = useCallback((provider: string) => {
    setSettings((current) =>
      buildNextStudioChatSettingsForProvider(
        credentialModel.credentialOptions,
        current,
        provider,
      ));
  }, [credentialModel.credentialOptions]);

  const handleModelNameChange = useCallback((value: string) => {
    setSettings((current) => ({ ...current, modelName: value }));
  }, []);

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
    const userMessage = buildStudioUserMessage({
      attachments,
      content,
      currentDocumentContent,
      currentDocumentPath,
      selectedContextPaths,
    });

    const assistantMessage = createStudioChatMessage(
      "assistant",
      STUDIO_PENDING_REPLY_MESSAGE,
      { status: "pending" },
    );
    const nextMessages = [...messages, userMessage];
    const payload = buildStudioAssistantTurnPayload({
      messages: nextMessages,
      projectId,
      settings,
    });

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setAttachments([]);
    setIsResponding(true);

    try {
      const result = settings.streamOutput
        ? await runStudioChatStream(payload, assistantMessage.id, setMessages)
        : await runAssistantTurn(payload);
      setMessages((current) =>
        replaceStudioChatMessage(
          current,
          assistantMessage.id,
          buildCompletedStudioMessage(assistantMessage.id, result.content),
        ));
    } catch (error) {
      setMessages((current) =>
        replaceStudioChatMessage(
          current,
          assistantMessage.id,
          buildFailedStudioMessage(assistantMessage.id, current, error),
        ));
      Message.error(getErrorMessage(error));
    } finally {
      setIsResponding(false);
    }
  }, [
    credentialModel.canChat,
    credentialModel.credentialNotice,
    currentDocumentContent,
    currentDocumentPath,
    isResponding,
    messages,
    projectId,
    selectedContextPaths,
    settings,
    attachments,
  ]);

  return {
    attachments: extractStudioChatAttachmentMeta(attachments),
    credentialModel,
    handleAttachFiles,
    handleModelNameChange,
    handleProviderChange,
    handleRemoveAttachment,
    handleSendMessage,
    handleToggleContext,
    isResponding,
    messages,
    selectedContextPaths,
    selectedCredentialLabel: credentialModel.selectedCredential?.displayLabel ?? null,
    settings,
    visibleModelLabel: resolveStudioModelButtonLabel({
      modelName: settings.modelName,
      selectedCredential: credentialModel.selectedCredential,
    }),
  };
}

function buildCompletedStudioMessage(messageId: string, content: string) {
  const normalized = normalizeStudioAssistantReply(content);
  return {
    content: normalized.content,
    id: messageId,
    rawMarkdown: content,
    role: "assistant" as const,
    status: normalized.status,
  };
}

function buildFailedStudioMessage(
  messageId: string,
  messages: StudioChatMessage[],
  error: unknown,
) {
  const failedMessage = messages.find((message) => message.id === messageId);
  const fallbackContent = resolveStudioFailedReply(
    failedMessage?.content ?? "",
    getErrorMessage(error),
  );
  return {
    content: fallbackContent ?? getErrorMessage(error),
    id: messageId,
    rawMarkdown: failedMessage?.rawMarkdown ?? "",
    role: "assistant" as const,
    status: "error" as const,
  };
}

async function runStudioChatStream(
  payload: Parameters<typeof runAssistantTurn>[0],
  messageId: string,
  setMessages: React.Dispatch<React.SetStateAction<StudioChatMessage[]>>,
) {
  try {
    return await runAssistantTurnStream(payload, {
      onChunk: (delta) => {
        setMessages((current) =>
          appendStudioChatMessageDelta(current, messageId, delta));
      },
    });
  } catch (error) {
    if (!shouldRetryAssistantWithoutStream(error)) {
      throw error;
    }
    Message.info(buildAssistantStreamRecoveryNotice());
    try {
      return await runAssistantTurn(payload);
    } catch (retryError) {
      throw buildAssistantRetryFailure(error, retryError);
    }
  }
}

function buildStudioUserMessage(options: {
  attachments: StudioChatAttachment[];
  content: string;
  currentDocumentContent: string;
  currentDocumentPath: string | null;
  selectedContextPaths: string[];
}) {
  const trimmedContent = options.content.trim();
  const displayContent = trimmedContent || buildStudioAttachmentOnlyMessage(options.attachments);
  const requestContent = buildStudioUserRequestContent({
    attachments: options.attachments,
    currentDocumentContent: options.currentDocumentContent,
    currentDocumentPath: options.currentDocumentPath,
    message: displayContent,
    selectedContextPaths: options.selectedContextPaths,
  });
  return createStudioChatMessage("user", displayContent, {
    attachments: extractStudioChatAttachmentMeta(options.attachments),
    requestContent,
  });
}
