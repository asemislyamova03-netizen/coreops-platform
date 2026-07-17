import type {
  ListPartiesParams,
  Party,
  PartyCreate,
  PartyMatchRequest,
  PartyMatchResponse,
  PartyUpdate,
} from "../types/party";
import { buildQuery } from "./query";
import { workspaceApiFetch } from "./workspace";

export function listParties(params: ListPartiesParams = {}): Promise<Party[]> {
  return workspaceApiFetch<Party[]>(
    `/parties${buildQuery({
      party_type: params.party_type,
      status: params.status,
      party_role: params.party_role,
      search: params.search,
      skip: params.skip,
      limit: params.limit,
    })}`,
  );
}

export function getParty(partyId: string): Promise<Party> {
  return workspaceApiFetch<Party>(`/parties/${partyId}`);
}

export function createParty(payload: PartyCreate): Promise<Party> {
  return workspaceApiFetch<Party>("/parties", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateParty(partyId: string, payload: PartyUpdate): Promise<Party> {
  return workspaceApiFetch<Party>(`/parties/${partyId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/** Read-only contact match (E2). Does not create or link parties. */
export function matchParties(payload: PartyMatchRequest): Promise<PartyMatchResponse> {
  return workspaceApiFetch<PartyMatchResponse>("/parties/match", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
