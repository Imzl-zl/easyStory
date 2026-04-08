"use client";

import type { ProjectDocumentCatalogEntry } from "@/lib/api/types";

export function buildStudioDocumentCatalogQueryKey(projectId: string) {
  return ["project-document-catalog", projectId] as const;
}

export async function buildStudioDocumentCatalogVersion(
  entries: ReadonlyArray<ProjectDocumentCatalogEntry>,
) {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new Error("Studio document catalog hashing requires Web Crypto support.");
  }
  const payload = JSON.stringify(
    [...entries]
      .sort(compareStudioCatalogEntriesByPath)
      .map((entry) => ({
        content_state: entry.content_state,
        document_kind: entry.document_kind,
        document_ref: entry.document_ref,
        mime_type: entry.mime_type,
        path: entry.path,
        resource_uri: entry.resource_uri,
        schema_id: entry.schema_id,
        source: entry.source,
        title: entry.title,
        version: entry.version,
        writable: entry.writable,
      })),
  );
  const digest = await subtle.digest("SHA-256", new TextEncoder().encode(payload));
  return `catalog:${readHexDigest(digest)}`;
}

function compareStudioCatalogEntriesByPath(
  left: ProjectDocumentCatalogEntry,
  right: ProjectDocumentCatalogEntry,
) {
  if (left.path < right.path) {
    return -1;
  }
  if (left.path > right.path) {
    return 1;
  }
  return 0;
}

function readHexDigest(buffer: ArrayBuffer) {
  return Array.from(new Uint8Array(buffer))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}
