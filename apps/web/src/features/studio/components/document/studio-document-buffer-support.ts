"use client";

import type { AssistantActiveBufferState } from "@/lib/api/types";

const STUDIO_EDITOR_BUFFER_SOURCE = "studio_editor";
const FNV1A64_OFFSET = 0xcbf29ce484222325n;
const FNV1A64_PRIME = 0x100000001b3n;
const FNV1A64_MASK = 0xffffffffffffffffn;

export function buildStudioActiveBufferState(options: {
  baseVersion: string;
  content: string;
  dirty: boolean;
}): AssistantActiveBufferState {
  return {
    base_version: options.baseVersion,
    buffer_hash: buildStudioBufferHash(options.content),
    dirty: options.dirty,
    source: STUDIO_EDITOR_BUFFER_SOURCE,
  };
}

export function buildStudioBufferHash(content: string) {
  let hash = FNV1A64_OFFSET;
  for (const character of content) {
    hash ^= BigInt(character.codePointAt(0) ?? 0);
    hash = (hash * FNV1A64_PRIME) & FNV1A64_MASK;
  }
  return `fnv1a64:${hash.toString(16).padStart(16, "0")}`;
}
