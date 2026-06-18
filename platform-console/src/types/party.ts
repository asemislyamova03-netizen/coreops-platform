export type PartyType = "person" | "organization" | "sole_proprietor";
export type PartyStatus = "active" | "inactive" | "archived";

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
