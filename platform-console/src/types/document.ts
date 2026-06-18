export type DocumentStatus =
  | "draft"
  | "generated"
  | "sent_for_review"
  | "sent_for_signature"
  | "signed"
  | "rejected"
  | "cancelled"
  | "archived";

export type SignatureStatus = "pending" | "sent" | "signed" | "rejected" | "cancelled";

export interface SignatureRequest {
  id: string;
  status: SignatureStatus;
  sent_at: string | null;
  signed_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface Document {
  id: string;
  tenant_id: string;
  template_id: string | null;
  title: string;
  status: DocumentStatus;
  rendered_content: string | null;
  context_json: Record<string, unknown>;
  party_id: string | null;
  work_item_id: string | null;
  signature_requests: SignatureRequest[];
  created_at: string;
  updated_at: string;
}

export interface ListDocumentsParams {
  status?: DocumentStatus;
  skip?: number;
  limit?: number;
}
