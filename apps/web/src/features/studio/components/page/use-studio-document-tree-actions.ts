import { useCallback, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Message } from "@arco-design/web-react";

import { buildStudioDocumentCatalogQueryKey } from "@/features/studio/components/document/studio-document-catalog-support";
import {
  buildDocumentTreeDialogCopy,
  buildStudioDocumentEntryPath,
  findClosestRemainingFilePath,
  isDocumentTreePathAffected,
  readDocumentTreeLabel,
  readDocumentTreeParentPath,
  readInvalidDocumentEntryNameMessage,
  readStudioDocumentEntryBaseName,
  remapDocumentTreePath,
} from "@/features/studio/components/page/studio-panel-path";
import type { DocumentTreeDialogState } from "@/features/studio/components/page/studio-panel-path";
import type { DocumentTreeNode } from "@/features/studio/components/page/studio-document-tree";
import {
  createProjectDocumentEntry,
  deleteProjectDocumentEntry,
  renameProjectDocumentEntry,
} from "@/lib/api/projects";
import { getErrorMessage } from "@/lib/api/client";

type UseDocumentTreeActionsConfig = {
  documentModel: {
    discardUnsavedChanges: () => void;
    hasUnsavedChanges: boolean;
  };
  documentPath: string | null;
  navigationGuard: {
    attemptNavigation: (callback: () => void) => void;
  };
  projectId: string;
  chatModel: {
    remapDocumentPathReferences: (previousPath: string, nextPath: string | null) => void;
  };
  tree: DocumentTreeNode[];
  updateParams: (patches: Record<string, string | null>) => void;
};

export function useStudioDocumentTreeActions(config: UseDocumentTreeActionsConfig) {
  const queryClient = useQueryClient();
  const [documentTreeDialog, setDocumentTreeDialog] = useState<DocumentTreeDialogState>(null);
  const [documentTreeDialogValue, setDocumentTreeDialogValue] = useState("");

  const closeDocumentTreeDialog = useCallback(() => {
    setDocumentTreeDialog(null);
    setDocumentTreeDialogValue("");
  }, []);

  const invalidateProjectDocumentQueries = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["project-document-tree", config.projectId] });
    await queryClient.invalidateQueries({ queryKey: buildStudioDocumentCatalogQueryKey(config.projectId) });
  }, [config.projectId, queryClient]);

  const createDocumentEntryMutation = useMutation({
    mutationFn: (payload: { kind: "file" | "folder"; path: string }) =>
      createProjectDocumentEntry(config.projectId, payload),
    onSuccess: async (entry) => {
      await invalidateProjectDocumentQueries();
      closeDocumentTreeDialog();
      Message.success(entry.node_type === "file" ? "已新建文稿" : "已新建目录");
      if (entry.node_type !== "file") {
        return;
      }
      config.navigationGuard.attemptNavigation(() => {
        config.documentModel.discardUnsavedChanges();
        config.updateParams({ doc: entry.path });
      });
    },
    onError: (error) => {
      Message.error(getErrorMessage(error));
    },
  });

  const renameDocumentEntryMutation = useMutation({
    mutationFn: (payload: { path: string; next_path: string }) =>
      renameProjectDocumentEntry(config.projectId, payload),
    onSuccess: async (entry, payload) => {
      const nextDocumentPath = config.documentPath
        ? remapDocumentTreePath(config.documentPath, payload.path, entry.path)
        : null;
      await invalidateProjectDocumentQueries();
      closeDocumentTreeDialog();
      config.chatModel.remapDocumentPathReferences(payload.path, entry.path);
      if (nextDocumentPath !== config.documentPath) {
        config.documentModel.discardUnsavedChanges();
        config.updateParams({ doc: nextDocumentPath });
      }
      Message.success(entry.node_type === "file" ? "已重命名文稿" : "已重命名目录");
    },
    onError: (error) => {
      Message.error(getErrorMessage(error));
    },
  });

  const deleteDocumentEntryMutation = useMutation({
    mutationFn: (path: string) => deleteProjectDocumentEntry(config.projectId, path),
    onSuccess: async (entry) => {
      const currentDocumentAffected = config.documentPath
        ? isDocumentTreePathAffected(config.documentPath, entry.path)
        : false;
      const nextDocumentPath = currentDocumentAffected
        ? findClosestRemainingFilePath(config.tree, entry.path, config.documentPath)
        : config.documentPath;
      await invalidateProjectDocumentQueries();
      closeDocumentTreeDialog();
      config.chatModel.remapDocumentPathReferences(entry.path, null);
      if (currentDocumentAffected) {
        config.documentModel.discardUnsavedChanges();
        config.updateParams({ doc: nextDocumentPath });
      }
      Message.success(entry.node_type === "file" ? "已删除文稿" : "已删除目录");
    },
    onError: (error) => {
      Message.error(getErrorMessage(error));
    },
  });

  const handleSelectNode = useCallback((node: DocumentTreeNode) => {
    if (node.type !== "file" || node.path === config.documentPath) {
      return;
    }
    config.navigationGuard.attemptNavigation(() => {
      config.documentModel.discardUnsavedChanges();
      config.updateParams({ doc: node.path });
    });
  }, [config]);

  const handleAddDocument = useCallback((parentPath: string) => {
    setDocumentTreeDialog({
      mode: "create-file",
      parentPath,
      parentLabel: readDocumentTreeLabel(parentPath),
    });
    setDocumentTreeDialogValue("");
  }, []);

  const handleAddFolder = useCallback((parentPath: string) => {
    setDocumentTreeDialog({
      mode: "create-folder",
      parentPath,
      parentLabel: readDocumentTreeLabel(parentPath),
    });
    setDocumentTreeDialogValue("");
  }, []);

  const handleRenameNode = useCallback((node: DocumentTreeNode) => {
    setDocumentTreeDialog({ mode: "rename", node });
    setDocumentTreeDialogValue(readStudioDocumentEntryBaseName(node));
  }, []);

  const handleDeleteNode = useCallback((node: DocumentTreeNode) => {
    setDocumentTreeDialog({ mode: "delete", node });
    setDocumentTreeDialogValue("");
  }, []);

  const handleConfirmDocumentTreeDialog = useCallback(() => {
    if (!documentTreeDialog) {
      return;
    }
    if (documentTreeDialog.mode === "create-file" || documentTreeDialog.mode === "create-folder") {
      const kind = documentTreeDialog.mode === "create-file" ? "file" : "folder";
      const path = buildStudioDocumentEntryPath(
        documentTreeDialog.parentPath,
        documentTreeDialogValue,
        kind,
      );
      if (!path) {
        Message.warning(readInvalidDocumentEntryNameMessage(kind, documentTreeDialog.parentPath));
        return;
      }
      createDocumentEntryMutation.mutate({ kind, path });
      return;
    }
    if (documentTreeDialog.mode !== "rename" && documentTreeDialog.mode !== "delete") {
      return;
    }
    const targetNode = documentTreeDialog.node;

    if (
      config.documentPath
      && config.documentModel.hasUnsavedChanges
      && isDocumentTreePathAffected(config.documentPath, targetNode.path)
    ) {
      Message.warning("当前文稿有未保存修改，先保存或放弃后，再重命名或删除相关文稿。");
      return;
    }

    if (documentTreeDialog.mode === "rename") {
      const nextPath = buildStudioDocumentEntryPath(
        readDocumentTreeParentPath(targetNode.path),
        documentTreeDialogValue,
        targetNode.type,
      );
      if (!nextPath) {
        Message.warning(
          readInvalidDocumentEntryNameMessage(
            targetNode.type,
            readDocumentTreeParentPath(targetNode.path),
          ),
        );
        return;
      }
      if (nextPath === targetNode.path) {
        Message.warning("名称没有变化。");
        return;
      }
      renameDocumentEntryMutation.mutate({
        path: targetNode.path,
        next_path: nextPath,
      });
      return;
    }

    deleteDocumentEntryMutation.mutate(targetNode.path);
  }, [
    createDocumentEntryMutation,
    deleteDocumentEntryMutation,
    config,
    documentTreeDialog,
    documentTreeDialogValue,
    renameDocumentEntryMutation,
  ]);

  const handleCreateNewDocument = useCallback(() => {
    Message.info("先在左侧创作结构里新建文稿，再把内容整理到当前写作流里。");
  }, []);

  const dialogCopy = buildDocumentTreeDialogCopy(documentTreeDialog);
  const dialogPending = documentTreeDialog?.mode === "rename"
    ? renameDocumentEntryMutation.isPending
    : documentTreeDialog?.mode === "delete"
      ? deleteDocumentEntryMutation.isPending
      : createDocumentEntryMutation.isPending;

  return {
    closeDocumentTreeDialog,
    dialogCopy,
    dialogPending,
    documentTreeDialog,
    documentTreeDialogValue,
    handleAddDocument,
    handleAddFolder,
    handleConfirmDocumentTreeDialog,
    handleCreateNewDocument,
    handleDeleteNode,
    handleRenameNode,
    handleSelectNode,
    setDocumentTreeDialogValue,
  };
}
