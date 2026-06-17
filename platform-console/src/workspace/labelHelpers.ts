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
