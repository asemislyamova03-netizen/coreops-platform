export type PartyType = "person" | "organization" | "sole_proprietor";
export type PartyStatus = "active" | "inactive" | "archived";
export type ContactMethodType =
  | "email"
  | "phone"
  | "mobile"
  | "telegram"
  | "whatsapp"
  | "other";

export interface ContactMethod {
  id: string;
  method_type: string;
  value: string;
  label: string | null;
  is_primary: boolean;
}

export interface Address {
  id: string;
  address_type: string;
  country: string | null;
  city: string | null;
  line1: string | null;
  line2: string | null;
  postal_code: string | null;
  is_primary: boolean;
}

export interface Party {
  id: string;
  tenant_id: string;
  party_type: PartyType;
  display_name: string;
  status: PartyStatus;
  metadata_json: Record<string, unknown>;
  contact_methods: ContactMethod[];
  addresses: Address[];
  custom_fields: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  created_by_user_id: string | null;
  updated_by_user_id: string | null;
}

export interface ListPartiesParams {
  party_type?: PartyType;
  status?: PartyStatus;
  party_role?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export function getPartyRole(party: Party): string | null {
  const role = party.metadata_json?.party_role;
  return typeof role === "string" ? role : null;
}

export interface ContactMethodCreate {
  method_type: ContactMethodType;
  value: string;
  label?: string | null;
  is_primary?: boolean;
}

export interface PartyCreate {
  party_type: PartyType;
  display_name: string;
  status?: PartyStatus;
  party_role?: string | null;
  metadata_json?: Record<string, unknown>;
  contact_methods?: ContactMethodCreate[];
  custom_fields?: Record<string, unknown>;
}

export interface PartyUpdate {
  party_type?: PartyType;
  display_name?: string;
  status?: PartyStatus;
  party_role?: string | null;
  contact_methods?: ContactMethodCreate[];
  custom_fields?: Record<string, unknown>;
}

export interface PartyMatchRequest {
  name?: string | null;
  phone?: string | null;
  email?: string | null;
  telegram_username?: string | null;
  telegram_user_id?: string | null;
  whatsapp?: string | null;
}

export type PartyMatchType = "exact" | "weak";

export interface PartyMatchContactPreview {
  method_type: string;
  value: string;
  label: string | null;
  is_primary: boolean;
}

export interface PartyMatchWorkItemPreview {
  id: string;
  title: string;
  status: string;
  updated_at: string;
}

export interface PartyMatchHit {
  party_id: string;
  display_name: string;
  party_type: PartyType;
  status: PartyStatus;
  match_type: PartyMatchType;
  score: number;
  matched_on: string[];
  contact_methods: PartyMatchContactPreview[];
  recent_work_items: PartyMatchWorkItemPreview[];
}

export interface PartyMatchNormalizedQuery {
  name: string | null;
  phone: string | null;
  email: string | null;
  telegram_username: string | null;
  telegram_user_id: string | null;
  whatsapp: string | null;
}

export interface PartyMatchResponse {
  matches: PartyMatchHit[];
  query_normalized: PartyMatchNormalizedQuery;
}
