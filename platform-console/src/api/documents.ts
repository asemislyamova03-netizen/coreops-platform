import type { Document, ListDocumentsParams } from "../types/document";
import { buildQuery } from "./query";
import { workspaceApiFetch } from "./workspace";

export function listDocuments(params: ListDocumentsParams = {}): Promise<Document[]> {
  return workspaceApiFetch<Document[]>(
    `/documents${buildQuery({
      status: params.status,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}

export function getDocument(documentId: string): Promise<Document> {
  return workspaceApiFetch<Document>(`/documents/${documentId}`);
}
