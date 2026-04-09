export const STUDIO_ATTACHMENT_MAX_COUNT = 4;
const MAX_STUDIO_ATTACHMENT_BYTES = 1024 * 1024;
const MAX_STUDIO_ATTACHMENT_PREVIEW_LENGTH = 12000;

const SUPPORTED_STUDIO_ATTACHMENT_EXTENSIONS = new Set([
  "txt",
  "md",
  "markdown",
  "json",
  "yaml",
  "yml",
  "csv",
  "ts",
  "tsx",
  "js",
  "jsx",
  "mjs",
  "cjs",
  "py",
  "java",
  "go",
  "rs",
  "sql",
  "html",
  "htm",
  "css",
  "scss",
  "xml",
  "sh",
  "log",
]);

const SUPPORTED_STUDIO_ATTACHMENT_MIME_TYPES = new Set([
  "application/json",
  "application/sql",
  "application/xml",
  "text/csv",
  "text/html",
  "text/markdown",
  "text/plain",
  "text/xml",
]);

export const STUDIO_ATTACHMENT_ACCEPT = [
  ".txt",
  ".md",
  ".markdown",
  ".json",
  ".yaml",
  ".yml",
  ".csv",
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  ".py",
  ".java",
  ".go",
  ".rs",
  ".sql",
  ".html",
  ".css",
  ".xml",
  ".sh",
  ".log",
].join(",");

export type StudioChatAttachment = {
  content: string;
  id: string;
  name: string;
  size: number;
};

export type StudioChatAttachmentMeta = Omit<StudioChatAttachment, "content">;

export async function readStudioChatAttachments(files: FileList | File[]) {
  const normalizedFiles = Array.from(files);
  if (normalizedFiles.length === 0) {
    return [];
  }
  if (normalizedFiles.length > STUDIO_ATTACHMENT_MAX_COUNT) {
    throw new Error(`一次最多发送 ${STUDIO_ATTACHMENT_MAX_COUNT} 个文件。`);
  }
  return Promise.all(normalizedFiles.map(readStudioChatAttachment));
}

export function extractStudioChatAttachmentMeta(
  attachments: StudioChatAttachment[],
): StudioChatAttachmentMeta[] {
  return attachments.map(({ id, name, size }) => ({ id, name, size }));
}

export function buildStudioAttachmentContext(
  attachments: StudioChatAttachment[],
) {
  if (attachments.length === 0) {
    return "";
  }
  return attachments.map(buildStudioAttachmentBlock).join("\n\n");
}

export function buildStudioAttachmentOnlyMessage(
  attachments: StudioChatAttachment[],
) {
  if (attachments.length === 0) {
    return "";
  }
  if (attachments.length === 1) {
    return `我附带了 1 个文件：${attachments[0]?.name}，请结合文件内容处理。`;
  }
  return `我附带了 ${attachments.length} 个文件，请结合文件内容处理。`;
}

export function formatStudioChatAttachmentSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

async function readStudioChatAttachment(file: File): Promise<StudioChatAttachment> {
  validateStudioChatAttachment(file);
  const content = await file.text();
  return {
    content,
    id: `file-${Math.random().toString(36).slice(2, 10)}`,
    name: file.name,
    size: file.size,
  };
}

function validateStudioChatAttachment(file: File) {
  if (!isSupportedStudioAttachment(file)) {
    throw new Error(`暂时只支持发送文本类文件，当前文件不支持：${file.name}`);
  }
  if (file.size > MAX_STUDIO_ATTACHMENT_BYTES) {
    throw new Error(`文件过大，单个文件需小于 ${formatStudioChatAttachmentSize(MAX_STUDIO_ATTACHMENT_BYTES)}：${file.name}`);
  }
}

function isSupportedStudioAttachment(file: File) {
  if (file.type.startsWith("text/")) {
    return true;
  }
  if (SUPPORTED_STUDIO_ATTACHMENT_MIME_TYPES.has(file.type)) {
    return true;
  }
  const extension = file.name.split(".").pop()?.trim().toLowerCase() ?? "";
  return SUPPORTED_STUDIO_ATTACHMENT_EXTENSIONS.has(extension);
}

function buildStudioAttachmentBlock(attachment: StudioChatAttachment) {
  return [
    `【附带文件】${attachment.name}`,
    `大小：${formatStudioChatAttachmentSize(attachment.size)}`,
    truncateStudioAttachmentContent(attachment.content),
  ].join("\n");
}

function truncateStudioAttachmentContent(content: string) {
  const trimmed = content.trim();
  if (!trimmed) {
    return "[文件内容为空]";
  }
  if (trimmed.length <= MAX_STUDIO_ATTACHMENT_PREVIEW_LENGTH) {
    return trimmed;
  }
  return `${trimmed.slice(0, MAX_STUDIO_ATTACHMENT_PREVIEW_LENGTH)}\n\n[文件内容过长，已截断后发送]`;
}
