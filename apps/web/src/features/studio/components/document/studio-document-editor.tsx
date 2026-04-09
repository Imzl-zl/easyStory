"use client";

import { JsonDocumentEditor } from "@/features/studio/components/document/json-document-editor";
import { MarkdownDocumentEditor } from "@/features/studio/components/document/markdown-document-editor";
import {
  isJsonStudioDocument,
  type StudioDocumentEditorProps,
} from "@/features/studio/components/document/studio-document-editor-types";

export function StudioDocumentEditor(props: Readonly<StudioDocumentEditorProps>) {
  if (isJsonStudioDocument(props.documentPath)) {
    return <JsonDocumentEditor key={`json:${props.documentPath ?? "empty"}`} {...props} />;
  }
  return (
    <MarkdownDocumentEditor
      key={`markdown:${props.documentPath ?? "empty"}`}
      content={props.content}
      documentNode={props.documentNode}
      documentPath={props.documentPath}
      hasUnsavedChanges={props.hasUnsavedChanges}
      isLoading={props.isLoading}
      isSaving={props.isSaving}
      onChange={props.onChange}
      onSave={props.onSave}
      saveNoun={props.saveNoun}
    />
  );
}
