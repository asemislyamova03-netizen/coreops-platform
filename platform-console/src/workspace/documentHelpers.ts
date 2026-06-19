import type { Document } from "../types/document";
import { formatSignatureStatus } from "../i18n/ruUi";

const PENDING_DOCUMENT_STATUSES = new Set([
  "sent_for_review",
  "sent_for_signature",
]);

const PENDING_SIGNATURE_STATUSES = new Set(["pending", "sent"]);

export function isDocumentPendingAction(document: Document): boolean {
  if (PENDING_DOCUMENT_STATUSES.has(document.status)) {
    return true;
  }
  return document.signature_requests.some((item) =>
    PENDING_SIGNATURE_STATUSES.has(item.status),
  );
}

export function filterDocumentsByParty(documents: Document[], partyId: string): Document[] {
  return documents.filter((doc) => doc.party_id === partyId);
}

export function getDocumentSignatureHint(document: Document): string {
  if (document.signature_requests.length === 0) {
    return "—";
  }
  const latest = document.signature_requests[document.signature_requests.length - 1];
  return formatSignatureStatus(latest.status);
}
