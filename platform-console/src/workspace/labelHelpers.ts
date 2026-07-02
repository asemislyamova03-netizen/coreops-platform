import {
  DEFAULT_WORKSPACE_LABELS,
  type TenantLabelsConfig,
} from "../types/labels";

function mergeSection<T extends Record<string, string>>(
  defaults: T | undefined,
  overrides: T | undefined,
): T {
  return { ...(defaults ?? ({} as T)), ...(overrides ?? {}) };
}

export function normalizeTenantLabels(
  raw: Record<string, unknown> | null | undefined,
): TenantLabelsConfig {
  if (!raw || typeof raw !== "object") {
    return DEFAULT_WORKSPACE_LABELS;
  }

  const entities =
    raw.entities && typeof raw.entities === "object"
      ? (raw.entities as Record<string, string>)
      : undefined;
  const party_roles =
    raw.party_roles && typeof raw.party_roles === "object"
      ? (raw.party_roles as Record<string, string>)
      : undefined;
  const catalog_item_types =
    raw.catalog_item_types && typeof raw.catalog_item_types === "object"
      ? (raw.catalog_item_types as Record<string, string>)
      : undefined;

  return {
    entities: mergeSection(DEFAULT_WORKSPACE_LABELS.entities, entities),
    party_roles: mergeSection(DEFAULT_WORKSPACE_LABELS.party_roles, party_roles),
    catalog_item_types: mergeSection(
      DEFAULT_WORKSPACE_LABELS.catalog_item_types,
      catalog_item_types,
    ),
  };
}

export function entityLabel(labels: TenantLabelsConfig, key: string, fallback: string): string {
  return labels.entities?.[key] ?? fallback;
}

export function partyRoleLabel(labels: TenantLabelsConfig, key: string, fallback: string): string {
  return labels.party_roles?.[key] ?? fallback;
}

const PARTY_ROLE_PRIORITY = ["lead", "contact", "client"] as const;

/** Default role when creating a Party — driven by template labels, not tenant slug. */
export function pickDefaultPartyRole(labels: TenantLabelsConfig): string {
  const roles = labels.party_roles ?? {};
  for (const key of PARTY_ROLE_PRIORITY) {
    if (key in roles) {
      return key;
    }
  }
  return "client";
}

/**
 * Role key for clients-section subtitle — keeps kindergarten guardian when template defines it.
 */
export function pickClientsSectionPartyRoleKey(labels: TenantLabelsConfig): string {
  const roles = labels.party_roles ?? {};
  if ("lead" in roles) return "lead";
  if ("contact" in roles) return "contact";
  if ("guardian" in roles) return "guardian";
  if ("client" in roles) return "client";
  return "client";
}

/** Roles shown on the Clients/Parties list (includes template-defined roles). */
export function collectVisiblePartyRoles(labels: TenantLabelsConfig): Set<string> {
  const roles = new Set<string>(["client", "guardian", "lead", "contact"]);
  for (const key of Object.keys(labels.party_roles ?? {})) {
    roles.add(key);
  }
  return roles;
}

export function isPartyVisibleInClientsList(
  partyRole: string | null,
  labels: TenantLabelsConfig,
): boolean {
  if (partyRole === null) {
    return true;
  }
  return collectVisiblePartyRoles(labels).has(partyRole);
}

/** WorkItem participant API role — lead/contact are not participant enums; use other. */
export function pickWorkItemParticipantRole(
  defaultPartyRole: string,
): "client" | "assignee" | "observer" | "other" {
  if (defaultPartyRole === "lead" || defaultPartyRole === "contact") {
    return "other";
  }
  return "client";
}
