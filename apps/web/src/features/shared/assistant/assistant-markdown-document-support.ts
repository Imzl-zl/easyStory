"use client";

const FENCED_MARKDOWN_DOCUMENT_PATTERN = /```(?:markdown|md)\s*\n([\s\S]*?)\n```/i;
const PRIMARY_MARKDOWN_HEADING_PATTERN = /^#\s+\S+/;
const SECONDARY_MARKDOWN_HEADING_PATTERN = /^##\s+\S+/gm;
const MARKDOWN_LIST_PATTERN = /^(?:- |\* |\d+\. )\S+/gm;
const STANDALONE_DOCUMENT_MIN_LENGTH = 80;

export type AssistantMarkdownDocumentMatch = {
  body: string;
  leadingText: string | null;
  trailingText: string | null;
};

export function extractAssistantMarkdownDocument(content: string): string | null {
  return matchAssistantMarkdownDocument(content)?.body ?? null;
}

export function matchAssistantMarkdownDocument(
  content: string,
): AssistantMarkdownDocumentMatch | null {
  const normalized = content.trim();
  if (!normalized) {
    return null;
  }
  const fencedMatch = normalized.match(FENCED_MARKDOWN_DOCUMENT_PATTERN);
  if (fencedMatch) {
    const body = fencedMatch[1]?.trim();
    if (!body) {
      return null;
    }
    const fullMatch = fencedMatch[0];
    const startIndex = fencedMatch.index ?? normalized.indexOf(fullMatch);
    const leadingText = normalized.slice(0, startIndex).trim() || null;
    const trailingText = normalized.slice(startIndex + fullMatch.length).trim() || null;
    return { body, leadingText, trailingText };
  }
  if (!looksLikeStandaloneMarkdownDocument(normalized)) {
    return null;
  }
  return { body: normalized, leadingText: null, trailingText: null };
}

function looksLikeStandaloneMarkdownDocument(content: string) {
  const hasPrimaryHeading = PRIMARY_MARKDOWN_HEADING_PATTERN.test(content);
  if (!hasPrimaryHeading) {
    return false;
  }
  const secondaryHeadings = content.match(SECONDARY_MARKDOWN_HEADING_PATTERN) ?? [];
  if (secondaryHeadings.length >= 1) {
    return true;
  }
  const lists = content.match(MARKDOWN_LIST_PATTERN) ?? [];
  return content.length >= STANDALONE_DOCUMENT_MIN_LENGTH && lists.length >= 2;
}
