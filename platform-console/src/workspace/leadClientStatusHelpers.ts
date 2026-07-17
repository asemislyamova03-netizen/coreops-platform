/**
 * Helpers for LeadDetailModal «Сделать клиентом» (E8-C).
 * Run: npx tsx src/workspace/leadClientStatusHelpers.test.ts
 */

export const CLIENT_PARTY_ROLE = "client";

export const MARK_AS_CLIENT_HELP =
  "Это только пометка контакта как клиента. Tenant создаётся отдельно, если нужен рабочий контур.";

export const ALREADY_CLIENT_HINT = "Контакт уже отмечен как клиент.";

export type LeadClientStatusView = {
  partyRole: string | null;
  isClient: boolean;
  canMarkAsClient: boolean;
  shouldShowClientBlock: boolean;
  showClientBadge: boolean;
  helpText: string | null;
  badgeLabel: string;
};

export type LeadClientStatusInput = {
  hasParty: boolean;
  stageCode: string | null | undefined;
  partyRole: string | null | undefined;
};

export function normalizePartyRole(role: string | null | undefined): string | null {
  if (typeof role !== "string") return null;
  const trimmed = role.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function isPartyClientRole(role: string | null | undefined): boolean {
  return normalizePartyRole(role) === CLIENT_PARTY_ROLE;
}

/** Payload for updateParty — stage/tenant untouched. */
export function buildMarkAsClientPayload(): { party_role: typeof CLIENT_PARTY_ROLE } {
  return { party_role: CLIENT_PARTY_ROLE };
}

export function getLeadClientStatusView(
  input: LeadClientStatusInput,
): LeadClientStatusView {
  const partyRole = normalizePartyRole(input.partyRole);
  const isClient = partyRole === CLIENT_PARTY_ROLE;
  const isAccepted = (input.stageCode ?? "").trim() === "accepted";
  const hasParty = Boolean(input.hasParty);

  if (!hasParty) {
    return {
      partyRole,
      isClient: false,
      canMarkAsClient: false,
      shouldShowClientBlock: false,
      showClientBadge: false,
      helpText: null,
      badgeLabel: "Клиент",
    };
  }

  const canMarkAsClient = isAccepted && !isClient;
  const showClientBadge = isClient;
  // Accepted + non-client → action block; already client → badge (any stage, low noise).
  const shouldShowClientBlock = canMarkAsClient || showClientBadge;

  return {
    partyRole,
    isClient,
    canMarkAsClient,
    shouldShowClientBlock,
    showClientBadge,
    helpText: canMarkAsClient ? MARK_AS_CLIENT_HELP : isClient ? ALREADY_CLIENT_HINT : null,
    badgeLabel: "Клиент",
  };
}
