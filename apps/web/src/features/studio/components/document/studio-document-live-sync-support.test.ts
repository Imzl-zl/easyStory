import assert from "node:assert/strict";
import test from "node:test";

import {
  createIdleStudioDocumentLiveSyncState,
  createStaleStudioDocumentLiveSyncState,
  createSyncedStudioDocumentLiveSyncState,
  createWritingStudioDocumentLiveSyncState,
  resolveStudioDocumentBaseVersion,
} from "@/features/studio/components/document/studio-document-live-sync-support";

test("resolveStudioDocumentBaseVersion preserves the original draft base version while editing", () => {
  assert.equal(
    resolveStudioDocumentBaseVersion({
      documentVersion: "sha256:latest",
      draftBaseVersion: "sha256:original",
      hasUnsavedChanges: true,
    }),
    "sha256:original",
  );
  assert.equal(
    resolveStudioDocumentBaseVersion({
      documentVersion: "sha256:latest",
      draftBaseVersion: "sha256:original",
      hasUnsavedChanges: false,
    }),
    "sha256:latest",
  );
});

test("studio document live sync states expose user-facing copy", () => {
  assert.deepEqual(createIdleStudioDocumentLiveSyncState(), {
    detail: null,
    status: "idle",
  });
  assert.deepEqual(createWritingStudioDocumentLiveSyncState(), {
    detail: "助手正在写入当前文稿…",
    status: "writing",
  });
  assert.deepEqual(createSyncedStudioDocumentLiveSyncState(), {
    detail: "助手写入已自动同步到当前编辑器。",
    status: "synced",
  });
  assert.deepEqual(createStaleStudioDocumentLiveSyncState(), {
    detail: "远端文稿已更新，当前仍保留你的未保存草稿。",
    status: "stale_remote",
  });
});
