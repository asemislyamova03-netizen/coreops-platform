/**
 * Helpers for CreateWorkItemModal party match UI (E3).
 * Run: npx tsx src/workspace/partyMatchUiHelpers.test.ts
 */

import type { PartyMatchHit, PartyMatchRequest } from "../types/party";

export const PARTY_MATCH_DEBOUNCE_MS = 500;
export const PARTY_MATCH_MAX_VISIBLE = 3;

const MATCHED_ON_LABELS: Record<string, string> = {
  phone: "телефон",
  email: "email",
  whatsapp: "WhatsApp",
  telegram_username: "Telegram",
  telegram_user_id: "Telegram ID",
  name: "имя",
};

export function buildPartyMatchPayload(input: {
  name: string;
  phone: string;
  email: string;
}): PartyMatchRequest | null {
  const name = input.name.trim();
  const phone = input.phone.trim();
  const email = input.email.trim();

  const phoneDigits = phone.replace(/\D+/g, "");
  const hasPhone = phoneDigits.length >= 10;
  const hasEmail = email.includes("@") && email.length >= 5;
  const hasName = name.length >= 3;

  if (!hasPhone && !hasEmail && !hasName) {
    return null;
  }

  return {
    name: hasName ? name : null,
    phone: hasPhone ? phone : null,
    email: hasEmail ? email : null,
  };
}

export function partyMatchFingerprint(payload: PartyMatchRequest): string {
  return [
    payload.name?.trim().toLowerCase() ?? "",
    payload.phone?.replace(/\D+/g, "") ?? "",
    payload.email?.trim().toLowerCase() ?? "",
  ].join("|");
}

export function formatMatchedOn(matchedOn: string[]): string {
  return matchedOn.map((key) => MATCHED_ON_LABELS[key] ?? key).join(", ");
}

export function matchTypeLabel(matchType: PartyMatchHit["match_type"]): string {
  return matchType === "exact" ? "точное совпадение" : "похожее имя";
}

export function pickVisibleMatches(matches: PartyMatchHit[]): PartyMatchHit[] {
  const exact = matches.filter((item) => item.match_type === "exact");
  const weak = matches.filter((item) => item.match_type === "weak");
  return [...exact, ...weak].slice(0, PARTY_MATCH_MAX_VISIBLE);
}

export function hasExactMatch(matches: PartyMatchHit[]): boolean {
  return matches.some((item) => item.match_type === "exact");
}
